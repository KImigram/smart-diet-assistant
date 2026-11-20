# 智能饮食助手

[简体中文](README.md) · [English](README.en.md)

一个用 Qt 和 FastAPI 构建的桌面应用，支持记录饮食、查看营养摄入和查询做法。

## 项目功能

- **拍照识别菜品**：微调后的 MiniCPM-V 提供候选，基座模型核验结果，用户可以确认或纠正菜名。
- **饮食和健康记录**：记录食物和份量，查看每日及每周营养统计，跟踪体重变化。
- **多轮饮食问答**：结合 MySQL 饮食记录、食物营养数据和 300 篇菜谱，回答历史摄入、指定份量营养和菜品做法等问题。
- **运动计划与打卡**：生成每日运动计划，确认后记录任务完成情况。

## 项目结构

| 路径 | 内容 |
| --- | --- |
| `src/` | Qt/C++ 桌面界面 |
| `backend/main.py` | FastAPI 接口入口 |
| `backend/ai/` | MiniCPM-V 识别服务与模型客户端 |
| `backend/rag/` | 对话查询计划、菜谱检索和回答生成 |
| `backend/services/`、`backend/dao/`、`backend/database/` | 业务逻辑、MySQL 数据访问和建表脚本 |
| `backend/data/` | 菜谱原文和营养参考数据 |
| `backend/scripts/`、`backend/evals/`、`tests/` | 建库脚本、检索评测和自动化测试 |
| `dataset/`、`build_dataset.py` | 视觉微调数据清单与生成脚本 |
