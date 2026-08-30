import re

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
    frequency_penalty=0.9,
    presence_penalty=0.7,
)

conversation_store = {}

# Tune against your own test set. Chroma's default distance metric for
# OpenAI embeddings is cosine distance (0 = identical, 2 = opposite),
# so a single threshold works for both languages now that the search
# query is always translated to English before retrieval.
DISTANCE_THRESHOLD = 0.8

SINHALA_RANGE = re.compile(r"[\u0D80-\u0DFF]+")

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


def _is_sinhala(text: str) -> bool:
    return bool(SINHALA_RANGE.search(text))


def _fallback_answer(is_sinhala: bool) -> str:
    if is_sinhala:
        return (
            "මට මගේ දත්ත ගබඩාවේ මේ ශාකය පිළිබඳ ප්‍රමාණවත් විශ්වසනීය තොරතුරු නොමැත. "
            "කරුණාකර මගේ දත්ත ගබඩාවේ ඇති ශාක ගැන අසන්න."
        )
    return (
        "I don't have verified information about this in my knowledge base, "
        "so I can't answer that accurately. Please ask about one of the plants "
        "I've been trained on."
    )


def _build_search_query(user_question: str, chat_history: list, is_sinhala: bool) -> str:
    """
    One LLM call that both makes the question standalone (using recent
    history) AND translates it to English if needed. Doing this in a
    single call — instead of a rewrite call followed by a separate
    translate call — avoids compounding errors: a second call can only
    translate whatever the first call produced, so if the first call
    drifts off the plant name, the mistake is invisible and gets
    "faithfully" translated.
    """
    if not chat_history and not is_sinhala:
        return user_question

    instructions = (
        "You turn Ayurvedic/medicinal-plant questions into short, standalone English "
        "search queries for a vector database.\n"
        "- Use the conversation history only to resolve pronouns or an implied plant "
        "(e.g. 'what about for skin?' after asking about neem).\n"
        "- If the new question is about a different plant/topic, ignore old history entirely.\n"
        "- If the question is in Sinhala, translate it to English and keep the exact plant "
        "identity (do not substitute a different plant). Prefer the common English name and, "
        "if useful, the scientific name (e.g. 'neem Azadirachta indica leaves for skin diseases').\n"
        "- Return ONLY the search query text. No preamble, no quotes."
    )
    messages = [SystemMessage(content=instructions)] + chat_history[-4:] + [
        HumanMessage(content=f"Question: {user_question}")
    ]
    return llm.invoke(messages).content.strip()


def ask_question(user_question: str, session_id: str = "default", user_context: dict = None):
    if user_context is None:
        user_context = {}

    user_type = user_context.get("user_type", "general_public")
    if user_type not in PERSONA_INSTRUCTIONS:
        user_type = "general_public"
    persona_instruction = PERSONA_INSTRUCTIONS[user_type]

    chat_history = conversation_store.get(session_id, [])
    is_sinhala = _is_sinhala(user_question)
    sinhala_terms = SINHALA_RANGE.findall(user_question)

    # 1. Standalone + translated search query (single LLM call)
    search_question = _build_search_query(user_question, chat_history, is_sinhala)

    # 2. Retrieve with distance scores
    docs_with_scores = vectorstore.similarity_search_with_score(search_question, k=5)
    relevant_docs_with_scores = [
        (doc, score) for doc, score in docs_with_scores if score <= DISTANCE_THRESHOLD
    ]

    if not relevant_docs_with_scores:
        return {
            "answer": _fallback_answer(is_sinhala),
            "sources": [],
            "user_type": user_type,
            "safety_context_available": False,
        }

    docs = [doc for doc, _ in relevant_docs_with_scores]

    # 3. Dict-free hallucination guard: if the user asked in Sinhala, at
    # least one Sinhala term from their own question should actually
    # appear in the retrieved text. Your knowledge base already embeds
    # the Sinhala plant name in the English content (e.g. "known as
    # 'kohomba' in Sinhala"), so this needs no maintained keyword list
    # and generalizes to every plant in the KB, not just ~20 hard-coded
    # ones. It's a soft check across ALL retrieved docs, not just the
    # top one, so a same-named plant showing up 2nd or 3rd still counts.
    if is_sinhala and sinhala_terms:
        combined_text = "\n\n".join(doc.page_content for doc in docs)
        if not any(term in combined_text for term in sinhala_terms):
            return {
                "answer": _fallback_answer(is_sinhala),
                "sources": [],
                "user_type": user_type,
                "safety_context_available": False,
            }

    context = "\n\n".join([f"Document {i+1}: {doc.page_content}" for i, doc in enumerate(docs)])

    # 4. Final prompt
    prompt = f"""You are a highly accurate Sri Lankan Ayurvedic expert.

**CRITICAL RULES:**
- Answer ONLY about the plant the user asked about in the Current Question.
- If the Context is about a different plant, refuse and say you don't have information — do not mix plants.
- Always answer in the language of the Current Question.
- If the user changes topic or asks about a new plant, completely switch to the new topic; never force old context onto an unrelated new question.
- If the context includes a "Precautions/Limitations" field for the plant being discussed, you MUST mention the relevant caution briefly, even if the user did not ask about safety.
- If the context does not contain enough information to answer confidently, say so plainly instead of guessing.

**{persona_instruction}**

**Current Question:** {user_question}

**Context:**
{context}
"""

    recent_history = chat_history[-4:]

    messages = [
        SystemMessage(content="""You are a careful Sri Lankan Ayurvedic expert.
You must detect topic changes and language changes, and you never answer about the wrong plant.
If the retrieved context does not match the plant in the Current Question, you must refuse."""),
    ] + recent_history + [
        HumanMessage(content=prompt)
    ]

    result = llm.invoke(messages)
    answer = result.content

    chat_history.append(HumanMessage(content=user_question))
    chat_history.append(AIMessage(content=answer))
    conversation_store[session_id] = chat_history[-6:]  # last 3 Q&A pairs

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
