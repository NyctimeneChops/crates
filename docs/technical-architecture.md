# Crates: Technical Architecture

**Status:** Working spec. Derives from `synthesis.md`.
**Date:** 21 July 2026

---

## 0. How to read this document

This spec documents what was chosen **and what was rejected, with reasons**. The rejections are the more valuable half. A specification that only records decisions loses the reasoning, and six months later somebody re-proposes FL Studio and the argument gets had again from zero.

Sections 1 through 5 are components. Section 6 is platform decisions and rejected alternatives. Section 7 is the roadblock register. Section 8 is build order.

---

## 1. System overview

```
                        ┌─────────────────────────────┐
                        │      SESSION FILE           │
                        │  (.als, gzipped XML)        │
                        └──────────────┬──────────────┘
                                       │
        ┌──────────────┬───────────────┼───────────────┬──────────────┐
        │              │               │               │              │
   ┌────▼────┐   ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐  ┌────▼─────┐
   │ Local   │   │  Studio   │   │  Library  │   │  Feature  │  │  Split   │
   │ Crawler │   │ Assistant │   │ Ingestion │   │ Extraction│  │  Sheets  │
   │         │   │ + Teacher │   │           │   │           │  │          │
   └────┬────┘   └─────┬─────┘   └─────┬─────┘   └─────┬─────┘  └────┬─────┘
        │              │               │               │             │
        │         ┌────▼────┐     ┌────▼────┐     ┌────▼────┐        │
        │         │ Ableton │     │  Proxy  │     │ Crates  │        │
        │         │  Live   │     │ Renderer│     │Discovery│        │
        │         │  (LOM)  │     │         │     │         │        │
        │         └─────────┘     └─────────┘     └─────────┘        │
        │                                                             │
        └──────────────── local, never uploaded ──────────────────────┘
```

Two trust zones, and the distinction matters legally as well as technically:

- **Local zone.** The user's own sessions. The crawler and the assistant operate entirely on the user's machine. Nothing is transmitted. This zone requires no rights clearance of any kind and can ship first.
- **Shared zone.** Sessions an artist has deliberately uploaded to the Library. Everything in the shared zone passes through ingestion, proxy substitution, and rights review.

Never blur these. The local zone is the product that can ship without a lawyer. The shared zone is the product that cannot ship without one.

---

## 2. Component A: Crates Studio, the assistant

### 2.1 Integration layer

Ableton Live 11 and above exposes the Live Object Model through an internal Python remote-script interface. Two viable access paths:

| Path | Notes |
|---|---|
| **AbletonOSC** | MIDI remote script exposing the LOM over Open Sound Control. Full object hierarchy, property getters and setters, state change listeners. Installed by dropping a folder into the User Library Remote Scripts directory and selecting it as a Control Surface. **Recommended starting point.** |
| **ableton-js** | Node wrapper over a Max for Live device. More convenient in a JavaScript stack, adds a Max for Live dependency, which requires Live Suite. |
| **Direct remote script** | Writing your own Python remote script. Maximum control, maximum maintenance burden, no reason to start here. |

Available operations that matter: create and delete clips in clip slots, add and read MIDI notes, set clip length and looping, set tempo, create and rename tracks, load devices and presets from the browser (Live 11 and later), read and set device parameters, fire and stop clips, and register listeners on song, track, and clip state.

### 2.2 The intermediate representation

**The language model must never emit LOM calls.** It emits a validated JSON document; a deterministic renderer converts that document into API calls.

Rough shape:

```json
{
  "version": "1.0",
  "intent": "create_clip",
  "target": { "track": "new", "track_type": "midi", "slot": 0 },
  "clip": {
    "length_bars": 4,
    "time_signature": [4, 4],
    "grid": 16,
    "events": [
      { "pitch": 36, "start": 0.0,  "duration": 0.25, "velocity": 100 },
      { "pitch": 36, "start": 2.0,  "duration": 0.25, "velocity": 100 },
      { "pitch": 38, "start": 1.0,  "duration": 0.25, "velocity": 96  },
      { "pitch": 38, "start": 3.0,  "duration": 0.25, "velocity": 96  }
    ]
  },
  "device_intent": { "category": "drum_machine", "preference": null }
}
```

Why this matters, in order of importance:

1. **Debuggability.** When the output sounds wrong, you can inspect the IR and immediately tell whether the model misunderstood the request or the renderer misplaced the notes. Without the IR these are indistinguishable.
2. **Undo and replay.** The IR is the unit of work. Storing it gives you a mutation log independent of Live.
3. **Model portability.** Swapping models, or running a local model, requires no renderer changes.
4. **Schema validation.** Malformed output is rejected before it touches the user's session.
5. **Determinism.** The same IR always produces the same result. Generative unpredictability is confined to the language step.

### 2.3 The local grammar fast path

A deterministic parser handles the common cases with no network round trip. Target coverage: grid placement by beat, standard subdivisions, simple transposition, velocity ramps, length and loop changes, tempo.

```
"kick on 1 and 3"                → grammar, ~0ms
"snare on 2 and 4"               → grammar, ~0ms
"hats on every 8th"              → grammar, ~0ms
"make it feel more like a shuffle" → model fallback
```

This is not an optimization. The entire product thesis is friction removal, and a language model round trip on a trivial grid request reintroduces exactly the friction the product exists to eliminate. Parse first, escalate on failure.

### 2.4 The snapshot layer

**Non-negotiable, build on day one.**

Live's undo stack does not capture mutations made through the API. This is documented behavior and other projects building on this interface warn explicitly that AI manipulation of clips can destroy existing notes irrecoverably.

Before any mutation:
1. Read the full note array of every clip in scope.
2. Store it, keyed to the IR document that is about to be applied.
3. Apply.
4. Expose an in-product undo that restores from the snapshot.

Never allow a user to lose work in their own session. One occurrence of this destroys the trust the whole company runs on.

### 2.5 Input

Push-to-talk voice, not typing, as the primary modality. Typing while an idea is in your hands is itself friction. Typing remains available.

---

## 3. Component B: the local crawler

The cheapest high-value component in the system. Ships first. Requires no permission, no server, and no legal review.

### 3.1 Parsing

`.als` files are gzipped XML. Decompress, parse the tree, extract:

- Sample file references and their resolved paths
- Device and plugin identifiers per track
- Track count, type, naming, grouping
- Tempo, time signature, key where set
- Clip inventory and lengths
- Mute, solo, and arm state
- Automation presence per parameter

### 3.2 The weighting problem

**Frequency of loading is not frequency of preference.** A sample appearing on a muted track in two hundred sessions is not a favorite; it is residue.

Weight by evidence of intent:
- Did the track survive to the end of the session?
- Was it unmuted?
- Did it have automation written on it?
- Did it have processing applied?
- Did it appear in the arrangement, or only in Session view?

The resulting metric should approximate "sounds this artist actually committed to" rather than "sounds this artist opened."

### 3.3 Revision diffing

If revision-saved sets exist (`Project v1.als`, `v2`, `v3`), diffing them yields something nobody else has: **what gets deleted, and how early.** The subtractive history of a track is arguably more revealing than the additive one. Opportunistic, not required.

### 3.4 Path reconciliation

Sample references store paths plus relative hints and break when libraries move. Expect fuzzy reconciliation by filename, file size, and audio hash. Plan for a meaningful unresolved rate and surface it honestly rather than silently dropping.

### 3.5 Output

The "shape of your taste" report. Top sounds by weighted usage, category distribution, the concentration curve showing what fraction of the library does what fraction of the work, and unused regions of the library. This is the artifact that makes a producer feel something, and it runs without Ableton even being open.

---

### 3.6 Amendment, 2026-07-25: the settled crawler design

Sections 3.1 to 3.5 were written on 2026-07-21 and describe the crawler at the
level it had been thought through then. The design was carried considerably
further in conversation afterwards and was never written back here, so it
survived only in a session handoff document. This section closes that gap.

Where this section and 3.1 to 3.5 disagree, this section is later and wins. The
specific supersessions are noted inline.

#### 3.6.1 The primary output is a category-scoped ranking

Kicks compete with kicks, pads with pads, devices with devices. A global ranking
over an undifferentiated asset pool answers a question nobody asked. This follows
the original framing: "organize all my drum sounds by the ones I actually use
most." The global concentration curve remains, as a secondary summary.

Samples and devices never share a ranking. The taxonomy is two levels, family and
type; ranking is scoped at type with family as the rollup.

#### 3.6.2 Scoring: gated presence as the base, bounded bonuses to differentiate

**Supersedes 3.2.** Audible or timeline extent was rejected as a base signal
because it measures sustain and density, which track instrument *role* rather
than commitment, and the bias is systematic: pads score high for doing nothing
and a defining one-shot scores low. If a continuous base is wanted, use section
coverage rather than timeline extent.

- **Base:** presence, gated. Section coverage is binary per section (an asset
  counts a section if it sounds anywhere within it), normalised by `n_sections`.
  For sessions without locators, divide the arrangement into a fixed number of
  equal-duration bins as pseudo-sections.
- **Gate to zero:** every instance muted, or the asset present only on a track
  holding no clips.
- **Bonuses, each bounded and additive:** automation on the track or on a device
  parameter in its chain; non-default downstream processing; the track renamed
  from Ableton's default, a small deliberate act that correlates with intent; the
  clip worked rather than dropped (warp markers moved, transposed, non-zero start
  offset, length differing from source).
- **Aggregation:** per-session score capped at 1, then summed across sessions,
  because a favourite is something reached for across many projects rather than
  used forty times in one. Report breadth (count of sessions above a threshold)
  as a column separate from depth (summed score). Where they disagree is
  interesting output, not noise.

**"Survived to end of session" is dropped from v1.** It is listed in 3.2 and it
is not observable from a single saved `.als`: a saved set is the end state, so
everything visible survived by definition. It returns only under revision
diffing.

#### 3.6.3 Two problems the parser must solve rather than defer

**Backup folders.** Ableton auto-creates a `Backup/` subdirectory of timestamped
saves in every project. A naive drive walk finds them all, inflating N by an
order of magnitude and polluting the concentration curve with near-duplicate
snapshots that content hashing will not dedupe. Do **not** simply exclude them.
They are a free automatic revision history, which is exactly the opportunistic
corpus 3.3 describes. Treat them as a distinct class: excluded from N and from
scoring, retained and indexed.

**Drum Racks, Instrument Racks, and multi-sample instruments.** A Drum Rack sits
on one track and holds many samples across chains. At (session, track, asset)
grain every pad inherits identical track-level signals, and unplayed pads from a
loaded preset score as present. That breaks the flagship "which drums do I
actually use" output entirely. Presence must resolve at chain level: a sample
counts only if MIDI notes in the track's clips trigger its chain, via the chain's
receive note range. Note count per pad is also a better presence signal than
anything available at track level. This likely needs a nullable `chain_id` on the
occurrences grain.

**Chain resolution is not a refinement. It is the parser's main job for the
flagship output.**

#### 3.6.4 Categorisation: a precedence cascade

Each assignment logs which rule fired and at what specificity, so failures are
auditable.

1. Manual override file (`category_overrides.yaml`, matching content hash or path
   glob). Always wins. This is the correction loop, not a fallback.
2. Device identifier lookup. Native Ableton devices are enumerable and exact;
   third party via a maintained name map.
3. Path heuristics. Directory tokens against a keyword lexicon, deepest match
   winning. Sample packs curate folders, so this carries most of the load.
4. Filename patterns. Tokenise, strip BPM/key/index, match the lexicon plus
   standard abbreviations (BD, SD, CH, OH, HH).
5. Length and warp heuristic, separating one-shot from loop within a family.
6. Unknown, **sorted by weighted score**, so the roughly twenty hand-written
   overrides are the twenty that actually move the output. The tail is never
   triaged.

`recorded` (self-recorded and render directories) is separated early, because it
makes the eventual third-party classification problem tractable. Publish the
coverage number in the README: "78% auto-categorised, 14% override, 8% unknown"
is itself a result. Audio-based classification is deferred to v2, in writing, so
that it reads as a decision rather than an omission.

#### 3.6.5 Schema: five tables, Parquet on disk, small CSV extract in `sample-output/`

- `crawl_runs` — the honesty layer. Tool, lexicon and weight-config versions,
  supported version range, files found, parsed, skipped-unsupported, parse-failed.
  Nothing skipped silently.
- `sessions` — per set. Version, schema variant, parse status and error,
  `project_group_id` (collapses v1/v2/v3 into one project and enables revision
  diffing), track count, `has_arrangement`, `has_locators`, `n_sections`, tempo,
  time signature.
- `assets` — per sample or device. Identity basis, hashes and identifiers,
  resolution status, category family, type, method, specificity, conflict.
- `occurrences` — the long-format fact table at (session, track, asset) grain,
  likely plus `chain_id`. Track name and whether default, clip counts,
  `in_arrangement`, `sections_covered`, mute and solo, automation presence and
  parameter count, downstream device count, non-default processing, clip-edit
  flags. Track grain rather than session grain, so note-level features attach
  later without a migration.
- `scores` — a derived view at (session, asset), recomputed rather than stored by
  hand: gated, `base_presence`, `section_coverage`, the bonus terms, and C.

**Separating `scores` from `occurrences` is what makes the sensitivity sweep
cheap:** parse once, then recompute scores hundreds of times against different
weight configs without touching an `.als` again.

Category rankings and the concentration curve are both views over `scores` joined
to `assets`. Neither is a pipeline.

#### 3.6.6 Calibration, which is what makes it a result

There is no ground truth, so a reviewer will say the weights were chosen to
produce the answer. Preempt it. Weights live in a config file, and a **sensitivity
sweep** randomises them within bounds a few hundred times and reports rank
stability of the top 50. If the concentration curve holds its shape and the top of
the ranking barely moves, the finding is about the library rather than the
weighting. If it does not hold, that is also a finding and is stated.

README framing discipline: the output is an **ordinal ranking of commitment**,
never a *measure of preference*.

#### 3.6.7 The shared extraction point

The crawler and the offline imputation study want the same feature-extraction
layer and the same long-format table. Build the table first; the crawler report is
a view over it. `scores` needs session-level aggregates for the study, and the
perceptual versus process-only split (5.4) is a column tag on the asset table,
not a second pipeline.

#### 3.6.8 Step 0: `inventory.py`

Walks for `*.als`, classifies each as primary, backup, or orphan, reads only the
`<Ableton ...>` gzip-header tag for version attributes, content-hashes files,
flags factory and pack paths separately, and prints N, the revision corpus, and
the schema histogram.

Run it against actual music and project directories, not a full `C:\` walk, which
is slow and mostly empty. Before N means anything, check the orphan heuristic (the
script now labels weak classifications explicitly and reports them as a separate
count) and confirm the backup-timestamp regex holds for older Live versions.

The two numbers gate everything downstream. If the version histogram is one or two
versions wide, the parser is a normal afternoon. If it spans Live 9 through 12,
scope v1 to the dominant version and report the skipped count. Eyeball
backups-per-project too: a median of two means the revision corpus is thin and
stays opportunistic, a median of twenty means it is a real dataset that may deserve
to move up the build order.

---

## 4. Component C: Library ingestion

Only touches the shared zone. Gated on counsel and on formation.

### 4.1 Third-party asset handling

**This is the sharpest technical and legal problem in the system.**

An uploaded session is not only the artist's work. It contains sample pack one-shots, purchased loops, and library content, each carrying its own license. Many sample library agreements license to the purchaser and prohibit redistribution in extractable form. An artist granting educational transcription rights grants the rights that artist holds, and the artist does not hold rights to the loop on track seven.

Pipeline:

1. **Identify** every audio asset referenced in the session.
2. **Classify** each as artist-original (recorded or rendered by them), third-party licensed (matched against known library hashes and path signatures), or unknown.
3. **Substitute.** Third-party and unknown assets are replaced with neutral proxy sounds drawn from a Crates-owned proxy kit, matched by category and rough spectral profile.
4. **Preserve** all placement, timing, velocity, length, and automation exactly.
5. **Flag** anything unclassifiable for human review rather than defaulting to inclusion.

The student receives the pattern, never the sound. This is legally necessary and pedagogically correct: the lesson is where the notes are.

### 4.2 The A/B mechanism

The learner toggles between the artist's finished master and the proxy reconstruction. This is the core pedagogical loop of the Library and the reason the master must be streamable in the closed loop even though the proxy carries the instruction.

### 4.3 The closed loop and tagging

Material enters a user's DAW only through the service. Every delivered item carries a service tag. The Studio plugin refuses to analyze untagged material.

This solves provenance by controlling the pipe rather than by inspecting audio. Note explicitly why the alternative fails: audio fingerprinting can identify *what* a recording is; it cannot determine how the user obtained it. Provenance is not recoverable from the waveform.

**Export prevention is not claimed.** On a local machine with audio routing, preventing capture is unenforceable and any counterparty's lawyers will know it. The mitigation is architectural where possible (server-side analysis returning only MIDI and metadata for some flows) and contractual otherwise.

### 4.4 Rights review

Automated first pass: fingerprint against known commercial recordings, query public works databases, check ISRC and ISWC where present. Then a rights questionnaire at upload, warranties and indemnification in the artist agreement, and human review of flags.

**Split the flow so clearance never blocks the artist:** upload and private analysis are instant; publication to the shared Library passes through clearance. A multi-week gate at the moment an artist is most excited is a product-killing delay if it blocks everything.

---

## 5. Component D: feature extraction into discovery

### 5.1 What sessions yield

Features not derivable from a master with any reliability: exact quantization and deviation from grid, layer counts per element, arrangement section boundaries and lengths, automation density and shape, device chain topology, note-level velocity distributions, and the subtractive history if revisions exist.

### 5.2 The coverage problem

Audio features exist for the entire catalog. Session features exist only for uploaded sessions. The feature matrix is mostly holes and most methods handle that badly.

### 5.3 The imputation move

**This is the highest-value idea in the component and possibly in the company.**

On the subset with both audio and session data, train a model to predict session-derived attributes from audio alone. Sessions provide ground-truth labels for properties that would otherwise have to be inferred. Then apply the trained model to the entire catalog.

Consequences:
- A few thousand sessions improve analysis for millions of tracks that will never have a session uploaded.
- The cold start problem stops being fatal, because corpus value no longer scales linearly with upload count.
- It is a publishable research contribution in its own right.

### 5.4 Sorting features by relevance

Split session-derived features on a single axis before using them:

- **Perceptual analogues** (groove deviation, arrangement density, layer count, dynamic range): plausibly relevant to listener experience. Candidates for the discovery model.
- **Process-only** (which plugin, which folder a sample came from, naming conventions): almost certainly noise for discovery, and gold for education and collaboration matching.

Pandora's Music Genome attributes were chosen because they are perceptually relevant. Session features are process-relevant by default. The sorting step is what bridges them.

### 5.5 The honest constraint

Crates is deliberately designed with isolated journeys and no global taste profile. That is a principled choice and it means less behavioral signal accumulates per user than in a conventional recommender. Which pushes the architecture toward content-based methods over collaborative filtering, which in turn makes rich features *more* important, not less. The design philosophy and the feature strategy are consistent. They also mean the harder recommender problem was chosen deliberately, and research time should be priced accordingly.

---

## 6. Platform decisions and rejected alternatives

### 6.1 Ableton Live: chosen

Full Live Object Model access through a documented-enough Python remote script interface. Browser access for programmatic device loading in Live 11 and later. State listeners for the teaching mode. An existing open-source ecosystem to build on rather than from scratch.

### 6.2 FL Studio: rejected, with reasons

FL Studio's Python API is split across two contexts and neither supports the product.

**MIDI controller scripting:** event-driven, designed for hardware surfaces. Modules for transport, mixer, channel rack, step sequencer grid bits, and plugin parameters.

**Piano roll scripting:** can create and modify notes, but runs once when the user invokes it from the Scripts menu, is restricted to the Python standard library with no external imports, and has minimal dialog capability.

Documented limitations that are individually fatal here:

| Limitation | Why it kills the product |
|---|---|
| Cannot load VST or AU plugins programmatically | The assistant cannot set up an instrument |
| Cannot create patterns programmatically | The assistant cannot create the container the notes go in |
| Piano roll scripts require a keystroke to invoke | Replaces friction with different friction |
| No external library imports | Cannot use a validation or networking stack in-process |

The teaching mode is worse off still: the two skills most worth teaching first (create a track, load an instrument) are exactly the two the API cannot perform.

**Revisit trigger:** Image-Line expands the API to cover pattern creation and plugin loading. Track their release notes. The genre demographic argument for FL is real and worth returning to.

### 6.3 REAPER: internal bench only

ReaScript offers far deeper control and in-app UI, which makes it the cheapest place to prototype the teaching mode's interaction design. It is illegible on camera; a demo in a DAW the audience does not recognize quietly undermines the demo. Prototype where it is cheap, ship and film where it is recognized.

### 6.4 Max for Live: not the primary path

The sanctioned extension route, but sandboxed and requiring Live Suite. Useful for specific devices, not as the integration backbone.

### 6.5 Platform risk, stated plainly

Ableton's remote script interface is undocumented and tolerated, not supported. There is no official API for custom UI panels inside Live. A commercial product on this foundation exists at Ableton's discretion and can break on any point release. This is a real business risk and belongs in every investor conversation rather than being discovered in one.

---

## 7. Roadblock register

| ID | Roadblock | Severity | Status | Mitigation |
|---|---|---|---|---|
| T-01 | API mutations bypass Live's undo | Critical | Solved by design | Snapshot layer, section 2.4 |
| T-02 | Live's UI state is not exposed by the LOM (no cursor, focus, or panel state) | High | Deferred | v1 uses result detection, not input interception. v2 requires a perception layer. |
| T-03 | Live is custom-drawn, so the macOS accessibility tree is sparse | High | Open | The v2 perception layer likely needs computer vision or a vision model on screenshots. Latency and cost unknown. This is the real engineering hire. |
| T-04 | Third-party samples inside uploaded sessions | Critical | Design solved, legally open | Proxy substitution, section 4.1. Needs counsel sign-off. |
| T-05 | Sample path references break when libraries move | Low | Accepted | Fuzzy reconciliation; surface unresolved rate honestly |
| T-06 | Ableton may break the remote script interface | Medium | Accepted | Version pinning, fast patch cadence, disclosed as risk |
| T-07 | Cold start on session corpus | High | Mitigated | Imputation model, section 5.3 |
| T-08 | Export prevention is unenforceable | Medium | Accepted | Architectural where possible, contractual otherwise; never claimed to counterparties |
| T-09 | Model latency violates the friction thesis | High | Solved by design | Local grammar fast path, section 2.3 |
| T-10 | Session upload is high-friction (large files, artists are protective of unfinished work) | High | Open | No mitigation designed yet. This is the biggest unaddressed product risk in the system. |

T-10 deserves emphasis. Artists share finished tracks freely and guard sessions, because a session is the unfinished, revealing version. The upload ask is far larger than it appears and no mitigation has been designed. Candidate directions: selective upload (one section, one instrument), local-first analysis with upload as an explicit second step, or making the crawler's personal value so high that upload becomes the natural next step rather than an act of charity.

---

## 8. Build order

Each step is independently useful and gated only on the one before it.

**1. The crawler.** Local, no server, no legal review, days of work. Produces the shape-of-your-taste report.

**2. The offline feature experiment.** Using existing Essentia analysis on the current catalog plus whatever session data is available, test whether production-decision similarity predicts listener co-liking better than audio similarity alone. Either justifies the discovery claim or redirects it toward education and collaboration matching. See risk register R-19. NOTE 2026-07-25: BLOCKED until there is a real user base; with one user there is nothing to correlate. It is not, as sometimes stated, replaced by the imputation study (step 9), which serves a different risk (R-08, cold start). Both remain live.

**3. The assistant, end to end, hardcoded.** AbletonOSC plus a script. Prove text to audible clip. Snapshot layer included from the first commit.

**4. The IR, renderer, and local grammar.** Turn the hardcoded proof into an architecture.

**5. Teaching mode, one lesson.** Environmental constraint plus result detection. One complete prompt hierarchy, one fading protocol, per `pedagogy.md`.

**6. The demo.** Songwriters on camera. Requires nothing from step 7 onward.

**7. Formation, counsel, artist agreement.** Before any third-party upload.

**8. Library ingestion.** Proxy substitution, rights review, closed-loop tagging.

**9. Feature pipeline into discovery.** Including the imputation model.

**10. Split sheets.**

**11. The perception layer and true errorless mode.** Requires a systems hire. The demo from step 6 is the recruiting instrument.

---

## 9. Open technical questions

1. What is the actual accuracy ceiling on classifying third-party versus artist-original audio inside a session, and what is the human review load at scale?
2. Does the imputation model in 5.3 work well enough to be worth building? Needs a pilot on a small paired dataset.
3. Can the v2 perception layer be built from Live's accessibility tree at all, or is vision mandatory? A day of investigation would settle it.
4. What is the minimum viable corpus size for the Library to be pedagogically useful? Fifty sessions or five thousand?
5. Does result detection cover enough of the teaching curriculum, or are there skills where the absence of input blocking makes the lesson incoherent?
6. What is the storage and bandwidth profile of session uploads at scale, and does it change the economics?
