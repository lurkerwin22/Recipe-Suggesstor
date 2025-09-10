# 🍽️ Recipe Suggester (CrewAI + Gemini)

## Overview

A command-line **Recipe Suggester** that uses **CrewAI** agents and a Google *Gemini* LLM to propose structured, ingredient-driven recipes.  
Given an ingredient list (via CLI or file), the application asks an agent to return a constrained JSON array of recipe objects that maximize use of the provided ingredients.

## Features

- Parse ingredient lists from CLI or text/JSON files.
- Build a tightly constrained task for an LLM agent (CrewAI) to return **JSON-only** structured recipes.
- Output normalized JSON to `outputs.json` for downstream consumption (apps, UIs).
- Robust extraction of JSON from noisy LLM output; fallbacks for inspection.

## Project layout

```
.
├── main.py                # CLI entrypoint, agent/task orchestration, JSON normalization
├── requirements.txt       # (optional) list of Python dependencies
├── examples/              # (optional) sample ingredient files
└── outputs.json           # Generated result (created at runtime)
```

## Requirements

- Python 3.9+  
- Dependencies (install via `pip`): `crewai`, `langchain`, `langchain-community`, `pypdf` (if you reuse loaders), and any HTTP/SDK libs required by your provider.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate     # macOS / Linux
.venv\Scripts\activate      # Windows (PowerShell)
pip install crewai langchain langchain-community pypdf
```

## Configuration & Security

- **Do not hardcode API keys.** Place keys in environment variables or a `.env` file (see below). Hardcoded keys in source are a security risk and must be removed before publishing. See official best practices on API key safety. citeturn0search14

- Example `.env` usage (via `python-dotenv`):
  1. Add `.env` at repo root:
     ```
     CREWAI_API_KEY=your_crewai_key
     GEMINI_API_KEY=your_google_key
     ```
  2. Load in Python (example):
     ```py
     from dotenv import load_dotenv
     load_dotenv()
     import os
     CREWAI_API_KEY = os.getenv("CREWAI_API_KEY")
     ```
  Using `python-dotenv` follows 12-factor app practices. citeturn0search3

## How it works (short)

1. Parse ingredients from `--ingredients` or `--file` CLI flags.  
2. Compose a constrained `Task` for CrewAI that requires JSON output following a strict schema.  
3. Run the `Crew.kickoff()` flow to get the agent output. CrewAI is used to orchestrate agents and tasks. citeturn0search5turn0search10  
4. Attempt to parse the returned content as JSON (with regex fallback). If parse fails, write raw output for debugging.

## CLI Usage

```bash
python main.py --ingredients "chicken, garlic, rice" --recipes 3 --servings 2
# or
python main.py --file ingredients.txt --recipes 4
```

Output is written to `outputs.json` (overwritten each run).

## Key implementation notes

- The script uses `langchain` loaders and text splitters in other projects to handle long documents; `PyPDFLoader` and `RecursiveCharacterTextSplitter` are useful tools when you need to extract and chunk long textual sources. If you reuse those capabilities, follow LangChain docs. citeturn1search2turn1search1
- The prompt enforces a strict JSON schema and constraints (max missing ingredients, no external links, fixed fields) to encourage structured output suitable for programmatic consumption.
- The code includes helper functions to normalize/deserialize SDK-returned objects into Python primitives for JSON serialization.

## Security & Operational recommendations

- Remove any hardcoded API keys and rotate exposed keys immediately. citeturn0search14
- Run LLMs behind a backend service; avoid exposing keys in client-side code or public repos.
- Add rate-limit handling and retries (the project already attempts to parse and handle outputs).

## Suggested improvements (prioritized)

1. **Secrets & Configuration**  
   - Move API keys into `.env` and load with `python-dotenv`. Add `.env` to `.gitignore`. citeturn0search3

2. **Input validation & richer parsers**  
   - Improve ingredient parsing for quantities, units, and synonyms (e.g., `scallions` → `green onion`), optionally with a small NLP normalization layer.

3. **Output schema validation**  
   - Use `pydantic` models to validate the JSON schema returned by the agent and reject malformed recipes.

4. **Retries & Observability**  
   - Add robust retry logic and structured logging (timestamps, unique request IDs, LLM latency). Consider tracing with OpenTelemetry.

5. **Unit & Integration Tests**  
   - Add tests for parsing, `suggest_recipes()` behavior (mock CrewAI responses), and CLI flows.

6. **Rate-limiting & Cost Controls**  
   - If running on paid LLMs, add safeguards for token usage, e.g., cap max tokens and sample frequency.

7. **UI / UX**  
   - Add a small Streamlit or Flask UI to upload ingredient lists and display recipe cards.

## References

- CrewAI docs — building agents and crews. citeturn0search5turn0search10  
- LangChain — document loaders & text splitters (PyPDFLoader, RecursiveCharacterTextSplitter). citeturn1search2turn1search1  
- Google Gemini API (structured output & models). citeturn0search2  
- python-dotenv (12-factor config). citeturn0search3  
- API key safety best practices (example guidance). citeturn0search14



