# Telmi — Local AI Journal

*Tell me your day. Tell me your mind.*

Your thoughts stay on your machine. No cloud. No subscription. No one reading your diary.

Telmi is an AI journaling companion that runs entirely on your laptop. Talk about your day. Work through what's on your mind. Telmi listens, remembers, and gets better at knowing you — without sending a single word to a server.

---

## Two modes. One purpose.

**📓 Tell me your day** — a daily journaling space. Reflect on what happened, what you're feeling, what's next. Telmi asks follow-up questions and builds a running memory of your life over time.

**🧠 Tell me your mind** — a deeper mode for working things through. Telmi tracks what matters to you across sessions and refers back to it when relevant. Like having a therapist who actually remembers.

---

## What makes it different

- **Fully local.** Everything runs on your computer. Nothing is ever sent to a server.
- **No subscription.** No API key. No usage limits. You own the models, you own the data.
- **Runs on 8 GB RAM.** No GPU required. Works on everyday hardware.
- **Remembers you.** Past conversations are stored and retrieved — Telmi doesn't start from scratch every time.
- **Open models.** Switch between any model you have installed in Ollama. Upgrade when you want.

---

## Setup

**1. Install [Ollama](https://ollama.com) and start it.**

**2. Pull the embedding model:**
```bash
ollama pull nomic-embed-text
```

**3. Install Python dependencies:**
```bash
pip3 install -r requirements.txt
```

**4. Run Telmi:**
```bash
python3 -m streamlit run telmi.py
```

> **macOS:** Always use `python3 -m streamlit run`, not `streamlit run`

On first launch, Telmi walks you through picking and downloading a chat model. Recommended starting points:

| RAM   | Model                                  |
|-------|----------------------------------------|
| 8 GB  | `gemma4:e2b` · `llama3.2:3b`          |
| 16 GB | `llama3.1:8b` · `mistral:7b`          |
| 32 GB+ | `llama3.1:70b` · `qwen2.5:32b`       |

---

## Privacy

`memory.json`, `profile.json`, and `chroma_db/` live on your machine and are excluded from git. Telmi never phones home.
