from flask import Blueprint, request, jsonify
from conversation_rag import ask_question, clear_conversation

api = Blueprint('api', __name__)

@api.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    query = data.get('query', '').strip()
    session_id = data.get('session_id', 'default')
    user_context = data.get('user_context', {})

    if not query:
        return jsonify({"error": "Query is required"}), 400

    try:
        result = ask_question(
            user_question=query,
            session_id=session_id,
            user_context=user_context
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/clear', methods=['POST'])
def clear():
    data = request.get_json()
    session_id = data.get('session_id', 'default')
    clear_conversation(session_id)
    return jsonify({"message": "Conversation history cleared"})