from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vectorstore = Chroma(persist_directory="chroma_db_free", embedding_function=embeddings)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.15,
    max_tokens=700,
    model_kwargs={"frequency_penalty": 0.9, "presence_penalty": 0.7}
)

conversation_store = {}

# --- Persona-adaptive response configuration ---from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vectorstore = Chroma(persist_directory="chroma_db_free", embedding_function=embeddings)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.15,
    max_tokens=700,
    model_kwargs={"frequency_penalty": 0.9, "presence_penalty": 0.7}
)

conversation_store = {}

#Persona-adaptive response configuration 
PERSONA_INSTRUCTIONS = {
    "general_public": (
        "Audience: a member of the general public with no medical background. "
        "Use simple, everyday language. Avoid technical/pharmacological terms unless you "
        "immediately explain them in plain words. Keep the answer short and easy to act on."
    ),
    "practitioner": (
        "Audience: an Ayurvedic practitioner or doctor. You may use clinical and pharmacological "
        "terminology freely. Include preparation method, plant part used, and any dosage or "
        "administration detail present in the context, since this audience needs practical detail."
    ),
    "student": (
        "Audience: a student studying Ayurveda or traditional medicine. Explain the reasoning behind "
        "the answer (why the plant/preparation works, what property is responsible) in an educational "
        "tone, as if teaching a concept, not just stating a fact."
    ),
    "researcher": (
        "Audience: a researcher or academic. Be precise and evidence-conscious. Explicitly distinguish "
        "between what is traditional/folk knowledge versus what has scientific support, citing the "
        "'Scientific Evidence Level' field from the context if it is present."
    ),
}


def ask_question(user_question: str, session_id: str = "default", user_context: dict = None):
    if user_context is None:
        user_context = {}

    user_type = user_context.get("user_type", "general_public")
    if user_type not in PERSONA_INSTRUCTIONS:
        user_type = "general_public"
    persona_instruction = PERSONA_INSTRUCTIONS[user_type]

    chat_history = conversation_store.get(session_id, [])

    # 1. Standalone Question - Use very recent history only
    if chat_history:
        rewrite_messages = [
            SystemMessage(content="""You are rewriting questions for Ayurvedic search.
Focus on the latest user question. If the new question is about a different topic or plant, ignore old context."""),
        ] + chat_history[-4:] + [   # Use only last 2 Q&A
            HumanMessage(content=f"Rewrite this as a standalone search query: {user_question}")
        ]
        standalone = llm.invoke(rewrite_messages)
        search_question = standalone.content.strip()
    else:
        search_question = user_question

    # 2. Retrieve documents WITH distance scores
    docs_with_scores = vectorstore.similarity_search_with_score(search_question, k=5)

    # Tune this threshold using your own test set 
    DISTANCE_THRESHOLD = 0.8

    relevant_docs_with_scores = [
        (doc, score) for doc, score in docs_with_scores if score <= DISTANCE_THRESHOLD
    ]

    if not relevant_docs_with_scores:
        is_sinhala_query = any("\u0d80" <= ch <= "\u0dff" for ch in user_question)
        fallback_answer = (
            "මට මගේ දත්ත ගබඩාවේ මේ ශාකය පිළිබඳ ප්‍රමාණවත් විශ්වසනීය තොරතුරු නොමැත. "
            "කරුණාකර මගේ දත්ත ගබඩාවේ ඇති ශාක ගැන අසන්න."
            if is_sinhala_query
            else
            "I don't have verified information about this in my knowledge base, "
            "so I can't answer that accurately. Please ask about one of the plants "
            "I've been trained on."
        )
        # Deliberately NOT saved to chat_history, so an unanswerable question
        # doesn't pollute the context used for the next follow-up question.
        return {
            "answer": fallback_answer,
            "sources": [],
            "user_type": user_type,
            "safety_context_available": False,
        }

    docs = [doc for doc, _ in relevant_docs_with_scores]

    context = "\n\n".join([f"Document {i+1}: {doc.page_content}" for i, doc in enumerate(docs)])

    # 3. STRONGER FINAL PROMPT 
    prompt = f"""You are a highly accurate Sri Lankan Ayurvedic expert.

**CRITICAL RULES:**
- Always answer in the language of the **Current Question**.
- If the user changes topic or asks about a new plant, **completely switch** to the new topic.
- Do NOT continue talking about the previous plant unless the new question clearly refers to it.
- Never force old context on a new unrelated question.
- If the retrieved context includes a "Precautions/Limitations" field for the plant being discussed,
  you MUST mention the relevant caution briefly, even if the user did not ask about safety.
- If the context does not contain enough information to answer confidently, say so plainly instead
  of guessing.

**{persona_instruction}**

**Current Question:** {user_question}

**Context:**
{context}
"""

    # Use very limited history
    recent_history = chat_history[-4:]   # Last 2 conversations only

    messages = [
        SystemMessage(content="""You are a Sri Lankan Ayurvedic expert.
You must detect topic changes and language changes.
If user asks about a new subject, focus only on the new question."""),
    ] + recent_history + [
        HumanMessage(content=prompt)
    ]

    result = llm.invoke(messages)
    answer = result.content

    # Update history
    chat_history.append(HumanMessage(content=user_question))
    chat_history.append(AIMessage(content=answer))
    
    # Keep only last 6 messages (3 Q&A pairs)
    conversation_store[session_id] = chat_history[-6:]

    return {
        "answer": answer,
        "sources": [doc.metadata.get('source', 'Medicinal Plants.txt') for doc in docs[:3]],
        "user_type": user_type,
        "safety_context_available": "Precautions/Limitations" in docs[0].page_content,
    }


def clear_conversation(session_id: str = "default"):
    if session_id in conversation_store:
        del conversation_store[session_id]
PERSONA_INSTRUCTIONS = {
    "general_public": (
        "Audience: a member of the general public with no medical background. "
        "Use simple, everyday language. Avoid technical/pharmacological terms unless you "
        "immediately explain them in plain words. Keep the answer short and easy to act on."
    ),
    "practitioner": (
        "Audience: an Ayurvedic practitioner or doctor. You may use clinical and pharmacological "
        "terminology freely. Include preparation method, plant part used, and any dosage or "
        "administration detail present in the context, since this audience needs practical detail."
    ),
    "student": (
        "Audience: a student studying Ayurveda or traditional medicine. Explain the reasoning behind "
        "the answer (why the plant/preparation works, what property is responsible) in an educational "
        "tone, as if teaching a concept, not just stating a fact."
    ),
    "researcher": (
        "Audience: a researcher or academic. Be precise and evidence-conscious. Explicitly distinguish "
        "between what is traditional/folk knowledge versus what has scientific support, citing the "
        "'Scientific Evidence Level' field from the context if it is present."
    ),
}


def ask_question(user_question: str, session_id: str = "default", user_context: dict = None):
    if user_context is None:
        user_context = {}

    user_type = user_context.get("user_type", "general_public")
    if user_type not in PERSONA_INSTRUCTIONS:
        user_type = "general_public"
    persona_instruction = PERSONA_INSTRUCTIONS[user_type]

    chat_history = conversation_store.get(session_id, [])

    # 1. Standalone Question - Use very recent history only
    if chat_history:
        rewrite_messages = [
            SystemMessage(content="""You are rewriting questions for Ayurvedic search.
Focus on the latest user question. If the new question is about a different topic or plant, ignore old context."""),
        ] + chat_history[-4:] + [   # Use only last 2 Q&A
            HumanMessage(content=f"Rewrite this as a standalone search query: {user_question}")
        ]
        standalone = llm.invoke(rewrite_messages)
        search_question = standalone.content.strip()
    else:
        search_question = user_question

    # 2. Retrieve documents
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(search_question)

    context = "\n\n".join([f"Document {i+1}: {doc.page_content}" for i, doc in enumerate(docs)])

    # 3. STRONGER FINAL PROMPT (This is the key fix)
    prompt = f"""You are a highly accurate Sri Lankan Ayurvedic expert.

**CRITICAL RULES:**
- Always answer in the language of the **Current Question**.
- If the user changes topic or asks about a new plant, **completely switch** to the new topic.
- Do NOT continue talking about the previous plant unless the new question clearly refers to it.
- Never force old context on a new unrelated question.
- If the retrieved context includes a "Precautions/Limitations" field for the plant being discussed,
  you MUST mention the relevant caution briefly, even if the user did not ask about safety.
- If the context does not contain enough information to answer confidently, say so plainly instead
  of guessing.

**{persona_instruction}**

**Current Question:** {user_question}

**Context:**
{context}
"""

    # Use very limited history
    recent_history = chat_history[-4:]   # Last 2 conversations only

    messages = [
        SystemMessage(content="""You are a Sri Lankan Ayurvedic expert.
You must detect topic changes and language changes.
If user asks about a new subject, focus only on the new question."""),
    ] + recent_history + [
        HumanMessage(content=prompt)
    ]

    result = llm.invoke(messages)
    answer = result.content

    # Update history
    chat_history.append(HumanMessage(content=user_question))
    chat_history.append(AIMessage(content=answer))
    
    # Keep only last 6 messages (3 Q&A pairs)
    conversation_store[session_id] = chat_history[-6:]

    return {
        "answer": answer,
        "sources": [doc.metadata.get('source', 'Medicinal Plants.txt') for doc in docs[:3]],
        "user_type": user_type,
        "safety_context_available": any(
            "Precautions/Limitations" in doc.page_content for doc in docs
        ),
    }


def clear_conversation(session_id: str = "default"):
    if session_id in conversation_store:
        del conversation_store[session_id]