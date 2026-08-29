from flask import Blueprint, request, jsonify

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "message": "Backend is working"})

@bp.route('/ask', methods=['POST'])
def ask():
    """Placeholder for RAG Chatbot - You will implement this in your branch"""
    data = request.get_json()
    query = data.get('query', '') if data else ''
    
    return jsonify({
        "answer": "This is a placeholder response. RAG functionality will be added in feature/rag branch.",
        "query": query,
        "sources": []
    })