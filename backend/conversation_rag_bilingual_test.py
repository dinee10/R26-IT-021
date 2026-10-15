
import json
import logging
import os
import re
from pathlib import Path

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("RAG_DEBUG") == "1"
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.WARNING)
log = logging.getLogger("herbal_rag")

CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db_bilingual_refs_test")
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

MEDICINAL_EN = DATA_DIR / "Medicinal Plants.txt"
MEDICINAL_SI = DATA_DIR / "Medicinal_Plants_Sinhala.txt"
DISEASE_EN = DATA_DIR / "disease_knowledge.txt"
DISEASE_SI = DATA_DIR / "disease_knowledge_sinhala.txt"

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)

# Main answer models. Sinhala needs more tokens than English for the same content.
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.15, max_tokens=900)
llm_sinhala = ChatOpenAI(model="gpt-4o-mini", temperature=0.15, max_tokens=1400)

# Small deterministic models for classification / query building.
classifier_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=60)
extract_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=120)
query_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=150)

conversation_store = {}

# NOTE: Chroma's default metric is squared L2 unless the collection was created with
# {"hnsw:space": "cosine"}. 
DISTANCE_THRESHOLD = float(os.getenv("DISTANCE_THRESHOLD", "0.8"))

MAX_PERSONAS = 2          # max combined categories per answer
MAX_SEARCH_QUERIES = 3    # max plants/topics searched per question
DEFAULT_PERSONA = "general_public"

SINHALA_RANGE = re.compile(r"[\u0D80-\u0DFF]+")

# Heuristic: only these questions get sent through the multi-query splitter
# when there is no chat history and the question is in English.
MULTI_HINT = re.compile(r"\b(and|vs|versus|compare|compared|between|both)\b|,|&|සහ|හා", re.IGNORECASE)

# Heuristic: an explicit style/audience request must be stripped out of the search query.
STYLE_HINT = re.compile(
    r"\b(?:as|for)\s+(?:a|an|the)?\s*(?:researcher|scientist|student|practitioner|doctor|layman|layperson|beginner)\b"
    r"|\bin\s+simple\b|\bscientific(?:ally)?\b",
    re.IGNORECASE,
)

PERSONA_INSTRUCTIONS = {
    "general_public": (
        "Audience: a member of the general public with no medical background. "
        "For a name-only question, give only the requested name in one sentence. "
        "Otherwise write 3 to 5 short sentences (or a few short '-' lines) in everyday words. "
        "For medicinal-use questions, describe traditional uses and give a relevant precaution. "
        "Do NOT mention evidence levels, references or Latin names unless the user asked for them."
    ),
    "practitioner": (
        "Audience: an Ayurvedic practitioner or doctor. Use clinical terminology. "
        "Order the answer as: plant part and preparation; indications; precautions and contraindications; "
        "then one line on how strong the evidence is. Give dosage only if it appears in the context; "
        "otherwise say dosage is not specified in the knowledge base. Do not list references."
    ),
    "student": (
        "Audience: a student of Ayurveda or traditional medicine. "
        "Use clear educational explanations appropriate for learning. "
        "Answer the user's specific question directly before providing background. "
        "Adapt the response structure to the question type. "
        "For plant identification, give the requested name or classification. "
        "For preparation questions, explain only the documented preparation "
        "method and relevant precautions. If steps are missing, say so. "
        "For questions about medicinal uses, explain the traditional uses "
        "and their documented properties. "
        "For questions asking why or how something works, explain the "
        "mechanism only to the extent supported by the retrieved evidence. "
        "Clearly distinguish traditional uses from scientifically established effects. "
        "Use 'Key points to remember' only when a broader educational "
        "summary would genuinely help. "
        "Do not repeat unrelated medicinal uses or invent missing details. "
        "For scientific-name or identification questions, answer briefly and directly. "
        "Do not add 'Key points to remember', unrelated medicinal uses, or extra background."
    ),
    "researcher": (
        "Audience: a researcher or academic. Write precise prose, not a copy of the record. "
        "Give the scientific name and family, then for each main use state whether the support is traditional only, "
        "laboratory (in vitro or animal) or clinical, based on 'Evidence by Use' and 'Scientific Evidence Level'. "
        "Phrase traditional claims as 'traditionally reported', never as established fact. "
        "Name the evidence gaps and note toxicity briefly. "
        "Finish with the entries from 'Evidence References' exactly as written in the context; never add other studies."
    ),
}

ALLOWED_PERSONAS = list(PERSONA_INSTRUCTIONS.keys())  # must stay AFTER PERSONA_INSTRUCTIONS


# Language helpers
def _clean_markdown(text: str) -> str:
    """The Flutter chat shows plain text, so strip markdown that the model still emits."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    return text.strip()


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



# Dataset lookups (loaded ONCE at start-up, not on every request)

def _parse_records(file_path):
    """Yield one {field: value} dict per record. Missing files are skipped."""
    path = Path(file_path)
    if not path.exists():
        log.warning("Data file not found: %s", path)
        return
    text = path.read_text(encoding="utf-8")
    for record in re.split(r"\n\s*\n\s*\n", text):
        fields = {}
        for line in record.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
        if fields:
            yield fields


KNOWN_PLANT_NAMES = set()   # every English / Sinhala / scientific alias, casefolded
SINHALA_ALIAS_MAP = {}      # Sinhala alias -> "English name (Scientific name)"


def _add_aliases(value: str):
    for alias in value.split("/"):
        alias = alias.strip().casefold()
        if alias:
            KNOWN_PLANT_NAMES.add(alias)


def _build_lookups():
    for path in (MEDICINAL_EN, MEDICINAL_SI):
        for f in _parse_records(path):
            for key in ("Name (English)", "Name (Sinhala)", "Scientific Name"):
                _add_aliases(f.get(key, ""))

    # Disease records: the host plant must also count as a known plant.
    for path in (DISEASE_EN, DISEASE_SI):
        for f in _parse_records(path):
            _add_aliases(f.get("Species", ""))

    for f in _parse_records(MEDICINAL_SI):
        eng = f.get("Name (English)", "").split("/")[0].strip()
        sci = f.get("Scientific Name", "").strip()
        if not (eng and sci):
            continue
        for alias in f.get("Name (Sinhala)", "").split("/"):
            alias = alias.strip()
            if alias and _is_sinhala(alias):
                SINHALA_ALIAS_MAP[alias] = f"{eng} ({sci})"


_build_lookups()


def _inject_plant_identity(question: str) -> str:
    """Replace any known Sinhala plant name with 'English (Scientific)' so the
    translation step cannot swap in a different plant. Longest alias first.
    Substring matching also covers Sinhala suffixes (e.g. -ට, -ේ)."""
    for alias in sorted(SINHALA_ALIAS_MAP, key=len, reverse=True):
        if alias in question:
            question = question.replace(alias, SINHALA_ALIAS_MAP[alias])
    return question


def _is_known_plant(name: str) -> bool:
    """True if a requested plant name matches anything in the knowledge base."""
    pieces = [p.strip().casefold() for p in re.split(r"[()/,]", name) if p.strip()]
    for piece in pieces:
        if piece in KNOWN_PLANT_NAMES:
            return True
        for known in KNOWN_PLANT_NAMES:
            if len(known) >= 4 and re.search(rf"(?<!\w){re.escape(known)}(?!\w)", piece):
                return True
            if len(piece) >= 4 and re.search(rf"(?<!\w){re.escape(piece)}(?!\w)", known):
                return True
    return False


# The DB may store 'source' with Windows back-slashes (data\Medicinal Plants.txt).
# Discover the real stored strings so filters keep working on any OS.
def _discover_sources() -> dict:
    try:
        metas = vectorstore.get(include=["metadatas"]).get("metadatas") or []
    except Exception:
        log.warning("Could not read source metadata from Chroma", exc_info=True)
        return {}
    found = {}
    for meta in metas:
        src = (meta or {}).get("source")
        if src:
            found[os.path.basename(src.replace("\\", "/")).casefold()] = src
    return found


SOURCE_BY_NAME = _discover_sources()


def _src(filename: str) -> str:
    return SOURCE_BY_NAME.get(filename.casefold(), str(Path("data") / filename))



# The Flutter page already supplies the default audience. The classifier is only
# called when the question asks for a different style. Sinhala messages always go
# to the classifier, because Sinhala style requests are phrased in many ways that
# a keyword list cannot cover.
AUDIENCE_SWITCH_HINT = re.compile(
    r"\b(?:researcher|scientist|practitioner|student|beginner|layperson|"
    r"scientific|evidence|studies|research papers?|citations?|references?|"
    r"clinical trials?|explain why|why does|why is|how does|how do|"
    r"teach me|for learning|simple terms|in simple words|plain language|"
    r"explain simply|as a doctor|for a doctor)\b"
    r"|පර්යේෂ|විද්‍යාත්මක|සාක්ෂි|අධ්‍යයන|ශිෂ්‍ය|සිසුව|"
    r"සරලව|ලේසියෙන්|පහසුවෙන්|කෙසේ ක්‍රියා|ඇයි|"
    r"වෛද්‍යවරයෙකු ලෙස",
    re.IGNORECASE,
)

_ROLE_TO_PERSONA = {
    "researcher": "researcher", "scientist": "researcher",
    "practitioner": "practitioner", "doctor": "practitioner",
    "student": "student", "general public": "general_public",
    "layperson": "general_public", "beginner": "general_public",
}


def _detect_personas(question: str) -> list:
    """Return only explicitly requested answer styles; [] means use the page default."""
    direct_personas = []

    explicit_role = re.findall(
        r"\b(?:as|like)\s+(?:a|an|the)?\s*"
        r"(researcher|scientist|practitioner|doctor|student|"
        r"general\s+public|layperson|beginner)\b",
        question, flags=re.IGNORECASE,
    )
    named_style = re.findall(
        r"\b(researcher|practitioner|student|general\s+public)"
        r"\s+(?:style|mode|perspective|answer|version)\b",
        question, flags=re.IGNORECASE,
    )
    for raw in explicit_role + named_style:
        persona = _ROLE_TO_PERSONA.get(" ".join(raw.lower().split()))
        if persona and persona not in direct_personas:
            direct_personas.append(persona)
    if direct_personas:
        return direct_personas[:MAX_PERSONAS]

    if not AUDIENCE_SWITCH_HINT.search(question) and not _is_sinhala(question):
        return []

    instructions = (
        "Decide whether this message explicitly requests an answer style "
        "DIFFERENT from the chatbot page's default audience. The message may be "
        "in Sinhala or English. Allowed values: "
        "general_public, practitioner, student, researcher.\n"
        "- Researcher: requests scientific evidence, studies, citations or "
        "research-grade analysis; or explicitly asks to answer as a researcher.\n"
        "- Student: asks to be taught why/how something works or explicitly "
        "requests a student/learning explanation.\n"
        "- Practitioner: explicitly requests a practitioner/clinician's "
        "style, clinical prescribing details, or a clinician's explanation.\n"
        "- General Public: explicitly requests simple or plain-language "
        "explanations, or says to answer as General Public.\n"
        "- Ordinary questions about a plant's uses, preparation, risks, or "
        "identity DO NOT specify an audience; return []. In particular, "
        "'What is aloe vera used for?' must return [].\n"
        "- Only select a style actually requested by this message; don't infer "
        "General Public from a short or ordinary question.\n"
        "Return a JSON list of at most 2 distinct allowed values. "
        "Return [] if no answer style is requested. JSON only."
    )
    try:
        raw = classifier_llm.invoke(
            [SystemMessage(content=instructions), HumanMessage(content=question)]
        ).content.strip().replace("```json", "").replace("```", "").strip()
        found = json.loads(raw)
        if not isinstance(found, list):
            return []
        cleaned = []
        for p in found:
            if p in ALLOWED_PERSONAS and p not in cleaned:
                cleaned.append(p)
        return cleaned[:MAX_PERSONAS]
    except Exception:
        return []


def _resolve_personas(question: str, session_id: str, user_context: dict) -> list:
    """
    Priority:
      1. Explicit choice from the UI chips (sticky: the app resends it).
      2. Style requested in THIS message (applies to this answer only).
      3. The page's own category ("default_type"), else General Public.
    """
    home = user_context.get("default_type")
    if home not in ALLOWED_PERSONAS:
        home = DEFAULT_PERSONA

    explicit = user_context.get("user_type")
    if explicit and explicit != "auto":
        explicit = [explicit] if isinstance(explicit, str) else list(explicit)
        explicit = [p for p in explicit if p in ALLOWED_PERSONAS][:MAX_PERSONAS]
        if explicit:
            return explicit

    detected = _detect_personas(question)
    if detected:
        return detected

    return [home]


def _build_persona_instruction(personas: list) -> str:
    if len(personas) == 1:
        return PERSONA_INSTRUCTIONS[personas[0]]
    parts = "\n".join(f"- {PERSONA_INSTRUCTIONS[p]}" for p in personas)
    return (
        "The user needs information for more than one audience. Write ONE answer "
        "with a short labelled section for each audience below, in this order:\n" + parts
    )



# Query building + retrieval 

def _build_search_query(user_question: str, chat_history: list) -> str:
    """
    Makes the question standalone (using recent history), translates it to English
    if needed, and splits multi-plant questions into one query per line (max 3).
    Known Sinhala plant names are replaced by 'English (Scientific)' first so the
    translation can never substitute a different plant.
    """
    is_sinhala = _is_sinhala(user_question)
    if is_sinhala:
        user_question = _inject_plant_identity(user_question)

    if (
        not chat_history
        and not is_sinhala
        and not MULTI_HINT.search(user_question)
        and not STYLE_HINT.search(user_question)
    ):
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
        "- If the question asks about several plants or topics, return one query per line "
        "(maximum 3), one per plant. Otherwise return a single line.\n"
        "- Ignore requests about answer style or audience (e.g. 'answer as a researcher'); "
        "keep only the plant and the topic.\n"
        "- Return ONLY the search query text. No preamble, no quotes, no numbering."
    )
    messages = [SystemMessage(content=instructions)] + chat_history[-4:] + [
        HumanMessage(content=f"Question: {user_question}")
    ]
    return query_llm.invoke(messages).content.strip()


def _clean_query_line(line: str) -> str:
    return re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s*", "", line).strip()


def _get_record_identity(doc):
    """Identify a medicinal plant or plant-disease record."""
    fields = {}
    for line in doc.page_content.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().casefold()

    if "Species" in fields and "Disease Name" in fields:
        return ("plant_disease", fields["Species"], fields["Disease Name"])
    if "Name (English)" in fields:
        return ("medicinal", fields["Name (English)"])
    return None


def _normalize_disease_label(value: str) -> str:
    """Match disease names with spaces, underscores or punctuation consistently."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def _load_verified_disease_records() -> dict:
    """Index disease documents already stored in Chroma; do not rebuild the DB.

    Exact lookup prevents Quality Assessment labels from being mistaken for
    unsupported medicinal plants or substituted with semantically similar plants.
    """
    indexed = {}
    try:
        data = vectorstore.get(include=["documents", "metadatas"])
        for content, metadata in zip(data.get("documents") or [], data.get("metadatas") or []):
            if not content:
                continue
            doc = Document(page_content=content, metadata=metadata or {})
            identity = _get_record_identity(doc)
            if identity and identity[0] == "plant_disease":
                key = (_normalize_disease_label(identity[1]),
                       _normalize_disease_label(identity[2]))
                indexed.setdefault(key, []).append(doc)
    except Exception:
        log.warning("Could not index disease records from Chroma", exc_info=True)
    return indexed


VERIFIED_DISEASE_RECORDS = _load_verified_disease_records()


def _matching_verified_disease_records(question: str) -> list:
    """Find an explicitly named species + disease pair, such as a QA output label."""
    normalized = f" {_normalize_disease_label(question)} "
    matched = []
    for (species, disease), docs in VERIFIED_DISEASE_RECORDS.items():
        if f" {species} " in normalized and f" {disease} " in normalized:
            matched.extend(docs)
    return matched


def _extract_requested_plant_names(user_question: str, search_query: str) -> list:
    """Plant names the user explicitly mentioned, including ones NOT in the database."""
    instructions = (
        "Identify the plant names explicitly mentioned in the user's question. "
        "The English search query helps translate Sinhala plant names. "
        "Extract ALL requested plant names, including plants not in a database. "
        "Prefer common English names when available. "
        "If a common name and scientific name refer to the same plant, "
        "return only one name. "
        "Do not invent plants or substitute similar plants. "
        "For questions using only pronouns such as 'it' or 'its', return []. "
        "For questions with no explicitly named plant, return []. "
        "Return JSON only in this format: "
        '{"plants": ["Plant 1", "Plant 2"]}'
    )
    try:
        response = extract_llm.invoke([
            SystemMessage(content=instructions),
            HumanMessage(content=(
                f"Original question: {user_question}\n"
                f"English search query: {search_query}"
            )),
        ]).content.strip().replace("```json", "").replace("```", "").strip()

        plants = json.loads(response).get("plants", [])
        if not isinstance(plants, list):
            return []
        return [
            n.strip() for n in plants if isinstance(n, str) and n.strip()
        ][:MAX_SEARCH_QUERIES]
    except Exception:
        return []

_PLANT_DISEASE_QUERY = re.compile(
    r"\b(?:leaf\s+(?:blight|spot|rot|rust|miners?|disease|damage)|"
    r"plant\s+(?:diseases?|infection|damage)|"
    r"(?:powdery|downy)\s+mildew|web\s+blight|dieback|"
    r"(?:insect|caterpillar|pest|mite)\s+(?:damage|infestation)|"
    r"worm\s*creep|wormcreep|defoliation|foliar\s+(?:disease|damage)|"
    r"bacterial\s+(?:leaf\s+)?infection|leaf\s+yellowing|"
    r"diseases?\s+(?:affecting|of|on)\s+(?:the\s+)?[a-z]+)\b",
    re.IGNORECASE,
)


def _retrieve(search_query: str, k_single: int = 5, k_multi: int = 3, source_filter=None):
    """Retrieve from the correct document category before ranking by distance.

    Explicit `source_filter` takes priority. Otherwise medicinal records are
    the default for herbal questions; named plant-health conditions use disease
    records. Multi-line questions can search different categories per line.
    """
    queries = [_clean_query_line(q) for q in search_query.split("\n")]
    queries = [q for q in queries if q][:MAX_SEARCH_QUERIES] or [search_query]
    k = k_single if len(queries) == 1 else k_multi

    seen, merged = set(), []
    for q in queries:
        if source_filter:
            sources = (source_filter,)
        elif _PLANT_DISEASE_QUERY.search(q):
            # For explicit two-topic comparisons, retrieve evidence for both.
            mixed = (
                re.search(r"\b(?:medicinal|ayurvedic|herbal)\b", q, re.IGNORECASE)
                and re.search(r"\b(?:and|both|compare)\b", q, re.IGNORECASE)
            )
            sources = (
                (_src("disease_knowledge.txt"), _src("Medicinal Plants.txt"))
                if mixed else (_src("disease_knowledge.txt"),)
            )
        else:
            sources = (_src("Medicinal Plants.txt"),)

        for source in sources:
            results = vectorstore.similarity_search_with_score(
                q, k=k, filter={"source": source}
            )
            for doc, score in results:
                if DEBUG:
                    log.debug(
                        "query=%r source=%r score=%.4f identity=%s kept=%s",
                        q, source, score, _get_record_identity(doc),
                        score <= DISTANCE_THRESHOLD,
                    )
                if score <= DISTANCE_THRESHOLD and doc.page_content not in seen:
                    seen.add(doc.page_content)
                    merged.append((doc, score))

    return sorted(merged, key=lambda x: x[1])



def _add_matching_sinhala(search_query, retrieved_docs):
    """Add the reviewed Sinhala record for every English record already retrieved."""
    english_sources = {_src("Medicinal Plants.txt"), _src("disease_knowledge.txt")}
    sinhala_sources = [
        _src("Medicinal_Plants_Sinhala.txt"),
        _src("disease_knowledge_sinhala.txt"),
    ]

    english_identities = {
        _get_record_identity(doc)
        for doc, _ in retrieved_docs
        if doc.metadata.get("source") in english_sources
    }

    combined = list(retrieved_docs)
    seen = {doc.page_content for doc, _ in combined}

    for source in sinhala_sources:
        matches = vectorstore.similarity_search_with_score(
            search_query, k=5, filter={"source": source}
        )
        for doc, score in matches:
            identity = _get_record_identity(doc)
            if (
                score <= DISTANCE_THRESHOLD
                and identity is not None
                and identity in english_identities
                and doc.page_content not in seen
            ):
                combined.append((doc, score))
                seen.add(doc.page_content)
    return combined


def _filter_to_named_plants(search_query, retrieved_docs):
    """Keep records for plants explicitly named in the search query."""
    matched_plants = set()

    for doc, _ in retrieved_docs:
        identity = _get_record_identity(doc)
        if identity is None:
            continue
        plant_name = identity[1]
        for name in (n.strip() for n in plant_name.split("/") if n.strip()):
            if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", search_query, re.IGNORECASE):
                matched_plants.add(plant_name)
                break

    # Preserve normal retrieval for questions without named plants.
    if not matched_plants:
        return retrieved_docs

    return [
        (doc, score) for doc, score in retrieved_docs
        if _get_record_identity(doc) is not None
        and _get_record_identity(doc)[1] in matched_plants
    ]


def _filter_by_question_topic(search_query, retrieved_docs):
    """Filter by topic only when the intent is clear; keep both when ambiguous."""
    query = search_query.lower()

    medicinal_terms = ["medicinal", "ayurvedic", "traditional uses",
                       "traditionally used", "herbal remedy"]
    plant_disease_terms = ["leaf disease", "plant disease", "leaf blight", "leaf spot",
                           "powdery mildew", "dieback", "foliar disease",
                           "plant infection", "disease symptoms"]

    asks_medicinal = any(t in query for t in medicinal_terms)
    asks_plant_disease = any(t in query for t in plant_disease_terms)

    if asks_medicinal == asks_plant_disease:
        return retrieved_docs

    target = "medicinal" if asks_medicinal else "plant_disease"
    filtered = [
        (doc, score) for doc, score in retrieved_docs
        if _get_record_identity(doc) is not None
        and _get_record_identity(doc)[0] == target
    ]
    return filtered if filtered else retrieved_docs


def _botanical_mismatch(user_question, search_question, is_sinhala, scored_docs) -> bool:
    """True when a scientific name the user supplied (or the Sinhala translation
    produced) is not present in any retrieved record. Never substitute another plant."""
    match = re.search(r"\(([A-Z][a-z]+)\s+([a-z][a-z-]+)\)", user_question)

    if (
        match is None
        and is_sinhala
        and scored_docs
        and all((_get_record_identity(d) or (None,))[0] == "medicinal" for d, _ in scored_docs)
    ):
        candidates = [
            m for m in re.finditer(r"\b([A-Z][a-z]{2,})\s+([a-z][a-z-]{2,})\b", search_question)
            if m.group(1).casefold() not in {
                "what", "which", "where", "when", "how", "uses", "tell", "give",
                "explain", "traditional", "medicinal", "scientific"}
            and m.group(2).casefold() not in {
                "medicinal", "medicine", "uses", "used", "plant", "plants", "leaves",
                "flowers", "benefits", "preparation", "properties", "disease", "diseases"}
        ]
        if len(candidates) == 1:
            match = candidates[0]

    if match is None:
        return False

    requested = " ".join(match.groups()).casefold()
    identity_fields = ("Name (English):", "Scientific Name:", "Species:")
    return not any(
        requested in line.casefold()
        for doc, _ in scored_docs
        for line in doc.page_content.splitlines()
        if line.startswith(identity_fields)
    )



# Safety gate (plant-independent): possible poisoning / dangerous exposure

def _is_urgent_exposure(question: str, chat_history: list) -> bool:
    instructions = (
        "You are a multilingual safety triage classifier for a medicinal-plant "
        "information chatbot. Read Sinhala, English and mixed-language messages. "
        "Return JSON only: {\"emergency\": true} or {\"emergency\": false}. "
        "Use true when the user reports or strongly implies an actual, recent or "
        "ongoing possible poisoning or dangerous exposure: a person or child has "
        "swallowed/consumed an unknown, toxic or medicinal plant part, seed, oil, "
        "extract or excessive dose; there is a potentially serious reaction; or "
        "they ask what to do immediately about such an exposure. Assume the risk "
        "may be urgent even before symptoms appear. This applies to ANY plant. "
        "Use recent conversation only to resolve follow-up questions about an "
        "existing emergency. Do not treat a clearly new, unrelated question as "
        "a continuation. Use false for general educational questions about "
        "medicinal uses, precautions, side effects, normal food consumption or "
        "hypothetical risks when nobody is currently exposed. Never suggest a "
        "treatment. Output JSON, nothing else."
    )
    history = "\n".join(
        f"{('User' if isinstance(msg, HumanMessage) else 'Assistant')}: {msg.content}"
        for msg in chat_history[-4:]
    )
    try:
        raw = classifier_llm.invoke([
            SystemMessage(content=instructions),
            HumanMessage(content=f"Recent chat:\n{history}\nCurrent message:\n{question}"),
        ]).content.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(raw).get("emergency") is True
    except Exception:
        # Conservative backup if the classifier is unavailable. Not plant-specific.
        q = question.casefold()
        direct_exposure_terms = (
            "ගිල", "බීලා", "බිව්වා", "කාලා", "කෑවා", "පානය කර", "විෂවෙලා",
            "swallowed", "ingested", "drank", "accidentally ate", "poisoned",
            "overdose", "took too much",
        )
        return any(term in q for term in direct_exposure_terms)


def _urgent_exposure_reply(is_sinhala: bool) -> str:
    """Safety-first guidance; no plant-specific claims or treatment advice."""
    if is_sinhala:
        return (
            "ඔබ සඳහන් කළ සිදුවීමෙන් විෂවීමක් හෝ බරපතළ අහිතකර "
            "ප්‍රතික්‍රියාවක් ඇති විය හැක. දැන්ම වෛද්‍ය උපකාර ලබාගන්න. "
            "ළඟම ඇති රෝහලේ හදිසි ප්‍රතිකාර අංශයට යන්න හෝ "
            "හදිසි සේවාව අමතන්න. වමනය කරවීමට උත්සාහ නොකරන්න; "
            "නිවසේ ප්‍රතිකාර හෝ වෙනත් ඖෂධීය මිශ්‍රණ ලබා නොදෙන්න. "
            "රෝග ලක්ෂණ පෙනෙන තුරු බලා නොසිටින්න. හැකි නම් "
            "අදාළ ශාකය හෝ නිෂ්පාදන ඇසුරුම රැගෙන යන්න."
        )
    return (
        "This may be a poisoning or serious adverse exposure. Seek urgent "
        "medical help now: contact an emergency service or go to the nearest "
        "emergency department. Do not induce vomiting or try home remedies. "
        "Do not wait for symptoms. Take the plant or product container with "
        "you if available."
    )


CAUTION_PHRASES = (
    "caution", "precaution", "warning", "avoid", "risk", "toxic", "side effect",
    "do not", "should not", "not recommended", "medical advice", "consult a doctor",
    "pregnan", "breastfeed", "contraindicat",
    "අවදාන", "විෂ", "ප්‍රවේශ", "වළකි", "ගර්භ", "වෛද්‍ය උපදෙස්", "හදිසි", "අහිතකර",
)

CLARIFY_PREFIXES = ("Which plant are you referring to?", "ඔබ සඳහන් කරන්නේ කුමන ශාකය ගැනද?")



# Main entry point

def ask_question(user_question: str, session_id: str = "default", user_context: dict = None):
    if user_context is None:
        user_context = {}

    personas = _resolve_personas(user_question, session_id, user_context)
    persona_instruction = _build_persona_instruction(personas)

    def _result(answer, sources, safety, evidence=False):
        # Safety wording in the GENERATED answer (separate from safety info in documents).
        answer_has_caution = any(p in answer.casefold() for p in CAUTION_PHRASES)
        return {
            "answer": answer,
            "sources": sources,
            "user_types": personas,
            "user_type": personas[0],          # backward compatibility
            "answer_has_caution": answer_has_caution,
            "safety_context_available": safety,
            "evidence_references_available": evidence,
        }

    # Restore recent history from Flutter/Firestore, else use backend memory.
    restored_history = user_context.get("recent_history", [])
    if restored_history:
        chat_history = [
            HumanMessage(content=m["content"]) if m["role"] == "user"
            else AIMessage(content=m["content"])
            for m in restored_history[-6:]
        ]
    else:
        chat_history = list(conversation_store.get(session_id, []))

    is_sinhala = _is_sinhala(user_question)
    sinhala_terms = SINHALA_RANGE.findall(user_question)

        # Handle simple greetings without searching the knowledge base.
    greeting = re.sub(
        r"[!?.,\s]+$",
        "",
        user_question.strip()
    ).casefold()

    english_greetings = {
        "hi",
        "hello",
        "hey",
        "hi there",
        "hello there",
        "good morning",
        "good afternoon",
        "good evening"
    }

    sinhala_greetings = {
        "ආයුබෝවන්",
        "හායි",
        "හෙලෝ",
        "සුබ උදෑසනක්",
        "සුබ දවසක්",
        "සුබ සන්ධ්‍යාවක්"
    }

    if greeting in english_greetings or greeting in sinhala_greetings:

        if greeting in sinhala_greetings:
            greeting_answer = (
                "ආයුබෝවන්! මම ශ්‍රී ලංකාවේ ඖෂධීය ශාක පිළිබඳ "
                "තොරතුරු ලබාදෙන සහායකයෙක්. "
                "ඔබට දැනගැනීමට අවශ්‍ය ශාකය හෝ ප්‍රශ්නය සඳහන් කරන්න."
            )
        else:
            greeting_answer = (
                "Hello! I'm your Herbal Knowledge Assistant. "
                "I can help you learn about Sri Lankan medicinal plants, "
                "their uses. "
                "What would you like to know?"
            )

        chat_history.append(HumanMessage(content=user_question))
        chat_history.append(AIMessage(content=greeting_answer))
        conversation_store[session_id] = chat_history[-6:]

        return _result(greeting_answer, [], False)

    # 0. Safety gate FIRST: urgent cases never become ordinary RAG questions.
    if _is_urgent_exposure(user_question, chat_history):
        emergency_answer = _urgent_exposure_reply(is_sinhala)
        chat_history.append(HumanMessage(content=user_question))
        chat_history.append(AIMessage(content=emergency_answer))
        conversation_store[session_id] = chat_history[-6:]
        return _result(emergency_answer, [], True)

    # 1. Is a known plant named? (English, Sinhala or scientific name)
    question_lower = user_question.casefold()
    # Match English aliases as whole names; allow Sinhala inflectional suffixes.
    # Simple substring checks could mistake words that merely contain a plant name.
    plant_is_named = any(
        (name in question_lower if _is_sinhala(name)
         else re.search(rf"(?<!\w){re.escape(name)}(?!\w)", question_lower))
        for name in KNOWN_PLANT_NAMES
    )

    # Verify exact Quality Assessment labels before asking for clarification or
    # applying the unsupported-medicinal-plant gate.
    disease_docs = _matching_verified_disease_records(user_question)
    verified_disease = bool(
        disease_docs and user_context.get("knowledge_source") != "medicinal"
    )

    # 2. New conversation + no plant named -> ask which plant 
    if not chat_history and not plant_is_named and not verified_disease:
        try:
            check_prompt = (
                "You are checking whether a standalone question needs "
                "a previously identified plant or plant disease. "
                "Determine whether the user refers to an unspecified "
                "plant using words like 'it', 'its', 'this plant', "
                "or equivalent Sinhala expressions. "
                "Also detect incomplete questions such as 'How to prepare?' "
                "that require a specific plant. "
                "If the user explicitly names the plant, return false. "
                "For general questions that do not require a specific "
                "plant, return false. "
                "Return JSON only: {\"missing_subject\": true} "
                "or {\"missing_subject\": false}."
            )
            check_response = classifier_llm.invoke([
                SystemMessage(content=check_prompt),
                HumanMessage(content=user_question),
            ]).content.strip().replace("```json", "").replace("```", "").strip()

            if json.loads(check_response).get("missing_subject") is True:
                clarification = (
                    "ඔබ සඳහන් කරන්නේ කුමන ශාකය ගැනද? "
                    "කරුණාකර ශාකයේ නම සඳහන් කරන්න."
                    if is_sinhala
                    else "Which plant are you referring to? Please provide the plant's name."
                )
                chat_history.append(HumanMessage(content=user_question))
                chat_history.append(AIMessage(content=clarification))
                conversation_store[session_id] = chat_history[-6:]
                return _result(clarification, [], False)
        except Exception:
            pass

    # 3. Short plant/disease labels from the Quality Assessment integration.
    is_short_label = (
        not is_sinhala
        and not chat_history
        and "?" not in user_question
        and len(user_question.split()) <= 3
        and not re.search(
            r"\b(?:what|why|how|when|where|which|who|can|should|is|are|"
            r"do|does|tell|explain|describe|give|used|uses|benefits|"
            r"medicinal|evidence)\b",
            user_question, re.IGNORECASE,
        )
    )
    effective_question = (
        f"Tell me about {user_question} — what it is, its typical symptoms, "
        f"and whether affected leaves can still be used medicinally."
        if is_short_label else user_question
    )

    # 4. Pending clarification: combine the unanswered question with the plant name.
    search_input = user_question
    if (
        len(chat_history) >= 2
        and isinstance(chat_history[-2], HumanMessage)
        and isinstance(chat_history[-1], AIMessage)
        and chat_history[-1].content.strip().startswith(CLARIFY_PREFIXES)
    ):
        original_question = chat_history[-2].content
        effective_question = (
            f"Original unanswered question: {original_question}\n"
            f"User clarification: {user_question}\n"
            "Answer the original question using the clarification. "
            "Do not provide a general plant overview unless requested."
        )
        # The search must keep the ORIGINAL intent not just the plant name.
        search_input = f"{original_question} ({user_question})"

    # 5. Standalone + translated (+ split) search query
    search_question = _build_search_query(search_input, chat_history)

    # 6. An exact species + condition label was verified against stored disease
    # records. Ordinary medicinal questions still reject unsupported plants.
    if not verified_disease and not plant_is_named:
        requested = _extract_requested_plant_names(user_question, search_question)
        if requested and not any(_is_known_plant(n) for n in requested):
            log.info("Unsupported plant requested: %s", requested)
            return _result(_fallback_answer(is_sinhala), [], False)

    # 7. Knowledge source selection 
    source_filters = {
        "medicinal": _src("Medicinal Plants.txt"),
        "plant_disease": _src("disease_knowledge.txt"),
    }
    source_filter = source_filters.get(user_context.get("knowledge_source"))

    # 8. Retrieve and refine. For a verified Quality Assessment label, use its
    # exact disease record .
    if verified_disease:
        relevant_docs_with_scores = [(doc, None) for doc in disease_docs]
    else:
        relevant_docs_with_scores = _retrieve(search_question, source_filter=source_filter)
        if is_sinhala and relevant_docs_with_scores:
            relevant_docs_with_scores = _add_matching_sinhala(search_question, relevant_docs_with_scores)
        if relevant_docs_with_scores:
            relevant_docs_with_scores = _filter_to_named_plants(search_question, relevant_docs_with_scores)
        if relevant_docs_with_scores:
            relevant_docs_with_scores = _filter_by_question_topic(search_question, relevant_docs_with_scores)

    if not relevant_docs_with_scores:
        return _result(_fallback_answer(is_sinhala), [], False)

    # 9. Botanical-name validation: never answer with a different plant.
    if not verified_disease and _botanical_mismatch(user_question, search_question, is_sinhala, relevant_docs_with_scores):
        return _result(_fallback_answer(is_sinhala), [], False)

    docs = [doc for doc, _ in relevant_docs_with_scores]

    # 10. Soft hallucination guard for Sinhala questions: a Sinhala term from the
    # question, or an English name from the search query, must appear in the retrieved text.
    if is_sinhala and sinhala_terms:
        sinhala_match = any(
            term in doc.page_content for term in sinhala_terms for doc in docs
        )
        english_match = any(
            name.strip().lower() in search_question.lower()
            for doc in docs
            if doc.page_content
            for header in [doc.page_content.splitlines()[0]]
            if header.startswith(("Species:", "Name (English):"))
            for name in header.split(":", 1)[1].split("/")
            if name.strip()
        )
        if not (sinhala_match or english_match):
            return _result(_fallback_answer(is_sinhala), [], False)

    context = "\n\n".join(f"Document {i+1}: {doc.page_content}" for i, doc in enumerate(docs))

    
    # Quality Assessment -> More Information: use the full verified disease record.
    qa_detail_instruction = ""

    if verified_disease and user_question.strip().casefold().startswith("more information about"):
        qa_detail_instruction = """
QUALITY ASSESSMENT DETAIL MODE (overrides audience length and format only):

The user opened More Information for an identified plant condition.

Explain the exact condition in the Context in useful detail, using these sections:

- About the condition: plant name, Display Name and Description.
- Symptoms to look for: every important sign from Typical Symptoms.
- Healthy leaf comparison: facts from Healthy Plant Comparison.
- Recommended actions: all applicable guidance and cautions in Recommended Action.
- References: include the source URLs from Reference exactly as written.

Use clear, natural headings rather than database-field labels.
Cover every relevant section; do not restrict the response to 3-5 sentences.
Do not call pest injury, nutrient deficiency or physiological stress a proven disease.
Do not invent causes, treatments, pesticides or facts absent from this exact record.
Do not add unrelated medicinal uses; mention medicinal suitability only if recorded.
Always use the user's language.
"""


    # 11. Final prompt
    prompt = f"""You are a highly accurate Sri Lankan Ayurvedic expert.

**CRITICAL RULES:**
- Answer ONLY about the plant(s) named in the Current Question. If several plants are asked about, cover each one separately and never mix their facts.
- NEVER discuss medicinal uses of a plant that the user did not ask about. Similarity to a retrieved plant is not proof of plant identity.
- If no requested plant is supported by the Context, say briefly that verified information is unavailable; do NOT discuss other retrieved plants.
- If the user asks about several plants and only some are supported, answer only for the supported requested plants and identify the others as unavailable.
- Always answer in the language of the Current Question.
- If the user changes topic or asks about a new plant, completely switch to the new topic; never force old context onto an unrelated new question.
- If the context includes a "Precautions/Limitations" field for a plant being discussed, mention the relevant caution briefly for medicinal-use, preparation or safety questions.
- If the user asks ONLY for a plant's scientific name or identification, reply with the requested name in one sentence. Do not add medicinal uses, treatments or precautions. This overrides persona detail requirements for that naming-only question.
- If the context includes "Evidence by Use" or "Evidence References" for a plant being discussed, state the evidence level for the specific use asked about, and list the references when the audience is a researcher or student. Never invent studies that are not in the context.
- If the context does not contain enough information to answer confidently, say so plainly instead of guessing.
- Do NOT copy the record's field names (Medicinal Usage, Preparation, Precautions/Limitations, ...) as headings; write the answer in your own words in the format the audience instruction asks for.
- Do NOT use markdown symbols (no **, no #). Use plain sentences or short '-' lines.
- Present traditional claims as traditional ("traditionally used for ..."), not as proven effects.
- Do NOT say "based on the provided context" and do NOT end with an offer to answer more questions.
- If the user asks generally about diseases affecting a plant without naming a specific disease, provide an overview of the relevant diseases found in the Context. Explain their symptoms separately using their disease names. Do not refuse simply because the user did not name an exact disease. Clearly state that symptoms alone may not confirm a diagnosis.
- For Sinhala answers about plant diseases, use simple, natural, grammatically correct Sinhala. Keep scientific and disease names in English when necessary. Describe only the symptoms explicitly stated in the retrieved document's "Typical Symptoms" field. Do not invent additional symptoms, colours, causes, or treatments. If the Context contains relevant disease information, answer directly without first claiming that no information is available.
- For Sinhala answers in general, use simple, natural, grammatically correct Sinhala and keep plant scientific names in English. Use only facts from the Context.
- Always answer the user's CURRENT question directly before applying the audience-specific response format.
- For questions asking HOW TO PREPARE, USE, or APPLY a plant, prioritize the relevant preparation and plant-part information over general medicinal benefits. Explain only preparation details supported by the retrieved context.
- If the context does not provide complete preparation instructions, acknowledge that limitation instead of inventing steps. Audience-specific formats must never replace the direct answer.


**{persona_instruction}**

{qa_detail_instruction}

**Current Question:** {effective_question}

**Context:**
{context}
"""

    messages = [
        SystemMessage(content="""You are a careful Sri Lankan Ayurvedic expert.
You must detect topic changes and language changes, and you never answer about the wrong plant.
If the question names several plants, answer for each plant the context covers and say clearly which ones it does not cover.
If the retrieved context does not match any plant in the Current Question, you must refuse without giving facts about unrelated plants."""),
    ] + chat_history[-4:] + [HumanMessage(content=prompt)]

    answer_model = llm_sinhala if is_sinhala else llm
    try:
        result = answer_model.invoke(messages)
    except Exception:
        log.exception("Answer generation failed for session %s", session_id)
        return _result(_fallback_answer(is_sinhala), [], False)

    if (result.response_metadata or {}).get("finish_reason") == "length":
        log.warning("Answer truncated (token limit) for session %s", session_id)

    answer = _clean_markdown(result.content)

    chat_history.append(HumanMessage(content=user_question))
    chat_history.append(AIMessage(content=answer))
    conversation_store[session_id] = chat_history[-6:]  # last 3 Q&A pairs

    return _result(
        answer,
        [doc.metadata.get("source", "Medicinal Plants.txt") for doc in docs[:3]],
        any("Precautions/Limitations" in doc.page_content for doc in docs),
        any("Evidence References:" in doc.page_content for doc in docs),
    )


def clear_conversation(session_id: str = "default"):
    conversation_store.pop(session_id, None)