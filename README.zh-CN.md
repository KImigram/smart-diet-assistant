# 智能饮食助手

[English](README.md) · 简体中文

智能饮食助手是一款 Windows 桌面应用，支持拍照识别中式菜品、记录饮食和体重，以及查询营养和菜谱。Qt 客户端通过 FastAPI 后端访问 MySQL 业务数据和菜谱知识库。

## 项目功能

- **账号与健康档案** — 注册和登录，管理体重、活动水平、目标热量及过敏原等信息。
- **拍照识别菜品** — 选择或拖入图片，查看菜名和主要食材，确认或纠正后再登记。历史纠错结果可在后续识别中作为备选。
- **饮食记录与统计** — 手动选择食物或使用识别结果，按餐次和份量登记，查看每日、每周的热量、蛋白质、脂肪、碳水、膳食纤维和钠汇总，也可以跟踪体重变化。
- **多轮营养与菜谱问答** — 查询自身饮食记录、计算指定份量的营养，或者询问食材和做法。一句话可以同时查两种数据，例如「我昨天午饭记了多少大卡？清蒸鲈鱼要蒸多久？」客户端支持流式显示和会话历史。
- **运动计划与打卡** — 根据当天已记录的摄入、用户目标和运动偏好生成计划，确认后逐项打卡并查看完成情况。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 桌面端 | Qt 6 Widgets、C++17、Qt Network、qmake |
| 后端与数据库 | Python、FastAPI、Uvicorn、MySQL 8、MySQL Connector/Python |
| 视觉识别 | MiniCPM-V 4.6、LoRA、ChineseFoodNet、LLaMA-Factory、PyTorch、Hugging Face Transformers |
| 菜谱检索 | LangChain、Sentence Transformers、本地 BGE-M3、Chroma，可选 jieba 分词和 BM25 |
| 对话 | OpenAI 兼容云端接口，默认配置为 DeepSeek，通过 SSE（服务端发送事件）流式返回 |

## 核心流程

### 菜品识别与二次核验

从 ChineseFoodNet 的 **208 类中式菜品**按类别抽样，生成 ShareGPT 格式的训练与验证清单，通过 LLaMA-Factory 对 MiniCPM-V 4.6 进行 LoRA 微调。

推理时由微调模型提出菜名，基座模型结合图片进行二次核验。核验未通过时由基座模型重新识别，主要食材描述也由基座模型提供。后端将结果与食物库匹配。食物库缺少相应菜品时，可请求模型估算营养值，结果供参考。

### 菜谱 RAG 与数据库联动

1. **生成查询计划。** 云端大模型结合近期对话消解指代，将问题拆成饮食记录、指定份量营养和菜谱等子查询。Python 校验计划，校验失败时按原问题走规则处理。
2. **按计划查数据。** MySQL 的 **13 张表**保存食物营养及来源、饮食记录、档案和对话等数据。Python 执行参数化 SQL，并将常见重量单位换算为克，再计算营养。菜谱库从 HowToCook 整理出 **300 篇菜谱**，按 Markdown 章节切分为 **1,342 个文本块**，保留菜名、章节和来源。
3. **排序并生成答复。** 默认使用 BGE-M3 稠密向量检索，也可单独用 BM25 关键词检索。混合模式用 RRF（倒数排名融合）合并两路排名。最终选中的前 K 个文本块与数据库查询结果一起交给模型，回答可分别用 `[R1]`、`[D1]` 等编号引用菜谱和营养证据。

### 评测

- [菜谱检索评测](backend/evals/README.md) 包含 **200 道题**，划分开发集和保留测试集，支持在同一批问题上比较向量、BM25 和混合检索的证据命中、多事实覆盖和无答案场景表现。
- [数据库联动与口语专项](backend/evals/DATABASE_RAG.md) 核对日期、餐次、份量计算、菜谱引用和口语追问。在各自的同一批开发题上，原有联动题完整通过数由 **4/9 提升至 9/9**，口语查询规划由 **10/12 提升至 12/12**。

## 本地运行

先启动本地 MySQL，在仓库根目录使用已准备好的 Python 环境安装后端依赖。当前后端在 Python 3.12 下验证过。

```powershell
python -m pip install -r backend/requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

在 `.env` 中填写 MySQL 连接信息，然后初始化数据库。

```powershell
Push-Location backend
python init_db.py
Pop-Location
```

对话还需要在 `.env` 中配置 `LLM_API_KEY`、`LLM_BASE_URL` 和 `LLM_MODEL`。使用向量或混合检索时，将 `RAG_EMBEDDING_MODEL_PATH` 指向本地 BGE-M3 权重，再在新建或空目录中构建 Chroma 索引。如果已有兼容索引，将 `RAG_INDEX_PATH` 指向该索引即可跳过建库。单独使用 BM25 时可以直接读取项目中的 Markdown 菜谱。

```powershell
python backend/scripts/build_rag_index.py
python backend/main.py
```

用 Qt Creator 打开 [src/nutritious-diet.pro](src/nutritious-diet.pro)，选择 Qt 6 桌面构建套件后编译运行。客户端默认连接 `http://127.0.0.1:8001`，可访问后端的 `/api/health` 检查状态。

使用拍照识别功能时，先启动经微调的 MiniCPM-V 模型 API（默认端口 `8000`），再在支持 GPU 的 Python 环境中运行 `python backend/ai/finetune_server.py`。可通过识别进程的环境变量 `MINICPM_BASE_MODEL_PATH` 和 `MINICPM_FINETUNED_API_URL` 配置基座模型权重和微调模型接口。主后端通过 `FINETUNE_API_URL` 调用识别服务，默认端口为 `8002`。模型权重及生成的向量索引在本地保存。

## 项目结构

```text
smart-diet-assistant/
├── src/                    # Qt/C++ 页面、控件与 HTTP 客户端
├── backend/
│   ├── main.py             # FastAPI 入口
│   ├── ai/                 # 视觉服务与云端模型客户端
│   ├── rag/                # 查询规划、菜谱检索与回答生成
│   ├── services/           # 饮食、营养、识别与运动业务逻辑
│   ├── dao/                # MySQL 数据访问
│   ├── database/           # 数据库建表与初始数据
│   ├── data/               # 菜谱和营养参考数据
│   ├── scripts/            # 建库和数据准备脚本
│   └── evals/              # 检索、联动与口语查询规划评测
├── dataset/                # 视觉微调数据清单
├── build_dataset.py        # ChineseFoodNet 数据整理脚本
└── tests/                  # 自动化测试
```

菜谱来源与许可证见 [HowToCook 数据来源说明](backend/data/knowledge_source/howtocook/SOURCE.md)。
