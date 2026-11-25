# Smart Diet Assistant

English · [简体中文](README.zh-CN.md)

Smart Diet Assistant is a Windows desktop app for tracking meals and weight, identifying Chinese dishes from photos, and asking questions about nutrition and recipes. A Qt client connects to a FastAPI backend that combines personal records in MySQL with a searchable recipe collection.

## Features

- **Accounts and health profiles** — Register or sign in, then manage weight, activity level, calorie targets, and allergies.
- **Photo-based dish recognition** — Select or drop in a photo to see a proposed dish and its main ingredients. Confirm or correct the result before logging the meal. Saved corrections can appear as alternative candidates on later requests.
- **Meal logging and statistics** — Add food manually or from a recognition result, choose a meal and portion, and view daily and weekly totals for calories, protein, fat, carbohydrates, fibre, and sodium. Log weight and view trends.
- **Multi-turn nutrition and recipe chat** — Review logged intake, calculate nutrition for a specified portion, or ask about ingredients and cooking steps. A single question can use both sources, such as “How many calories did I log for lunch yesterday, and how long should I steam sea bass?” The Qt client streams replies and keeps conversation history.
- **Exercise planning and check-ins** — Generate a daily plan using logged intake, a goal, and preferred activities. Confirm the plan, check off tasks, and review completion.

## Technology stack

| Layer | Technologies |
| --- | --- |
| Desktop | Qt 6 Widgets, C++17, Qt Network, qmake |
| API and storage | Python, FastAPI, Uvicorn, MySQL 8, MySQL Connector/Python |
| Vision | MiniCPM-V 4.6, LoRA, ChineseFoodNet, LLaMA-Factory, PyTorch, Hugging Face Transformers |
| Recipe retrieval | LangChain, Sentence Transformers, local BGE-M3 embeddings, Chroma, optional jieba and BM25 |
| Conversation | OpenAI-compatible cloud API, with DeepSeek configured by default, and server-sent events (SSE) for streaming |

## How it works

### Dish recognition

The training pipeline samples images across **208 ChineseFoodNet dish categories** and writes ShareGPT-style training and validation manifests. MiniCPM-V 4.6 was fine-tuned with LoRA using LLaMA-Factory.

At runtime, the fine-tuned model proposes a dish name. The base model checks the name against the photo, makes a new prediction if it rejects the proposal, and supplies an ingredient description. The backend then matches the result against its food catalogue. For dishes outside the catalogue, the app can request a model-based nutrition estimate, which should be treated as an estimate.

### Recipe RAG and database queries

1. **Plan the query.** The cloud language model resolves references in recent dialogue and produces a structured plan for personal records, portion-based nutrition, and recipe lookup. Python validates the plan and falls back to rules on the original question if validation fails.
2. **Query the requested sources.** MySQL holds **13 tables**, including food nutrition references, source metadata, meal logs, profiles, and chat records. Python uses parameterized SQL for database lookups and converts common weight units to grams before calculating nutrition. Recipe search uses **300 curated recipes** from HowToCook, split into **1,342 text chunks** with dish and section metadata.
3. **Rank recipe evidence and generate the reply.** Dense BGE-M3 retrieval is the default. Optional BM25 keyword retrieval uses jieba segmentation. Hybrid mode combines the two rankings with reciprocal rank fusion (RRF). The selected top-K chunks and any database results go to the language model, which generates an answer with recipe `[R1]` and nutrition `[D1]` references where applicable.

### Evaluation

- The [recipe retrieval benchmark](backend/evals/README.md) contains **200 questions** with development and held-out splits. It measures chunk-level evidence hits, multi-fact evidence coverage, and performance on questions with insufficient evidence. Dense, BM25, and hybrid retrieval can be compared on the same questions.
- The [database and query-planning benchmarks](backend/evals/DATABASE_RAG.md) check date and meal selection, portion calculations, recipe citations, and colloquial follow-ups. On the same development questions, the original joint suite improved from **4/9 to 9/9**, and the colloquial query-planning suite improved from **10/12 to 12/12**.

## Run locally

From the repository root, use a Python environment with the backend dependencies and have a local MySQL server running. The current backend has been tested with Python 3.12.

```powershell
python -m pip install -r backend/requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set your MySQL connection values in `.env`, then initialize the database.

```powershell
Push-Location backend
python init_db.py
Pop-Location
```

For chat, configure `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` in `.env`. To enable dense or hybrid recipe retrieval, set `RAG_EMBEDDING_MODEL_PATH` to a local BGE-M3 checkpoint and build a Chroma index in a new or empty directory. If a compatible index already exists, set `RAG_INDEX_PATH` to it and skip the build command. BM25-only mode can read the bundled Markdown recipes directly.

```powershell
python backend/scripts/build_rag_index.py
python backend/main.py
```

Open [src/nutritious-diet.pro](src/nutritious-diet.pro) in Qt Creator, select a Qt 6 desktop kit, and build and run the client. It connects to `http://127.0.0.1:8001` by default. The backend health endpoint is `/api/health`.

Photo recognition requires two additional processes. Start the fine-tuned MiniCPM-V model on an OpenAI-compatible endpoint (port `8000` by default), then run `python backend/ai/finetune_server.py` in a GPU-enabled Python environment. Set `MINICPM_BASE_MODEL_PATH` and `MINICPM_FINETUNED_API_URL` in that process's environment as needed. The main backend sends recognition requests to `FINETUNE_API_URL`, on port `8002` by default. Model weights and generated vector indexes are local assets.

## Project structure

```text
smart-diet-assistant/
├── src/                    # Qt/C++ screens, widgets, and HTTP clients
├── backend/
│   ├── main.py             # FastAPI entry point
│   ├── ai/                 # Vision service and cloud model client
│   ├── rag/                # Query planning, recipe retrieval, and reply generation
│   ├── services/           # Meal, nutrition, recognition, and exercise logic
│   ├── dao/                # MySQL data access
│   ├── database/           # MySQL schema and seed data
│   ├── data/               # Recipes and nutrition reference data
│   ├── scripts/            # Index building and data setup
│   └── evals/              # Retrieval, joint workflow, and query-planning benchmarks
├── dataset/                # Vision fine-tuning manifests
├── build_dataset.py        # ChineseFoodNet data preparation
└── tests/                  # Automated tests
```

Recipe provenance and licensing are recorded in [the HowToCook source notes](backend/data/knowledge_source/howtocook/SOURCE.md).
