"""
Crates crawler, step 0: inventory.

Answers two questions before any parser exists:
  1. How many distinct projects are there? (N, which the concentration claim depends on)
  2. Which Live schema versions do they span? (which determines parser scope)

Reads only the gzip header region of each .als for version attributes, but note
that it ALSO content-hashes every file end to end for duplicate detection. On a
corpus with a deep Backup/ history the hashing, not the header read, dominates
runtime. Pass --no-hash to skip it if you only need N and the version histogram.

Nothing fails silently. Unreadable directories, unreadable headers, and weak
classifications are all counted and reported.

Usage:
    python inventory.py C:\\Users\\me\\Music D:\\Projects
    python inventory.py --no-hash C:\\Users\\me\\Music
    python inventory.py --out inventory.csv C:\\Users\\me\\Music

Output:
    inventory.csv   one row per .als found
    stdout summary  project counts, version histogram, backup distribution
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, asdict, fields
from pathlib import Path

HEADER_BYTES = 4096
HASH_CHUNK = 1 << 20

ABLETON_TAG = re.compile(rb"<Ableton\b[^>]*>")
ATTR = re.compile(rb'(\w+)="([^"]*)"')

# "Project Name [2024-03-15 143022].als"
BACKUP_STAMP = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{6})\]\s*$")

# Path fragments that indicate factory or vendor content rather than authored work.
# Reported separately rather than dropped, so the decision stays visible.
# NOTE: these are matched against a lowercased path with os.sep normalised to "\".
FACTORY_HINTS = (
    "ableton live 9 suite",
    "ableton live 10 suite",
    "ableton live 11 suite",
    "ableton live 12 suite",
    "core library",
    "factory packs",
    "\\packs\\",
    "/packs/",
    "program files\\ableton",
    "applications/ableton",
)

SKIP_DIRS = {
    "$recycle.bin",
    ".git",
    "node_modules",
    "system volume information",
    "windows",
    "appdata",
    ".trash",
    ".trashes",
}

# Populated by iter_als. Directories os.walk could not read, with the reason.
WALK_ERRORS: list[tuple[str, str]] = []

# parent dir -> count of .als files in it. Avoids re-globbing per file.
_SIBLING_CACHE: dict[str, int] = {}


@dataclass
class Row:
    path: str
    filename: str
    kind: str  # primary | backup | orphan
    classify_reason: str  # why `kind` was assigned; makes N auditable
    project_group_id: str
    project_dir: str
    backup_timestamp: str
    is_factory_path: int
    content_hash: str
    file_size: int
    last_modified: float
    live_creator: str
    major_version: str
    minor_version: str
    schema_change_count: str
    header_status: str  # ok | no_header | error
    was_gzip: int  # 1 normal, 0 uncompressed .als (which is legal, not an error)
    header_error: str


def _on_walk_error(err: OSError) -> None:
    """Record rather than swallow. An unknown number of skipped directories
    silently corrupts N, which is the one number this script exists to produce."""
    WALK_ERRORS.append((getattr(err, "filename", "?") or "?", str(err)))


def iter_als(roots: list[Path]):
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root, onerror=_on_walk_error):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            als_here = [n for n in filenames if n.lower().endswith(".als")]
            if als_here:
                _SIBLING_CACHE[dirpath] = len(als_here)
            for name in als_here:
                yield Path(dirpath) / name


def classify(path: Path) -> tuple[str, str, Path, str]:
    """Return (kind, reason, project_dir, backup_timestamp).

    `reason` records which rule fired, so a suspicious N can be traced to the
    rule that produced it instead of being taken on faith.
    """
    parent = path.parent
    stamp = ""
    m = BACKUP_STAMP.search(path.stem)
    if m:
        stamp = m.group(1)

    if parent.name.lower() == "backup":
        return "backup", "in_backup_dir", parent.parent, stamp

    # Ableton project folders conventionally end in " Project" and contain an
    # "Ableton Project Info" directory. Either is strong evidence.
    if parent.name.lower().endswith(" project") or (parent / "Ableton Project Info").exists():
        return "primary", "project_folder", parent, stamp

    # Weak heuristic: a loose .als in a folder holding only a few sets. This is
    # the rule most likely to inflate N (a single stray .als in Downloads scores
    # as a project), so it is labelled and counted separately in the summary.
    n_siblings = _SIBLING_CACHE.get(str(parent))
    if n_siblings is None:
        n_siblings = len(list(parent.glob("*.als"))) if parent.exists() else 1
        _SIBLING_CACHE[str(parent)] = n_siblings

    if n_siblings <= 3:
        return "primary", "loose_few_siblings_WEAK", parent, stamp
    return "orphan", "loose_many_siblings", parent, stamp


def is_factory(path: Path) -> bool:
    s = str(path).lower().replace("/", "\\") if os.sep == "\\" else str(path).lower()
    hints = [h.replace("/", "\\") if os.sep == "\\" else h for h in FACTORY_HINTS]
    return any(h in s for h in hints)


def content_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(HASH_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def read_header(path: Path) -> tuple[dict, str, bool, str]:
    """Read the <Ableton ...> root tag without parsing the document.

    Returns (attrs, status, was_gzip, error). An uncompressed .als is legal and
    returns status "ok" with was_gzip False. Previously this returned
    "not_gzip", which the summary then counted as a read failure.
    """
    try:
        with path.open("rb") as f:
            magic = f.read(2)
        gzipped = magic == b"\x1f\x8b"
        if gzipped:
            with gzip.open(path, "rb") as f:
                head = f.read(HEADER_BYTES)
        else:
            with path.open("rb") as f:
                head = f.read(HEADER_BYTES)

        m = ABLETON_TAG.search(head)
        if not m:
            return {}, "no_header", gzipped, f"no <Ableton> tag in first {HEADER_BYTES} bytes"
        return dict(ATTR.findall(m.group(0))), "ok", gzipped, ""
    except Exception as exc:  # noqa: BLE001
        return {}, "error", False, f"{type(exc).__name__}: {exc}"


def decode(attrs: dict, key: str) -> str:
    v = attrs.get(key.encode(), b"")
    return v.decode("utf-8", "replace")


def build_row(path: Path, do_hash: bool = True) -> Row:
    kind, reason, project_dir, stamp = classify(path)
    attrs, status, gzipped, err = read_header(path)
    try:
        stat = path.stat()
        size, mtime = stat.st_size, stat.st_mtime
    except OSError:
        size, mtime = -1, 0.0

    chash = ""
    if do_hash:
        try:
            chash = content_hash(path)
        except OSError as exc:
            err = err or f"hash failed: {exc}"

    return Row(
        path=str(path),
        filename=path.name,
        kind=kind,
        classify_reason=reason,
        project_group_id=hashlib.sha1(str(project_dir).lower().encode()).hexdigest()[:16],
        project_dir=str(project_dir),
        backup_timestamp=stamp,
        is_factory_path=int(is_factory(path)),
        content_hash=chash,
        file_size=size,
        last_modified=mtime,
        live_creator=decode(attrs, "Creator"),
        major_version=decode(attrs, "MajorVersion"),
        minor_version=decode(attrs, "MinorVersion"),
        schema_change_count=decode(attrs, "SchemaChangeCount"),
        header_status=status,
        was_gzip=int(gzipped),
        header_error=err,
    )


def summarize(rows: list[Row]) -> None:
    authored = [r for r in rows if not r.is_factory_path]
    factory = [r for r in rows if r.is_factory_path]
    primary = [r for r in authored if r.kind == "primary"]
    backup = [r for r in authored if r.kind == "backup"]
    orphan = [r for r in authored if r.kind == "orphan"]

    projects = {r.project_group_id for r in primary}
    strong = [r for r in primary if r.classify_reason == "project_folder"]
    weak = [r for r in primary if r.classify_reason == "loose_few_siblings_WEAK"]
    projects_strong = {r.project_group_id for r in strong}

    dupes = Counter(r.content_hash for r in primary if r.content_hash)
    exact_dupes = sum(c - 1 for c in dupes.values() if c > 1)

    backups_per_project = Counter()
    for r in backup:
        backups_per_project[r.project_group_id] += 1

    print()
    print("=" * 62)
    print("  N")
    print("=" * 62)
    print(f"  distinct projects (the number that matters)   {len(projects):>8}")
    print(f"    from real project folders (strong)          {len(projects_strong):>8}")
    print(f"    added by the loose-file heuristic (WEAK)    {len(projects) - len(projects_strong):>8}")
    print(f"  primary sets                                  {len(primary):>8}")
    print(f"    strong: in a recognised project folder      {len(strong):>8}")
    print(f"    WEAK:   loose .als, <=3 in its folder       {len(weak):>8}")
    print(f"    of which exact duplicate copies             {exact_dupes:>8}")
    print(f"  orphan sets (loose, many siblings)            {len(orphan):>8}")
    print(f"  factory / pack sets excluded from N           {len(factory):>8}")
    if weak:
        print()
        print("  ! The WEAK count is the orphan-heuristic risk. A single stray .als in")
        print("    a non-project folder counts as a project. If WEAK is a large share")
        print("    of N, filter classify_reason in the CSV and eyeball those paths")
        print("    before treating N as real.")
    print()
    print("=" * 62)
    print("  REVISION CORPUS (Backup/, excluded from N and scoring)")
    print("=" * 62)
    print(f"  backup sets indexed                           {len(backup):>8}")
    print(f"  projects with any backup history              {len(backups_per_project):>8}")
    if backups_per_project:
        counts = sorted(backups_per_project.values())
        print(f"  backups per project  min/median/max   "
              f"{counts[0]:>5} /{counts[len(counts) // 2]:>5} /{counts[-1]:>5}")
        deep = sum(1 for c in counts if c >= 10)
        print(f"  projects with 10+ revisions                   {deep:>8}")
    print()
    print("=" * 62)
    print("  SCHEMA RANGE (determines parser scope)")
    print("=" * 62)
    vh = Counter(
        (r.major_version, r.minor_version, r.live_creator)
        for r in authored
        if r.header_status == "ok"
    )
    for (maj, minor, creator), n in sorted(vh.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>6}  Major={maj:<4} Minor={minor:<16} {creator}")
    print()

    print("=" * 62)
    print("  COVERAGE AND FAILURES (nothing is skipped silently)")
    print("=" * 62)
    uncompressed = sum(1 for r in rows if r.header_status == "ok" and not r.was_gzip)
    print(f"  files found                                   {len(rows):>8}")
    print(f"  headers read OK                               {sum(1 for r in rows if r.header_status == 'ok'):>8}")
    print(f"    of which uncompressed .als (legal)          {uncompressed:>8}")
    bad = Counter(r.header_status for r in rows if r.header_status != "ok")
    if bad:
        for k, n in bad.most_common():
            print(f"  header {k:<12}                          {n:>8}")
        print("  (listed in the CSV with header_error, not swallowed)")
    print(f"  directories that could not be read            {len(WALK_ERRORS):>8}")
    if WALK_ERRORS:
        print("  ! Each unreadable directory may hide projects. N is a LOWER BOUND.")
        for p, e in WALK_ERRORS[:10]:
            print(f"      {p}  ({e})")
        if len(WALK_ERRORS) > 10:
            print(f"      ... and {len(WALK_ERRORS) - 10} more")
    print()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Inventory Ableton .als files.")
    ap.add_argument("roots", nargs="+", help="directories to walk")
    ap.add_argument("--out", default="inventory.csv")
    ap.add_argument("--no-hash", action="store_true",
                    help="skip content hashing (much faster; disables duplicate detection)")
    args = ap.parse_args(argv)

    roots = [Path(r) for r in args.roots]
    for r in roots:
        if not r.exists():
            print(f"warning: {r} does not exist", file=sys.stderr)

    rows: list[Row] = []
    for i, path in enumerate(iter_als(roots), 1):
        rows.append(build_row(path, do_hash=not args.no_hash))
        if i % 100 == 0:
            print(f"  ...{i} files", file=sys.stderr)

    out = Path(args.out)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[fl.name for fl in fields(Row)])
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))

    summarize(rows)
    print(f"  wrote {len(rows)} rows to {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
