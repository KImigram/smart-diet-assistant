# 智能饮食助手

[简体中文](README.md) · [English](README.en.md)

Qt 桌面应用，支持饮食营养记录、拍照识别菜品、体重跟踪和运动计划。

- `src/`：Qt/C++ 界面。
- `backend/`：FastAPI 接口、MySQL 数据访问和 MiniCPM-V 识别服务。
- `dataset/`：视觉微调数据清单，图片路径相对于 ChineseFoodNet 的 val 目录。
- `tests/`：测试。

[feat/rag 分支](https://github.com/KImigram/smart-diet-assistant/tree/feat/rag)包含新版菜谱检索、多轮问答与评测。
