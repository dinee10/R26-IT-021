import os

from flask import Flask, jsonify
from flask_cors import CORS
from app.routes.api import api

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(
    os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024))
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]
CORS(
    app,
    resources={r"/api/*": {"origins": allowed_origins}},
    supports_credentials=False,
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "OPTIONS"],
)

# Register blueprint
app.register_blueprint(api, url_prefix='/api')


@app.errorhandler(413)
def upload_too_large(_error):
    max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return jsonify({"error": f"Upload is too large. Maximum request size is {max_mb} MB."}), 413


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(_error):
    return jsonify({"error": "Method not allowed."}), 405


@app.errorhandler(413)
def upload_too_large(_error):
    max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return jsonify({"error": f"Upload is too large. Maximum request size is {max_mb} MB."}), 413


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(_error):
    return jsonify({"error": "Method not allowed."}), 405

@app.route('/')
def home():
    return {"message": "🌿 Herbal Knowledge Assistant Backend Running!"}

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
