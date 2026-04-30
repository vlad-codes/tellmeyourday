import os
import json
import ollama
import chromadb
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

_DATA_DIR          = os.environ.get("TELMI_DATA_DIR", ".")
MEMORY_FILE        = os.path.join(_DATA_DIR, "memory.json")
PROFILE_FILE       = os.path.join(_DATA_DIR, "profile.json")
CHROMA_DIR         = os.path.join(_DATA_DIR, "chroma_db")
COLLECTION         = "memory"
EMBED_MODEL        = "nomic-embed-text"
VECTOR_MIN_ENTRIES = 15
VECTOR_TOP_K       = 5
# Cosine distance threshold for /search (0 = identical, 1 = orthogonal, 2 = opposite).
# nomic-embed-text typically scores relevant hits below 0.50; raise to 0.65 for looser results.
SEARCH_DISTANCE_THRESHOLD = 0.50


# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_collection()  # warm up ChromaDB on startup
    yield

app = FastAPI(title="Telmi API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    user_input: str
    mode: str           # "day" | "mind"
    history: list[ChatMessage]
    selected_model: str

class SaveRequest(BaseModel):
    mode: str
    history: list[ChatMessage]
    selected_model: str

class SaveResponse(BaseModel):
    title: str
    summary: str
    timestamp: str
    profile_update: str | None = None

class Entry(BaseModel):
    timestamp: str
    title: str
    summary: str
    has_chat: bool = False

class UpdateEntryRequest(BaseModel):
    title: str | None = None
    summary: str | None = None

class CalendarDay(BaseModel):
    date: str       # YYYY-MM-DD
    timestamp: str  # full "YYYY-MM-DD HH:MM:SS"
    title: str
    summary: str


# ─────────────────────────────────────────────
# ChromaDB singleton
# ─────────────────────────────────────────────

_chroma_collection: chromadb.Collection | None = None

def get_collection() -> chromadb.Collection:
    global _chroma_collection
    if _chroma_collection is None:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        _chroma_collection = client.get_or_create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
    return _chroma_collection


# ─────────────────────────────────────────────
# Embedding
# ─────────────────────────────────────────────

def get_embedding(text: str) -> list[float] | None:
    try:
        resp = ollama.embeddings(model=EMBED_MODEL, prompt=text)
        return resp["embedding"]
    except Exception:
        return None


# ─────────────────────────────────────────────
# ChromaDB operations
# ─────────────────────────────────────────────

def get_all_entries() -> list[dict]:
    result = get_collection().get(include=["documents", "metadatas"])
    chroma_entries = {}
    for m, d in zip(result["metadatas"], result["documents"]):
        ts = m.get("timestamp", "")
        chroma_entries[ts] = {"timestamp": ts, "title": m.get("title", ""), "summary": d}

    # Merge has_chat flag from memory.json (ChromaDB doesn't store it)
    json_entries = {e["timestamp"]: e for e in load_memory_json()}
    entries = []
    for ts, entry in chroma_entries.items():
        has_chat = bool(json_entries.get(ts, {}).get("history"))
        entries.append({**entry, "has_chat": has_chat})
    entries.sort(key=lambda e: e["timestamp"])
    return entries


def get_relevant_entries(query: str) -> list[dict]:
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []

    if total < VECTOR_MIN_ENTRIES:
        result = collection.get(include=["documents", "metadatas"])
        entries = [{"timestamp": m["timestamp"], "summary": d}
                   for m, d in zip(result["metadatas"], result["documents"])]
        entries.sort(key=lambda e: e["timestamp"])
        return entries[-VECTOR_TOP_K:]

    query_embedding = get_embedding(query)
    if query_embedding is None:
        result = collection.get(include=["documents", "metadatas"])
        entries = [{"timestamp": m["timestamp"], "summary": d}
                   for m, d in zip(result["metadatas"], result["documents"])]
        entries.sort(key=lambda e: e["timestamp"])
        return entries[-VECTOR_TOP_K:]

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(VECTOR_TOP_K, total),
        include=["documents", "metadatas", "distances"],
    )
    return [{"timestamp": m["timestamp"], "summary": d}
            for m, d in zip(result["metadatas"][0], result["documents"][0])]


def save_entry_to_chroma(timestamp: str, summary: str, title: str) -> bool:
    try:
        collection = get_collection()
        embedding  = get_embedding(summary)
        metadata   = {"timestamp": timestamp, "title": title}
        if embedding:
            collection.add(ids=[timestamp], embeddings=[embedding],
                           documents=[summary], metadatas=[metadata])
        else:
            collection.add(ids=[timestamp], documents=[summary], metadatas=[metadata])
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────
# JSON I/O  — format must stay identical to telmi.py
# ─────────────────────────────────────────────

def load_memory_json() -> list:
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # legacy format: {"memory": "<plain text>"}
        if isinstance(data, dict) and "memory" in data and isinstance(data["memory"], str):
            if data["memory"].strip():
                return [{"timestamp": "Archive (legacy)", "title": "", "summary": data["memory"]}]
            return []
        return data.get("entries", [])
    except Exception:
        return []


def save_memory_json(entries: list) -> bool:
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"entries": entries}, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False


def load_profile() -> str:
    if not os.path.exists(PROFILE_FILE):
        return ""
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("notes", "")
    except Exception:
        return ""


def save_profile(notes: str) -> bool:
    try:
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "notes": notes,
            }, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────

def build_system_prompt(relevant_entries: list[dict], mode: str = "day") -> dict:
    if relevant_entries:
        memory_text = "\n\n".join(
            [f"[{e['timestamp']}]\n{e['summary']}" for e in relevant_entries]
        )
    else:
        memory_text = "No previous conversations on record."

    if mode == "day":
        return {
            "role": "system",
            "content": (
                "You are Telmi, a calm personal reflection companion. "
                "You know the user from past conversations.\n\n"
                f"RELEVANT SESSION MEMORIES:\n{memory_text}\n\n"
                "BEHAVIORAL RULES:\n"
                "1. If the user is simply sharing (no explicit question): "
                "validate and reflect back. No advice, no follow-up questions.\n"
                "2. If the user explicitly asks for your opinion: be direct and concrete.\n"
                "3. If the user wants help or advice: be practical and action-oriented.\n"
                "4. Only reference memories when there is a direct, natural connection.\n\n"
                "FORBIDDEN:\n"
                "- 'As an AI I have no feelings' or similar distancing phrases\n"
                "- Hollow empathy phrases like 'That sounds really challenging for you'\n"
                "- Unsolicited advice or questions\n"
                "- Sweeping philosophical conclusions drawn from small everyday things"
            ),
        }
    else:  # mind
        profile_text = load_profile()
        profile_section = (
            f"USER PROFILE (cumulative therapist notes):\n{profile_text}"
            if profile_text else
            "USER PROFILE: No profile yet — this is an early session."
        )
        return {
            "role": "system",
            "content": (
                "You are Telmi, acting as a skilled psychotherapist. "
                "You have worked with this user across multiple sessions.\n\n"
                f"{profile_section}\n\n"
                f"RELEVANT SESSION MEMORIES:\n{memory_text}\n\n"
                "YOUR APPROACH:\n"
                "1. Ask sharp, targeted questions that push the user to examine their own thinking.\n"
                "2. Identify and name patterns — emotional, behavioral, cognitive — as you notice them.\n"
                "3. Don't just mirror. Reflect with interpretation: "
                "'It sounds like you believe X — is that accurate?'\n"
                "4. Connect what the user says to known patterns from the profile when relevant.\n"
                "5. Gently challenge contradictions or avoidance without being confrontational.\n"
                "6. One question per response — focused, not a list.\n\n"
                "FORBIDDEN:\n"
                "- 'As an AI I have no feelings' or similar distancing phrases\n"
                "- Generic validation without substance\n"
                "- Multiple questions in one response\n"
                "- Diagnosing or labeling the user with clinical terms"
            ),
        }


# ─────────────────────────────────────────────
# Profile update (mind mode)
# ─────────────────────────────────────────────

def update_profile_from_session(history_text: str, summary: str, selected_model: str) -> str | None:
    existing = load_profile()
    profile_context = (
        f"EXISTING PROFILE NOTES:\n{existing}\n\n" if existing
        else "EXISTING PROFILE NOTES: None yet.\n\n"
    )
    prompt = (
        "You are taking factual notes after a therapy session. "
        "Your only job is to record what the user explicitly said or directly demonstrated — nothing else.\n\n"
        f"{profile_context}"
        f"SESSION SUMMARY:\n{summary}\n\n"
        f"FULL SESSION TRANSCRIPT:\n{history_text}\n\n"
        "Write down observations from this session that are NOT already in the existing profile.\n\n"
        "STRICT EVIDENCE RULE:\n"
        "Every single observation you write must be directly traceable to something the user "
        "said or did in the transcript above. If you cannot point to a specific line or statement "
        "that supports it, do not write it. No exceptions.\n\n"
        "WHAT TO NOTE (only if the user explicitly expressed it):\n"
        "- Things the user stated as facts about their life, relationships, or situation\n"
        "- Emotions or reactions the user named themselves\n"
        "- Patterns or behaviors the user described themselves doing\n"
        "- Beliefs or values the user expressed in their own words\n"
        "- Conflicts or tensions the user explicitly mentioned\n\n"
        "STRICTLY FORBIDDEN:\n"
        "- Psychological interpretations not stated by the user ('You seem to fear...')\n"
        "- Inferences about underlying causes, motives, or subconscious patterns\n"
        "- Assumptions about what the user 'really' feels or believes\n"
        "- Filling gaps with plausible-sounding psychology\n"
        "- Anything the user did not say — even if it seems likely\n\n"
        "FORMAT:\n"
        "- Write in second person: 'You said...', 'You described...', 'You mentioned...'\n"
        "- Plain text paragraphs only — no bullet points, no headers\n"
        "- Only write what is genuinely new — do not repeat anything already in the profile\n"
        "- If the conversation is too short or too shallow to support any observation "
        "(e.g. only one or two messages, or only small talk), output exactly: NO_NEW_OBSERVATIONS\n"
        "- If there is nothing new to record, output exactly: NO_NEW_OBSERVATIONS\n"
        "- Output only the new notes, no preamble, no labels"
    )
    try:
        response = ollama.chat(
            model=selected_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2},
        )
        raw = response["message"]["content"].strip()
        if not raw or raw == "NO_NEW_OBSERVATIONS":
            return None
        return raw
    except Exception:
        return None


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/status")
def get_status():
    try:
        result = ollama.list()
        models = [m["model"] for m in result["models"]]
        embedding_ok = any("nomic-embed-text" in m for m in models)
        return {"ollama_running": True, "models": models, "embedding_ok": embedding_ok}
    except Exception:
        return {"ollama_running": False, "models": [], "embedding_ok": False}


@app.get("/models", response_model=list[str])
def list_models():
    try:
        models = ollama.list()
        return [m["model"] for m in models["models"]]
    except Exception:
        return []


@app.post("/chat")
def chat(request: ChatRequest):
    relevant         = get_relevant_entries(request.user_input)
    system_prompt    = build_system_prompt(relevant, request.mode)
    messages_for_llm = [system_prompt] + [m.model_dump() for m in request.history]

    def generate():
        for chunk in ollama.chat(
            model=request.selected_model,
            messages=messages_for_llm,
            stream=True,
        ):
            if "message" in chunk and "content" in chunk["message"]:
                yield chunk["message"]["content"]

    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/save", response_model=SaveResponse)
def save_session(request: SaveRequest):
    user_messages = [m for m in request.history if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No conversation to save yet.")

    # Skip the opening assistant intro message when building the transcript
    convo = (request.history[1:]
             if request.history and request.history[0].role == "assistant"
             else request.history)
    history_text = "\n".join(
        [f"{m.role.capitalize()}: {m.content}" for m in convo]
    )

    summary_prompt = (
        f"Here is today's conversation:\n\n{history_text}\n\n"
        "Return exactly two things, nothing else:\n\n"
        "TITLE: a single line, max 8 words, capturing what was on the user's mind today\n"
        "SUMMARY: written from Telmi's perspective about the USER. "
        "Write 'You' when referring to the user. Never describe the conversation itself. "
        "Never mention Telmi. Only what the user brought up and their mood.\n\n"
        "RULES:\n"
        "- Focus entirely on the user, not the exchange\n"
        "- No meta-commentary like 'the conversation was about'\n"
        "- No poetry, no life lessons\n"
        "- If the conversation is very short or contains only greetings, write a minimal honest "
        "summary of exactly what happened — e.g. 'You stopped by briefly and said hi.' "
        "Do not invent emotions or assume context that isn't there. Just describe what is literally present.\n"
        "- Output only TITLE: and SUMMARY: labels, nothing else"
    )

    try:
        summary_response = ollama.chat(
            model=request.selected_model,
            messages=[{"role": "user", "content": summary_prompt}],
            options={"temperature": 0.1},
        )
        raw = summary_response["message"]["content"]

        title         = ""
        summary_lines = []
        in_summary    = False
        for line in raw.splitlines():
            if line.startswith("TITLE:"):
                title      = line.replace("TITLE:", "").strip()
                in_summary = False
            elif line.startswith("SUMMARY:"):
                summary_lines.append(line.replace("SUMMARY:", "").strip())
                in_summary = True
            elif in_summary and line.strip():
                summary_lines.append(line.strip())
        summary = " ".join(summary_lines)
        if not summary:
            summary = raw.strip()
        if not title:
            title = summary[:60]

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_entry_to_chroma(timestamp, summary, title)

        entries = load_memory_json()
        entries.append({
            "timestamp": timestamp,
            "title": title,
            "summary": summary,
            "history": [m.model_dump() for m in request.history],
        })
        save_memory_json(entries)

        profile_update = None
        if request.mode == "mind":
            new_observations = update_profile_from_session(
                history_text, summary, request.selected_model
            )
            if new_observations:
                existing = load_profile()
                ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated  = (existing + f"\n\n[{ts}]\n" + new_observations
                            if existing else new_observations)
                save_profile(updated)
                profile_update = new_observations

        return SaveResponse(
            title=title,
            summary=summary,
            timestamp=timestamp,
            profile_update=profile_update,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {e}")


@app.get("/calendar-data", response_model=list[CalendarDay])
def get_calendar_data():
    entries = load_memory_json()
    result = []
    for e in entries:
        ts = e.get("timestamp", "")
        if not ts or ts == "Archive (legacy)":
            continue
        result.append(CalendarDay(
            date=ts[:10],
            timestamp=ts,
            title=e.get("title", ""),
            summary=e.get("summary", "")[:200],
        ))
    return result


@app.get("/entries", response_model=list[Entry])
def list_entries():
    return get_all_entries()


@app.get("/search", response_model=list[Entry])
def search_entries(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=200),
):
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []

    query_embedding = get_embedding(q)
    if query_embedding is None:
        raise HTTPException(
            status_code=503,
            detail="Embedding-Modell nicht verfügbar. Bitte prüfen ob Ollama läuft.",
        )

    n_results = min(limit, total)
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    entries = []
    for m, d, dist in zip(result["metadatas"][0], result["documents"][0], result["distances"][0]):
        if dist <= SEARCH_DISTANCE_THRESHOLD:
            entries.append(Entry(
                timestamp=m.get("timestamp", ""),
                title=m.get("title", ""),
                summary=d,
            ))
    return entries


@app.put("/entries/{timestamp}", response_model=Entry)
def update_entry(timestamp: str, request: UpdateEntryRequest):
    collection = get_collection()
    existing   = collection.get(ids=[timestamp], include=["documents", "metadatas"])

    if not existing["ids"]:
        raise HTTPException(status_code=404, detail="Entry not found")

    current_summary  = existing["documents"][0]
    current_metadata = existing["metadatas"][0]

    new_summary  = request.summary if request.summary is not None else current_summary
    new_title    = request.title   if request.title   is not None else current_metadata.get("title", "")
    new_metadata = {"timestamp": timestamp, "title": new_title}

    if request.summary is not None:
        new_embedding = get_embedding(new_summary)
        if new_embedding:
            collection.update(ids=[timestamp], embeddings=[new_embedding],
                              documents=[new_summary], metadatas=[new_metadata])
        else:
            collection.update(ids=[timestamp],
                              documents=[new_summary], metadatas=[new_metadata])
    else:
        collection.update(ids=[timestamp], metadatas=[new_metadata])

    entries = load_memory_json()
    for entry in entries:
        if entry["timestamp"] == timestamp:
            entry["title"]   = new_title
            entry["summary"] = new_summary
            break
    save_memory_json(entries)

    return Entry(timestamp=timestamp, title=new_title, summary=new_summary)


@app.get("/entries/{timestamp}/chat", response_model=list[ChatMessage])
def get_entry_chat(timestamp: str):
    entries = load_memory_json()
    for entry in entries:
        if entry["timestamp"] == timestamp:
            history = entry.get("history")
            if not history:
                raise HTTPException(status_code=404, detail="No chat history stored for this entry.")
            return [ChatMessage(**m) for m in history]
    raise HTTPException(status_code=404, detail="Entry not found.")


@app.delete("/entries/{timestamp}")
def delete_entry(timestamp: str):
    collection = get_collection()
    existing   = collection.get(ids=[timestamp])

    if not existing["ids"]:
        raise HTTPException(status_code=404, detail="Entry not found")

    collection.delete(ids=[timestamp])

    entries = load_memory_json()
    entries = [e for e in entries if e["timestamp"] != timestamp]
    save_memory_json(entries)

    return {"deleted": timestamp}


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import multiprocessing
    import uvicorn
    multiprocessing.freeze_support()
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
