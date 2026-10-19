"""Production entry point for the AyurPlant backend.

The server intentionally listens on loopback by default. Cloudflare Tunnel runs
on the same computer and forwards requests to this private origin, so opening an
inbound firewall port is unnecessary.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, not {raw_value!r}.") from exc
    if value < 1:
        raise SystemExit(f"{name} must be greater than zero.")
    return value


def _enabled(name: str, default: bool = True) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    # Use an explicit path so startup works from the repository root, Task
    # Scheduler, or a Windows service with a different working directory.
    load_dotenv(BACKEND_DIR / ".env")

    from waitress import serve

    from app.main import app
    from app.routes.api import preload_backend_models

    host = os.getenv("BACKEND_HOST", "127.0.0.1").strip()
    port = _positive_int("BACKEND_PORT", 5000)
    threads = _positive_int("BACKEND_THREADS", 4)
    channel_timeout = _positive_int("BACKEND_CHANNEL_TIMEOUT", 240)

    print("Starting AyurPlant backend with Waitress")
    print(f"Origin: http://{host}:{port}")
    print(f"Threads: {threads}")

    if _enabled("PRELOAD_ML_MODELS"):
        print("Preloading ML models (this only happens once at startup)...")
        preload_results = preload_backend_models(
            include_all=_enabled("PRELOAD_ALL_ML_MODELS", default=False)
        )
        for model_name, result in preload_results.items():
            print(f"  {model_name}: {result}")

    serve(
        app,
        host=host,
        port=port,
        threads=threads,
        channel_timeout=channel_timeout,
        clear_untrusted_proxy_headers=True,
        expose_tracebacks=False,
        ident="AyurPlant",
    )


if __name__ == "__main__":
    main()

