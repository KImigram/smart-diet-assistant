# Smart Diet

面向个人饮食管理的桌面端 AI 项目。当前重构重点是：

1. 保留 MiniCPM-V 微调菜品识别与基座模型二次校验流程；
2. 重写可解释、可评测的营养知识 RAG；
3. 复用原 Qt 界面和基础业务功能，减少与项目重点无关的重复开发。

## 当前状态

- 已初始化独立 Git 仓库；
- 已迁移 Qt 源码、基础后端、数据库脚本和视觉识别服务；
- 已移除源码中的明文密钥和密码；
- 已完成数据库连接释放、密码存储、Qt SSE 生命周期等必要修复；
- 旧 RAG/LLM 文件仅作接口兼容，下一阶段将重写。

## 目录

```text
smart_diet/
├─ src/                         # Qt/C++ 桌面端源码
├─ backend/
│  ├─ ai/                      # MiniCPM 双模型识别及现有 AI 客户端
│  ├─ dao/                     # 数据访问层
│  ├─ database/                # MySQL 连接与初始化脚本
│  ├─ models/                  # API 数据结构
│  ├─ services/                # 业务服务（旧 RAG 待替换）
│  ├─ rag/                     # 新 RAG 模块（待实现）
│  ├─ evals/                   # RAG 评测集与评测脚本（待实现）
│  ├─ scripts/                 # 数据/索引构建脚本
│  └─ data/
│     ├─ knowledge_source/     # 原始知识文档
│     └─ vector_db/            # 本地生成的向量索引，不提交 Git
├─ dataset/                    # MiniCPM 微调数据清单
├─ tests/                      # 自动化测试（待补充）
├─ build_dataset.py            # 微调数据集构建脚本
├─ test_api.py                 # 双模型识别流程原始验证脚本
├─ test_recognition.py         # 视觉识别测试脚本
└─ .env.example                # 本地配置模板，不含真实凭据
```

## 安全说明

复制 `.env.example` 为 `.env` 后再填写本机数据库密码和云端 API Key。
`.env`、模型权重、运行日志、Qt 构建产物和向量索引均已被 Git 忽略。

