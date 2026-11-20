# Smart Diet Assistant

English · [简体中文](README.zh-CN.md)

A Qt desktop app for photo-based dish recognition, meal logging, and nutrition Q&A, backed by FastAPI and MySQL.

## Features

- **Dish recognition** — Identify dishes from a photo, then confirm or correct the result.
- **Meal and health tracking** — Record portions, review daily and weekly nutrition totals, and track weight.
- **Multi-turn Q&A** — Ask what you ate, calculate nutrients for a given portion, or look up a recipe.
- **Exercise plans and check-ins** — Generate a daily plan and mark completed activities.

## How it works

- **Vision fine-tuning** — MiniCPM-V was fine-tuned with LoRA on dish images prepared from ChineseFoodNet. During inference, the fine-tuned model proposes a dish name. The base model checks the prediction, identifies the dish itself if it rejects the proposal, and provides an ingredient description.
- **Recipe RAG and database queries** — The language model resolves follow-up references and produces a structured query plan. Python validates it, queries MySQL with parameterized SQL, and calculates nutrients from portion weights. Recipe questions use a BGE-M3 and Chroma index of 300 recipes, with optional BM25 hybrid retrieval. The language model then answers using the database results and retrieved recipe excerpts.

## Project structure

```text
smart-diet-assistant/
├── src/                    # Qt/C++ desktop client
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── ai/                  # Vision service and model clients
│   ├── rag/                 # Query planning, retrieval, and response generation
│   ├── services/            # Meal, nutrition, and recognition logic
│   ├── dao/                 # Database queries
│   ├── database/            # MySQL schema and seed data
│   ├── data/                # Recipes and nutrition reference data
│   ├── scripts/             # Index building and utility scripts
│   └── evals/               # Retrieval benchmarks
├── dataset/                # Vision fine-tuning manifests
├── build_dataset.py        # Vision dataset preparation
└── tests/                  # Automated tests
```
