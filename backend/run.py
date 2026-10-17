import os

from app.main import app

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    print("Starting Herbal Knowledge Assistant...")
    print(f"URL: http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)

