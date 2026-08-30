import sys
from pathlib import Path

if __package__ in (None, ''):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from flask import Flask
from flask_cors import CORS
from app.routes.api import bp as api

app = Flask(__name__)
CORS(app)

# Register blueprint
app.register_blueprint(api, url_prefix='/api')

@app.route('/')
def home():
    return {"message": "🌿 Herbal Knowledge Assistant Backend Running!"}

if __name__ == "__main__":
    app.run(debug=True, port=5000)
