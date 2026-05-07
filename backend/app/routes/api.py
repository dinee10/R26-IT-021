from flask import Blueprint, request, jsonify
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

api = Blueprint('api', __name__)

# Load once when module is imported
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = Chroma(persist_directory="chroma_db_free", embedding_function=embeddings)
llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0.1,      # Very important - was 0.3
    max_tokens=800
)

@api.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    query = data.get('query', '').strip()

    if not query:
        return jsonify({"error": "Query is required"}), 400

    # Retrieval
    docs = vectorstore.similarity_search(query, k=6)
    context = "\n\n".join([doc.page_content for doc in docs])

    prompt = f"""You are a highly accurate Sri Lankan Ayurvedic expert. 

**Strict Rules:**
- Answer **only** based on the given context.
- Never mix different plants. If user asks about අඩතොඩ, only talk about අඩතොඩ.
- If the context does not contain the answer, You don't have enough information.
- Be consistent every time.

Context:
{context}

Question: {query}

Answer:"""

    try:
        response = llm.invoke(prompt)
        return jsonify({"answer": response.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500