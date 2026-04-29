import os
import json
import calendar
import streamlit as st
import ollama
import chromadb
import plotly.graph_objects as go
from datetime import datetime, date, timedelta

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

MEMORY_FILE  = "memory.json"
PROFILE_FILE = "profile.json"
CHROMA_DIR   = "chroma_db"
COLLECTION   = "memory"
EMBED_MODEL  = "nomic-embed-text"

VECTOR_MIN_ENTRIES = 15
VECTOR_TOP_K       = 5

ONBOARDING_MODELS = [
    ("8 GB", [
        ("gemma4:e2b",    "Google's efficient 2B model. Fast and lightweight."),
        ("llama3.2:3b",   "Meta's compact 3B model. Snappy and capable."),
    ]),
    ("16 GB", [
        ("llama3.1:8b",   "Meta's 8B model. Solid quality for reflection and conversation."),
        ("mistral:7b",    "Mistral's 7B model. Sharp reasoning, great follow-up questions."),
    ]),
    ("32 GB+", [
        ("llama3.1:70b",  "Meta's full 70B model. Deep, nuanced, highly capable."),
        ("qwen2.5:32b",   "Alibaba's 32B model. Excellent for structured thought."),
    ]),
]


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

def get_available_models() -> list[str]:
    try:
        models = ollama.list()
        return [m["model"] for m in models["models"]]
    except Exception:
        return []


# ─────────────────────────────────────────────
# Embedding
# ─────────────────────────────────────────────

def get_embedding(text: str) -> list[float] | None:
    try:
        resp = ollama.embeddings(model=EMBED_MODEL, prompt=text)
        return resp["embedding"]
    except Exception as e:
        st.warning(f"Embedding error ({EMBED_MODEL}): {e}")
        return None


# ─────────────────────────────────────────────
# ChromaDB
# ─────────────────────────────────────────────

def get_collection() -> chromadb.Collection:
    if "chroma_collection" not in st.session_state:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        collection = client.get_or_create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
        st.session_state.chroma_collection = collection
    return st.session_state.chroma_collection


def count_entries() -> int:
    return get_collection().count()


def get_all_entries() -> list[dict]:
    result = get_collection().get(include=["documents", "metadatas"])
    entries = []
    for m, d in zip(result["metadatas"], result["documents"]):
        entries.append({
            "timestamp": m.get("timestamp", ""),
            "title":     m.get("title", ""),
            "summary":   d
        })
    entries.sort(key=lambda e: e["timestamp"])
    return entries


# ─────────────────────────────────────────────
# Streak
# ─────────────────────────────────────────────

def calculate_streaks(entries: list[dict]) -> tuple[int, int]:
    if not entries:
        return 0, 0

    days = sorted({
        datetime.strptime(e["timestamp"][:10], "%Y-%m-%d").date()
        for e in entries
        if len(e["timestamp"]) >= 10
    })

    if not days:
        return 0, 0

    today = date.today()
    current = 0
    check = today
    for d in reversed(days):
        if d == check:
            current += 1
            check -= timedelta(days=1)
        elif d < check:
            break

    longest = 1
    run = 1
    for i in range(1, len(days)):
        if days[i] == days[i - 1] + timedelta(days=1):
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    return current, max(longest, current)


# ─────────────────────────────────────────────
# Calendar (Plotly) — compact for sidebar
# ─────────────────────────────────────────────

def build_calendar(entries: list[dict], year: int, month: int):
    entry_map = {}
    for e in entries:
        d = e["timestamp"][:10]
        if d not in entry_map:
            entry_map[d] = {"title": e["title"], "summary": e["summary"]}

    today = date.today()
    cal = calendar.monthcalendar(year, month)
    day_names = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    x_vals, y_vals, colors, hover_texts, custom_dates, day_numbers = [], [], [], [], [], []
    num_weeks = len(cal)

    for week_idx, week in enumerate(cal):
        for day_idx, day in enumerate(week):
            x = day_idx
            y = num_weeks - 1 - week_idx

            if day == 0:
                x_vals.append(x); y_vals.append(y)
                colors.append("rgba(0,0,0,0)"); hover_texts.append("")
                custom_dates.append(""); day_numbers.append("")
                continue

            ds = f"{year:04d}-{month:02d}-{day:02d}"
            is_today   = (date(year, month, day) == today)
            has_entry  = ds in entry_map
            color      = "#a78bfa" if has_entry else ("#374151" if is_today else "#1e1e1e")
            title      = entry_map[ds]["title"] if has_entry else ""
            hover      = f"{ds}<br>{title}" if title else ds

            x_vals.append(x); y_vals.append(y); colors.append(color)
            hover_texts.append(hover); custom_dates.append(ds); day_numbers.append(str(day))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals, mode="markers+text",
        marker=dict(symbol="square", size=26, color=colors, line=dict(width=0)),
        text=day_numbers, textposition="middle center",
        textfont=dict(size=10, color="#e5e7eb"),
        hovertext=hover_texts, hovertemplate="%{hovertext}<extra></extra>",
        customdata=custom_dates,
    ))
    fig.add_trace(go.Scatter(
        x=list(range(7)), y=[num_weeks] * 7, mode="text",
        text=day_names, textfont=dict(size=9, color="#6b7280"), hoverinfo="skip",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=4, b=0), height=200, showlegend=False,
        xaxis=dict(visible=False, range=[-0.6, 6.6], fixedrange=True),
        yaxis=dict(visible=False, range=[-0.6, num_weeks + 0.6], fixedrange=True),
    )
    return fig, entry_map


# ─────────────────────────────────────────────
# Migration
# ─────────────────────────────────────────────

def migrate_json_to_chroma(entries: list) -> None:
    if not entries:
        return
    collection = get_collection()
    existing_ids = set(collection.get()["ids"])
    migrated = 0
    for entry in entries:
        entry_id = entry["timestamp"]
        if entry_id in existing_ids:
            continue
        embedding = get_embedding(entry["summary"])
        metadata = {"timestamp": entry["timestamp"], "title": entry.get("title", "")}
        if embedding:
            collection.add(ids=[entry_id], embeddings=[embedding],
                           documents=[entry["summary"]], metadatas=[metadata])
        else:
            collection.add(ids=[entry_id], documents=[entry["summary"]], metadatas=[metadata])
        migrated += 1
    if migrated:
        st.toast(f"{migrated} older entries migrated into vector database.")


# ─────────────────────────────────────────────
# Save entry
# ─────────────────────────────────────────────

def save_entry_to_chroma(timestamp: str, summary: str, title: str) -> bool:
    try:
        collection = get_collection()
        embedding = get_embedding(summary)
        metadata = {"timestamp": timestamp, "title": title}
        if embedding:
            collection.add(ids=[timestamp], embeddings=[embedding],
                           documents=[summary], metadatas=[metadata])
        else:
            collection.add(ids=[timestamp], documents=[summary], metadatas=[metadata])
        return True
    except Exception as e:
        st.error(f"ChromaDB error while saving: {e}")
        return False


# ─────────────────────────────────────────────
# Memory retrieval
# ─────────────────────────────────────────────

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
        include=["documents", "metadatas", "distances"]
    )
    return [{"timestamp": m["timestamp"], "summary": d}
            for m, d in zip(result["metadatas"][0], result["documents"][0])]


# ─────────────────────────────────────────────
# JSON backup
# ─────────────────────────────────────────────

def load_memory_json() -> list:
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "memory" in data and isinstance(data["memory"], str):
            if data["memory"].strip():
                return [{"timestamp": "Archive (legacy)", "title": "", "summary": data["memory"]}]
            return []
        return data.get("entries", [])
    except Exception as e:
        st.error(f"Error loading {MEMORY_FILE}: {e}")
        return []


def save_memory_json(entries: list) -> bool:
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"entries": entries}, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving {MEMORY_FILE}: {e}")
        return False


# ─────────────────────────────────────────────
# Profile — Tell me your mind
# ─────────────────────────────────────────────

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
                "notes": notes
            }, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving {PROFILE_FILE}: {e}")
        return False


def update_profile_from_session(history_text: str, summary: str) -> str | None:
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
            model=st.session_state.selected_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2}
        )
        raw = response["message"]["content"].strip()
        if not raw or raw == "NO_NEW_OBSERVATIONS":
            return None
        return raw
    except Exception as e:
        st.error(f"Error updating profile: {e}")
        return None


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
            )
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
            )
        }


# ─────────────────────────────────────────────
# Intro messages
# ─────────────────────────────────────────────

def get_intro_message(mode: str) -> str:
    if mode == "day":
        return (
            "Hey, I'm Telmi — your personal reflection companion.\n\n"
            "I'm here to listen. Just tell me what's been on your mind today — "
            "big or small, good or bad.\n\n"
            "I remember our past conversations and I'm curious how you're doing."
        )
    else:
        return (
            "Hey, I'm Telmi — let's go a little deeper today.\n\n"
            "What's been on your mind? Pick something specific — "
            "a situation, a feeling, a thought you keep coming back to.\n\n"
            "We'll look at it together."
        )


# ─────────────────────────────────────────────
# Save logic
# ─────────────────────────────────────────────

def run_save_flow(mode: str):
    msgs = st.session_state.messages_day if mode == "day" else st.session_state.messages_mind
    user_messages = [m for m in msgs if m["role"] == "user"]

    if not user_messages:
        st.session_state.save_warning = "No conversation to save yet."
        return

    convo = msgs[1:] if msgs and msgs[0]["role"] == "assistant" else msgs
    history_text = "\n".join(
        [f"{m['role'].capitalize()}: {m['content']}" for m in convo]
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
            model=st.session_state.selected_model,
            messages=[{"role": "user", "content": summary_prompt}],
            options={"temperature": 0.1}
        )
        raw = summary_response["message"]["content"]

        title = ""
        summary_lines = []
        in_summary = False
        for line in raw.splitlines():
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
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
        chroma_ok = save_entry_to_chroma(timestamp, summary, title)

        new_entry = {"timestamp": timestamp, "title": title, "summary": summary}
        st.session_state.json_entries.append(new_entry)
        save_memory_json(st.session_state.json_entries)
        st.session_state.all_entries = get_all_entries()

        if chroma_ok:
            st.session_state.model_changed = False
            saved = {"title": title, "summary": summary, "profile_update": None}
            if mode == "day":
                st.session_state.already_saved_day = True
                st.session_state.last_saved_day = saved
            else:
                st.session_state.already_saved_mind = True
                st.session_state.last_saved_mind = saved

        if mode == "mind":
            new_observations = update_profile_from_session(history_text, summary)
            if new_observations:
                existing = load_profile()
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = (existing + f"\n\n[{ts}]\n" + new_observations) if existing else new_observations
                save_profile(updated)
                if st.session_state.last_saved_mind:
                    st.session_state.last_saved_mind["profile_update"] = new_observations

    except Exception as e:
        st.session_state.save_error = f"Error generating summary: {e}"


# ─────────────────────────────────────────────
# Onboarding
# ─────────────────────────────────────────────

def render_onboarding():
    available = get_available_models()
    if st.query_params.get("onboarding") == "1":
        available = []

    # If a download was triggered, run it now
    if st.session_state.downloading_model:
        model = st.session_state.downloading_model
        st.markdown(f"### Downloading {model}")
        status_el    = st.empty()
        progress_bar = st.progress(0.0)
        status_el.caption("Starting download...")
        try:
            for chunk in ollama.pull(model, stream=True):
                status    = chunk.get("status", "")
                completed = chunk.get("completed") or 0
                total     = chunk.get("total") or 0
                if status:
                    status_el.caption(status)
                if total > 0:
                    progress_bar.progress(min(completed / total, 1.0))
            progress_bar.progress(1.0)
            status_el.caption("Download complete!")
            st.session_state.selected_model    = model
            st.session_state.downloading_model = None
            st.session_state.show_onboarding   = False
        except Exception as e:
            st.session_state.download_error    = f"{type(e).__name__}: {e}"
            st.session_state.downloading_model = None
        st.rerun()
        return

    # Header
    if available:
        col_back, _ = st.columns([1, 4])
        with col_back:
            if st.button("← Back to chat", use_container_width=True):
                st.session_state.show_onboarding = False
                st.rerun()
        st.markdown("### Download more models")
        st.caption("Models already installed are marked below. Click Download to add more.")
    else:
        st.markdown("### Get started")
        st.caption("Download a model to begin. Choose based on your device's RAM.")

    # Show any error from the previous download attempt
    if st.session_state.get("download_error"):
        st.error(f"Download failed — {st.session_state.download_error}")
        st.session_state.download_error = None

    # Model grid
    for ram_label, models in ONBOARDING_MODELS:
        st.divider()
        st.markdown(f"**{ram_label} RAM**")
        for model_name, description in models:
            col_info, col_btn = st.columns([4, 1])
            installed = model_name in available
            with col_info:
                label = f"**{model_name}**  ✓" if installed else f"**{model_name}**"
                st.markdown(label)
                st.caption(description)
            with col_btn:
                if installed:
                    if st.button("Use", key=f"use_{model_name}", use_container_width=True):
                        st.session_state.selected_model  = model_name
                        st.session_state.show_onboarding = False
                        st.rerun()
                else:
                    if st.button("Download", key=f"dl_{model_name}", use_container_width=True):
                        st.session_state.downloading_model = model_name
                        st.rerun()


# ─────────────────────────────────────────────
# Chat renderer (shared by both tabs)
# ─────────────────────────────────────────────

def render_chat(mode: str, messages_key: str, input_placeholder: str, input_key: str,
                already_saved_key: str, last_saved_key: str):
    msgs = getattr(st.session_state, messages_key)

    chat_container = st.container(height=500)
    with chat_container:
        for msg in msgs:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if user_input := st.chat_input(input_placeholder, key=input_key):
        st.session_state.app_mode = mode
        msgs.append({"role": "user", "content": user_input})

        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)

        relevant = get_relevant_entries(user_input)
        system_prompt = build_system_prompt(relevant, mode)
        messages_for_llm = [system_prompt] + msgs

        with chat_container:
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                try:
                    for chunk in ollama.chat(
                        model=st.session_state.selected_model,
                        messages=messages_for_llm,
                        stream=True
                    ):
                        if "message" in chunk and "content" in chunk["message"]:
                            full_response += chunk["message"]["content"]
                            response_placeholder.markdown(full_response + "▌")
                    response_placeholder.markdown(full_response)
                    msgs.append({"role": "assistant", "content": full_response})
                except Exception as e:
                    response_placeholder.empty()
                    st.error(f"Cannot reach Ollama. Is `ollama serve` running?\n\nError: {e}")

    already_saved = getattr(st.session_state, already_saved_key)
    last_saved    = getattr(st.session_state, last_saved_key)
    if already_saved and last_saved:
        st.success("Saved successfully!")
        st.info(f"**{last_saved['title']}**\n\n{last_saved['summary']}")
        if last_saved.get("profile_update"):
            st.info(f"**Profile updated:**\n\n{last_saved['profile_update']}")


# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────

st.set_page_config(page_title="Telmi", page_icon="📓", layout="centered")

# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────

if "show_onboarding" not in st.session_state:
    available = get_available_models()
    force_onboarding = st.query_params.get("onboarding") == "1"
    st.session_state.show_onboarding   = force_onboarding or len(available) == 0
    st.session_state.selected_model    = available[0] if available else ""
if "downloading_model" not in st.session_state:
    st.session_state.downloading_model = None
if "download_error" not in st.session_state:
    st.session_state.download_error = None
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "day"
if "messages_day" not in st.session_state:
    st.session_state.messages_day = [{"role": "assistant", "content": get_intro_message("day")}]
if "messages_mind" not in st.session_state:
    st.session_state.messages_mind = [{"role": "assistant", "content": get_intro_message("mind")}]
if "already_saved_day" not in st.session_state:
    st.session_state.already_saved_day = False
if "already_saved_mind" not in st.session_state:
    st.session_state.already_saved_mind = False
if "last_saved_day" not in st.session_state:
    st.session_state.last_saved_day = None
if "last_saved_mind" not in st.session_state:
    st.session_state.last_saved_mind = None
if "selected_model" not in st.session_state:
    st.session_state.selected_model = ""
if "json_entries" not in st.session_state:
    st.session_state.json_entries = load_memory_json()
if "cal_year" not in st.session_state:
    st.session_state.cal_year = date.today().year
if "cal_month" not in st.session_state:
    st.session_state.cal_month = date.today().month
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None
if "model_changed" not in st.session_state:
    st.session_state.model_changed = False
if "trigger_save" not in st.session_state:
    st.session_state.trigger_save = False
if "save_warning" not in st.session_state:
    st.session_state.save_warning = None
if "save_error" not in st.session_state:
    st.session_state.save_error = None

get_collection()
if not st.session_state.get("migration_done"):
    migrate_json_to_chroma(st.session_state.json_entries)
    st.session_state.migration_done = True

if "all_entries" not in st.session_state:
    st.session_state.all_entries = get_all_entries()

# ─────────────────────────────────────────────
# Handle save trigger
# ─────────────────────────────────────────────

if st.session_state.trigger_save:
    st.session_state.trigger_save = False
    mode  = st.session_state.app_mode
    label = "Saving and updating your profile..." if mode == "mind" else "Generating summary and saving..."
    with st.spinner(label):
        run_save_flow(mode)
    st.rerun()

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────

total = count_entries()

with st.sidebar:
    available_models = get_available_models()

    if available_models:
        current_index = (available_models.index(st.session_state.selected_model)
                         if st.session_state.selected_model in available_models else 0)
        new_model = st.selectbox("Model", available_models, index=current_index)

        if new_model != st.session_state.selected_model:
            has_unsaved = (
                (any(m["role"] == "user" for m in st.session_state.messages_day)
                 and not st.session_state.already_saved_day)
                or
                (any(m["role"] == "user" for m in st.session_state.messages_mind)
                 and not st.session_state.already_saved_mind)
            )
            if has_unsaved:
                st.session_state.model_changed = True
            st.session_state.selected_model = new_model

        if st.session_state.model_changed:
            st.warning("Save your conversation before the new model takes effect.")

        st.divider()

    # Save / New Session
    if not st.session_state.show_onboarding:
        mode         = st.session_state.app_mode
        already_saved = (st.session_state.already_saved_day if mode == "day"
                         else st.session_state.already_saved_mind)

        if already_saved:
            st.success("Session saved.")
            if st.button("New Session", use_container_width=True):
                if mode == "day":
                    st.session_state.messages_day      = [{"role": "assistant", "content": get_intro_message("day")}]
                    st.session_state.already_saved_day = False
                    st.session_state.last_saved_day    = None
                else:
                    st.session_state.messages_mind      = [{"role": "assistant", "content": get_intro_message("mind")}]
                    st.session_state.already_saved_mind = False
                    st.session_state.last_saved_mind    = None
                st.session_state.model_changed = False
                st.rerun()
        else:
            if st.button("End conversation & save", use_container_width=True):
                st.session_state.trigger_save = True
                st.rerun()

        if st.session_state.save_warning:
            st.warning(st.session_state.save_warning)
            st.session_state.save_warning = None
        if st.session_state.save_error:
            st.error(st.session_state.save_error)
            st.session_state.save_error = None

        st.divider()

    # Streak + calendar
    all_entries = st.session_state.all_entries
    current_streak, longest_streak = calculate_streaks(all_entries)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Streak", f"{current_streak}d")
    with col2:
        st.metric("Longest", f"{longest_streak}d")

    nav1, nav2, nav3 = st.columns([1, 3, 1])
    with nav1:
        if st.button("←", use_container_width=True, key="cal_prev"):
            if st.session_state.cal_month == 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
            else:
                st.session_state.cal_month -= 1
            st.session_state.selected_date = None
            st.rerun()
    with nav2:
        month_label = date(st.session_state.cal_year, st.session_state.cal_month, 1).strftime("%b %Y")
        st.markdown(
            f"<p style='text-align:center;margin:0;padding:4px 0;font-size:13px;'>{month_label}</p>",
            unsafe_allow_html=True
        )
    with nav3:
        if st.button("→", use_container_width=True, key="cal_next"):
            if st.session_state.cal_month == 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
            else:
                st.session_state.cal_month += 1
            st.session_state.selected_date = None
            st.rerun()

    fig, entry_map = build_calendar(all_entries, st.session_state.cal_year, st.session_state.cal_month)
    click_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="calendar")

    if click_data and click_data.get("selection", {}).get("points"):
        point   = click_data["selection"]["points"][0]
        clicked = point.get("customdata", "")
        if clicked and clicked in entry_map:
            st.session_state.selected_date = clicked

    if st.session_state.selected_date:
        sd = st.session_state.selected_date
        if sd in entry_map:
            st.caption(sd)
            if entry_map[sd]["title"]:
                st.caption(f"**{entry_map[sd]['title']}**")
            with st.expander("Read entry"):
                st.write(entry_map[sd]["summary"])

    st.divider()

    if available_models and not st.session_state.show_onboarding:
        if st.button("⬇ Download more models", use_container_width=True):
            st.session_state.show_onboarding = True
            st.rerun()
        st.divider()

    st.caption("""
**How it works**

Type freely — there's no right or wrong way to start. Just write what's on your mind.

When you're done, hit **End conversation & save**. Your session gets summarized and stored locally — no cloud, no data sharing.

To switch models, use the dropdown above. Start a **New Session** afterwards so the new model takes effect cleanly.

Your conversation history is used to personalize responses over time.
""")

    st.divider()
    st.caption(f"{total} memories stored")
    if total < VECTOR_MIN_ENTRIES:
        st.caption(f"Smart search activates at {VECTOR_MIN_ENTRIES} memories — {VECTOR_MIN_ENTRIES - total} to go.")

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if st.session_state.show_onboarding:
    render_onboarding()
else:
    tab_day, tab_mind = st.tabs(["📓 Tell me your day", "🧠 Tell me your mind"])

    with tab_day:
        render_chat(
            mode="day",
            messages_key="messages_day",
            input_placeholder="How was your day?",
            input_key="input_day",
            already_saved_key="already_saved_day",
            last_saved_key="last_saved_day",
        )

    with tab_mind:
        render_chat(
            mode="mind",
            messages_key="messages_mind",
            input_placeholder="What's on your mind?",
            input_key="input_mind",
            already_saved_key="already_saved_mind",
            last_saved_key="last_saved_mind",
        )
