from app.main import app

if __name__ == "__main__":
    print("🌿 Starting Herbal Knowledge Assistant...")
    print("URL → http://127.0.0.1:5000")
    app.run(debug=True, port=5000)