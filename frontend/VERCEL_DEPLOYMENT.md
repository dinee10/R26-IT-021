# Deploy the Flutter web application to Vercel

The Vercel project must use `frontend` as its **Root Directory**. The included
`vercel.json` installs Flutter 3.41.9 during the build, produces `build/web`,
and configures the fallback rewrite required by a single-page application.

## Required environment variable

Create this variable for Production and Preview in the Vercel project:

```text
API_BASE_URL=https://api.example.com
```

Use the backend origin only, without `/api` and without a trailing slash. The
build also accepts the former `/api` form and normalizes it, but using the
origin form keeps the configuration clear.

The current temporary development tunnel can be used for a preview build:

```text
API_BASE_URL=https://happen-fully-counts-nominations.trycloudflare.com
```

Do not use a `trycloudflare.com` URL for the production deployment. It changes
when the tunnel process restarts. Replace it with the named Cloudflare Tunnel
hostname before promoting the Vercel project to production.

## Vercel dashboard settings

1. Import this Git repository in Vercel.
2. Set **Root Directory** to `frontend`.
3. Set **Framework Preset** to `Other`.
4. Add `API_BASE_URL` to Preview and Production.
5. Deploy. The remaining build and output settings come from `vercel.json`.

Flutter web compiles `API_BASE_URL` into the browser application at build time.
Changing it in Vercel therefore requires a new deployment.

After Vercel assigns the final site hostname, add its exact HTTPS origin to
`ALLOWED_ORIGINS` in `backend/.env`, separated by commas when there is more
than one origin, and restart the backend.

Also open Firebase Console, go to **Authentication > Settings > Authorized
domains**, and add the final `<project>.vercel.app` hostname and any custom web
domain. This is required for Firebase Authentication and Google sign-in to work
from the deployed site.
