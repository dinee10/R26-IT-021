from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"],
)  # Allow frontend to connect

# Register routes
from app.routes.api import bp as api_bp
app.register_blueprint(api_bp)

@app.route('/')
def home():
    return {"message": "Herbal Knowledge AI Backend is running!"}

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
