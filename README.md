# Tell Me Your Day 📓

Ein lokaler, privater KI-Reflexionsbegleiter. Läuft vollständig auf deinem Computer – keine Cloud, keine API-Kosten, keine Datenweitergabe.

Gebaut auf **Gemma 4 E2B** – Googles aktuell leistungsfähigstes kompaktes Modell. Multimodal, kontextstark, und schnell genug für flüssige Konversation auf Consumer-Hardware. Das Setup ist explizit auf Gemma 4 E2B ausgerichtet und dort am besten getestet.

## Voraussetzungen

- [Ollama](https://ollama.com) installiert und gestartet
- Python 3.10 oder neuer

## Setup

1. Modelle laden:
```bash
ollama pull gemma4:e2b
ollama pull nomic-embed-text
```

2. Dependencies installieren:
```bash
pip3 install -r requirements.txt
```

3. App starten:
```bash
python3 -m streamlit run tellyourday.py
```

Das war's. Die App läuft standardmäßig mit `gemma4:e2b`. Wer ein anderes Modell verwenden möchte, trägt es einfach in `config.yaml` ein:

```yaml
chat_model: "anderes-modell"
embed_model: "nomic-embed-text"
```

> **macOS:** Verwende immer `python3 -m streamlit run` statt `streamlit run`

## Datenschutz

Deine Gespräche bleiben lokal. `memory.json` und `chroma_db/` werden nicht auf GitHub hochgeladen.
