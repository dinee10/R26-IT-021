from flask import Flask
from flask_cors import CORS
from app.routes.api import api

app = Flask(__name__)
CORS(app)

# Register blueprint
app.register_blueprint(api, url_prefix='/api')

@app.route('/')
def home():
    return {"message": "🌿 Herbal Knowledge Assistant Backend Running!"}

if __name__ == "__main__":
    app.run(debug=True, port=5000)