# Host the AyurPlant backend from a Windows PC with Cloudflare Tunnel

This setup keeps the Flask origin on `127.0.0.1:5000`. Only `cloudflared` can
reach it, so no router port forwarding or inbound Windows Firewall rule is
required.

## 1. Prepare the Python environment

From PowerShell in the repository root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Keep secrets in `backend/.env`. Use `.env.example` as the list of supported
settings. At minimum, provide `OPENAI_API_KEY` and a strong
`EXPERT_REVIEW_KEY`. Before the Flutter website is published, replace the
example `ALLOWED_ORIGINS` values with its exact HTTPS origins.

## 2. Start and verify the private origin

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\windows\Start-Backend.ps1
```

In a second PowerShell window:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\windows\Test-Backend.ps1
```

Waitress is used instead of Flask's development server. The server binds only
to loopback unless `BACKEND_HOST` is deliberately changed.

## 3. Create a stable named tunnel

The domain must use Cloudflare DNS. Run these commands with a current
`cloudflared.exe`:

```powershell
cloudflared.exe tunnel login
cloudflared.exe tunnel create ayurplant-api
cloudflared.exe tunnel route dns ayurplant-api api.example.com
```

Cloudflare creates a UUID and a matching JSON credentials file under
`$env:USERPROFILE\.cloudflared`. Do not copy either credential into this
repository.

Copy `deploy\cloudflare\config.yml.example` to
`$env:USERPROFILE\.cloudflared\config.yml`, replace the tunnel UUID,
credentials path, and hostname, and test it interactively:

```powershell
cloudflared.exe tunnel ingress validate
cloudflared.exe tunnel run ayurplant-api
```

Then verify the public endpoint:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\windows\Test-Backend.ps1 -BaseUrl https://api.example.com
```

The configuration forces HTTP/2 because this PC's previous connectivity logs
showed that outbound QUIC/UDP 7844 was blocked while TCP/HTTP2 succeeded.

## 4. Configure automatic startup

Both the backend and tunnel must start after a reboot, and the PC must be set
not to sleep while hosting.

For Cloudflare Tunnel, follow Cloudflare's Windows service procedure. Its
service runs as `LocalSystem`, so copy the final `config.yml` and tunnel JSON
credential to:

```text
C:\Windows\System32\config\systemprofile\.cloudflared\
```

Install `cloudflared.exe` under `C:\Cloudflared\bin`, install the service from
an Administrator terminal, and configure its service command to use the copied
configuration:

```text
C:\Cloudflared\bin\cloudflared.exe --config=C:\Windows\System32\config\systemprofile\.cloudflared\config.yml tunnel run
```

Run the backend with Windows Task Scheduler at system startup using:

```text
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Projects\R26-IT-021\backend\deploy\windows\Start-Backend.ps1"
```

Set the task to restart after failure. Do not run a second backend instance if
port 5000 is already occupied.

## 5. Operational checks

- Keep Windows, Python dependencies, and `cloudflared` updated.
- Prevent sleep/hibernation while the service must remain available.
- Back up `backend/data/verifications` or set `VERIFICATION_DATA_DIR` to a
  separately backed-up directory.
- Monitor `C:\Cloudflared\cloudflared.log` and the backend task output.
- Do not enable Cloudflare caching for `/api/*` responses.
- The public hostname is an API. Do not place an interactive Cloudflare Access
  login in front of it because the Android client cannot complete that flow.
