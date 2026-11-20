# Smart Diet Assistant

[简体中文](README.md) · [English](README.en.md)

A Qt desktop app for logging meals and nutrition, recognizing dishes from photos, tracking weight, and planning exercise.

- `src/`: Qt/C++ desktop interface.
- `backend/`: FastAPI endpoints, MySQL access, and MiniCPM-V dish recognition.
- `dataset/`: Fine-tuning manifests with paths relative to the ChineseFoodNet val directory.
- `tests/`: Tests.

The [feat/rag branch](https://github.com/KImigram/smart-diet-assistant/tree/feat/rag) contains the newer recipe retrieval, multi-turn Q&A, and evaluation code.
