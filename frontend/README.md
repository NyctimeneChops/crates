# Crates — frontend

React + Vite web app for Crates. It talks to the FastAPI backend and provides
sign-up/login, a feed, a player, and journey views.

## Development

```
npm install
npm run dev      # start the Vite dev server
npm run build    # production build to dist/
```

The dev server expects the backend to be running and reachable at the URL configured
in `VITE_API_URL` (see below).

## Environment variables — never put secrets in a `VITE_` variable

Vite inlines every variable prefixed with `VITE_` into the compiled client bundle at
build time. That bundle is shipped to and readable by **every visitor** — anyone can
open the browser dev tools and read the value.

Therefore **no secret may ever go in a `VITE_` variable** — not an API key, token,
password, client secret, or connection string — regardless of what `.gitignore` says.
Keeping `frontend/.env` out of git does *not* protect a `VITE_` value; the value still
ends up in the public JavaScript bundle.

Only non-sensitive, publicly-safe configuration belongs in `VITE_` variables. Copy
`.env.example` to `.env`:

```
VITE_API_URL=http://localhost:8000
```

Anything secret must live on the backend and be read from the server-side environment
there.

## Known gaps

- **Image assets are excluded from version control pending provenance review.**
  `src/assets/hero.png`, `public/favicon.svg`, and `public/icons.svg` are gitignored:
  their origin/licensing has not been established. They remain on disk so the app
  still renders locally, but they are not tracked and will be replaced with original
  or explicitly licensed assets before any public release.
- **Third-party brand assets / SoundCloud attribution.**
  `src/assets/powered_by_soundcloud.png` is a SoundCloud brand asset, included to
  satisfy the attribution that SoundCloud's API terms require. The `Player` and
  `WitnessPlayer` components also load a "Buy Me a Coffee" button image from
  `cdn.buymeacoffee.com` at runtime. Both are third-party assets/marks; their use
  needs a compliance review before any public release.
