# Crates

Crates is an early experiment in music discovery: a backend that ingests tracks from
SoundCloud and a web app that plays sequences of them ("journeys") while a
recommendation engine suggests what to play next. It is a research prototype built and
used by one person — its author.

## Status

Early research repository. Nothing here is production-ready, and there is exactly one
user (the author). The code runs, but it has not been hardened, load-tested, or
validated against real usage beyond that single user. Treat everything as provisional.

## What works today

- A **FastAPI backend** that runs locally: authentication (JWT), a tracks API, and a
  journeys API for recording and replaying listening sessions.
- **SoundCloud ingestion**: tracks can be pulled from SoundCloud into a PostgreSQL
  database. The current catalog is small (on the order of dozens of tracks).
- A **recommendation pipeline** (scoring, next-track selection, tag normalization,
  co-like signals, an audio-feature analyzer) that runs over that catalog.
- A **React frontend** with sign-up/login, a feed, a player, and journey views.
- Configuration is read from the environment; there are no credentials in the code.

## What does not work yet

This is the honest part, and it is the longest section on purpose.

- **Scale.** The catalog is tiny (dozens of tracks, not a real library). Nothing here
  has been run against a large catalog, and the ingestion path is largely manual.
- **The crawler is not built.** `crawler/` is an empty stub. There is no automated,
  large-scale catalog discovery yet.
- **The discovery-correlation experiment is not built and is blocked.** `experiment/`
  is a stub. The experiment needs behavioural data from a real user base to test
  whether the recommendation signals correlate with listening behaviour, and there is
  no such user base — there is one user.
- **The studio integration is not built.** `studio-prototype/` is a stub. The intended
  integration target is Ableton Live, but no prototype exists.
- **Session upload has no designed solution.** Getting session files out of a DAW and
  into the product is an unsolved UX problem, not a built feature.
- **No validated recommendation quality.** The pipeline produces suggestions, but there
  is no evidence yet that they are good — that is exactly what the blocked experiment
  is meant to find out.
- **Not deployment-hardened.** There is a `Procfile`, but no production configuration,
  monitoring, or security review has been done for real-world deployment.
- **No contribution mechanism** for any planned vendor/registry component.

## Repository layout

```
backend/            FastAPI app: api/, algorithm/, db/, soundcloud/
  db/config.py      get_database_url() — reads DATABASE_URL from the environment
  scratch/          throwaway one-off scripts (gitignored; README is tracked)
frontend/           React + Vite web app
crawler/            (stub) planned catalog crawler
experiment/         (stub) planned offline discovery-correlation experiment
studio-prototype/   (stub) planned Ableton Live integration prototype
sample-output/      (placeholder) sample outputs, charts, figures
docs/               synthesis.md, technical-architecture.md, pedagogy.md
ops/lab_notebook/   append-only decision & experiment log (CR-001, ...)
```

Configuration lives in `backend/.env` (never committed). Copy `backend/.env.example`
to `backend/.env` and fill it in to run the backend.

## Docs

- [docs/pedagogy.md](docs/pedagogy.md) — the teaching/learning design.
- [docs/synthesis.md](docs/synthesis.md) — the overall product thesis.

## License

All rights reserved. This repository is public for transparency and review. No license
to use, copy, modify, or distribute is granted.
