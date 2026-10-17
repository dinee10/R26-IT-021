# Two-day mobile demo deployment

The Flutter app now uses one build-time `API_BASE_URL` for every backend feature.
Pass the public origin only; both `https://example.com` and
`https://example.com/api` are accepted and normalized.

## Option 1: Railway

1. Commit and push the repository, including the previously ignored
   `backend/chroma_db_bilingual_refs_test/` directory. It contains the prepared
   vector index used by the knowledge assistant.
2. In Railway, create a project from the GitHub repository.
3. Set the service **Root Directory** to `/backend`. Railway will read
   `backend/railway.json` and build `backend/Dockerfile`.
4. Add this Railway variable:
   - `OPENAI_API_KEY`: the backend's OpenAI key. Never put it in Flutter or Git.
5. Generate a public Railway domain and wait for this URL to respond:
   `https://YOUR-DOMAIN.up.railway.app/api/health`.
6. Build the APK from the repository root:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\frontend\build-demo-apk.ps1 -ApiBaseUrl "https://YOUR-DOMAIN.up.railway.app"
   ```

The Railway trial has a 1 GB memory ceiling. This backend loads TensorFlow,
YOLO/PyTorch, and Chroma, so watch the Railway memory graph while testing. The
container deliberately runs one server worker to avoid duplicating the models
in memory. If Railway stops it for exceeding memory, use the tunnel option for
the demo or move to a larger-memory service.

## Option 2: Cloudflare Quick Tunnel

Install `cloudflared` once. Then open two PowerShell terminals.

Terminal 1:

```powershell
cd D:\Projects\R26-IT-021\backend
powershell -ExecutionPolicy Bypass -File .\start-local-demo.ps1
```

Terminal 2:

```powershell
cd D:\Projects\R26-IT-021\backend
powershell -ExecutionPolicy Bypass -File .\start-cloudflare-tunnel.ps1
```

The second command prints a temporary URL similar to
`https://random-words.trycloudflare.com`. Build the APK with it:

```powershell
powershell -ExecutionPolicy Bypass -File .\frontend\build-demo-apk.ps1 -ApiBaseUrl "https://random-words.trycloudflare.com"
```

Keep the computer, backend terminal, tunnel terminal, and internet connection
running throughout the demo. A Quick Tunnel URL changes when it is restarted,
so a new URL requires a new APK build.

## Verification

Before installing the APK, open these endpoints in a browser:

```text
PUBLIC_URL/
PUBLIC_URL/api/health
```

The root should report that the backend is running. The health endpoint may say
`degraded` when a model artifact or dependency is unavailable; inspect its JSON
fields before proceeding. Test identification, quality assessment,
recommendations, and chat from the APK before the presentation.
