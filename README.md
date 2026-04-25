# Tell Me Your Day 📓

Hi, this is my first GitHub project. It's vibe coded.

A local, private AI reflection companion. Runs entirely on your computer — no cloud, no API costs, no data sharing.

Built on **Gemma 4 E2B** — Google's most capable compact model. Multimodal, strong context handling, and fast enough for fluid conversation on consumer hardware. This setup is explicitly built and tested around Gemma 4 E2B.

## Requirements

- [Ollama](https://ollama.com) installed and running
- Python 3.10 or newer

## Setup

1. Pull the models:
```bash
ollama pull gemma4:e2b
ollama pull nomic-embed-text
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Start the app:
```bash
python3 -m streamlit run tellyourday.py
```

That's it. The app runs with `gemma4:e2b` by default. To use a different model, edit `config.yaml`:

```yaml
chat_model: "your-model-name"
embed_model: "nomic-embed-text"
```

> **macOS:** Always use `python3 -m streamlit run` instead of `streamlit run`

## Privacy

Your conversations stay local. `memory.json` and `chroma_db/` are excluded from GitHub via `.gitignore`.
