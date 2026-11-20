# Smart Diet

面向个人饮食管理的桌面端 AI 项目。当前重构重点是：

1. 保留 MiniCPM-V 微调菜品识别与基座模型二次校验流程；
2. 重写可解释、可评测的营养知识 RAG；
3. 复用原 Qt 界面和基础业务功能，减少与项目重点无关的重复开发。

## 功能

- Qt 桌面端支持饮食记录、营养追踪和拍照识别。
- MiniCPM-V 微调模型提供候选菜名，基座模型核验并补充食材。
- 聊天先生成结构化查询计划，再查询 MySQL、计算份量营养并按需检索菜谱，最后根据证据生成回答。
- 菜谱知识库包含 300 篇菜谱，支持 BGE-M3 向量检索和可选的 BM25 混合检索。检索评测说明见 [评测文档](backend/evals/README.md)。

## 目录

```text
smart_diet/
├─ src/                         # Qt/C++ 桌面端源码
├─ backend/
│  ├─ ai/                      # MiniCPM 双模型识别及现有 AI 客户端
│  ├─ dao/                     # 数据访问层
│  ├─ database/                # MySQL 连接与初始化脚本
│  ├─ models/                  # API 数据结构
│  ├─ services/                # 业务服务
│  ├─ rag/                     # 检索与对话流程
│  ├─ evals/                   # RAG 评测集与评测脚本
│  ├─ scripts/                 # 数据/索引构建脚本
│  └─ data/
│     ├─ knowledge_source/     # 原始知识文档
│     └─ vector_db/            # 本地生成的向量索引，不提交 Git
├─ dataset/                    # MiniCPM 微调数据清单
├─ tests/                      # 自动化测试
├─ build_dataset.py            # 微调数据集构建脚本
├─ test_api.py                 # 双模型识别流程原始验证脚本
├─ test_recognition.py         # 视觉识别测试脚本
└─ .env.example                # 本地配置模板，不含真实凭据
```

## 安全说明

复制 `.env.example` 为 `.env` 后再填写本机数据库密码和云端 API Key。
`.env`、模型权重、运行日志、Qt 构建产物和向量索引均已被 Git 忽略。


训练清单中的图片路径相对于 ChineseFoodNet 的 val 目录。图片与权重需要本地准备。可设置 CHINESEFOODNET_VAL_DIR 后运行 build_dataset.py 重新生成清单。
