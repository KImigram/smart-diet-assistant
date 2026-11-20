# Smart Diet Assistant

[简体中文](README.md) · [English](README.en.md)

A desktop app built with Qt and FastAPI for logging meals, tracking nutrition, and looking up recipes.

## Features

- **Photo-based dish recognition**: A fine-tuned MiniCPM-V model suggests dishes, the base model checks the prediction, and users can confirm or correct the result.
- **Meal and health tracking**: Log foods and portions, review daily and weekly nutrition summaries, and track weight changes.
- **Multi-turn dietary Q&A**: Ask about past meals, nutrition for a specific portion, or how to prepare a dish. Answers draw on MySQL meal records, nutrition data, and a collection of 300 recipes.
- **Exercise plans and check-ins**: Generate a daily exercise plan, confirm it, and mark tasks as complete.

## Project structure

| Path | Contents |
| --- | --- |
| `src/` | Qt/C++ desktop interface |
| `backend/main.py` | FastAPI entry point |
| `backend/ai/` | MiniCPM-V recognition service and model clients |
| `backend/rag/` | Chat query planning, recipe retrieval, and answer generation |
| `backend/services/`, `backend/dao/`, `backend/database/` | Business logic, MySQL data access, and database schema |
| `backend/data/` | Recipe documents and nutrition reference data |
| `backend/scripts/`, `backend/evals/`, `tests/` | Indexing scripts, retrieval evaluation, and automated tests |
| `dataset/`, `build_dataset.py` | Fine-tuning dataset manifests and preparation script |
