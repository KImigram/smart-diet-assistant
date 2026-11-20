# 数据来源

- 项目：Anduin2017/HowToCook
- 仓库：https://github.com/Anduin2017/HowToCook
- 许可证：Unlicense
- 本地用途：营养饮食助手 RAG 菜谱检索实验
- 处理方式：从 dishes 目录筛选菜谱，保留原料、步骤、用量和注意事项，删除图片及无关展示内容。

## 本次扩充快照

- 源仓库版本线索：`package.json` 中 `version` 为 `1.6.0`；本地副本不含 `.git` 目录，无法确定具体 commit。
- 快照整理时间：2026-11-16
- 收录规模：`recipes/` 下共 300 篇菜谱，其中原有 30 篇、本次新增 270 篇。
- 来源字段：每篇菜谱的 `source_path` 记录源仓库 `dishes/` 下的真实相对路径，`source_url` 指向对应 GitHub 文件页面。
- 分类归并：源仓库 `drink` 目录的饮品沿用既有约定归入 `dessert`；`dishes/vegetable_dish/西红柿豆腐汤羹` 按汤羹性质归入 `soup`。
- 说明：本次新增文件保留原文标题与章节结构，介绍、预估难度、预估卡路里等原文内容未专门删除，交由 `backend/rag/document_loader.py` 在加载时统一清洗；本次未新增这类内容。
