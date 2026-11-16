# BM25 与混合检索：实现和开发集对照

## 实现

- `rag/hybrid_retriever.py`：jieba 0.42.1 中文分词，统一小写、去除标点，语料和问题使用相同分词函数，HMM=False。不按测试题定制词典。
- BM25Okapi 使用 rank-bm25 0.2.2，k1=1.5、b=0.75、epsilon=0.25。处理现有文本块，不总结原文、不生成向量、不训练模型。
- 混合检索：BGE-M3 和 BM25 各取前 20 块，用 RRF（倒数排名融合）等权合并，公式为各路 `1/(60+排名)` 之和，按 chunk_id 去重后取最终 K。
- 混合检索的 BM25 从 Chroma 保存的正文构建，确保两路语料完全一致。单独 BM25 从现有加载与分块函数构建，不加载 BGE-M3。
- BM25 过滤无正分匹配的块；RRF/BM25 分数越大越靠前，不能使用余弦距离阈值。
- BM25 索引在进程中首次使用时构建并缓存。当前只有 140 块；语料变化后重启服务，向量索引仍需按原流程重建。

## 公平比较方式

2026-11-16，同一 v2 题库、同一 140 块语料、46 道开发题（41 道可回答、5 道无答案），K=1/3/5，不设距离阈值。

三个方案均启用现有多轮改写。第一组调用云端完成 8 道有历史题的改写，另外两组复用同一个查询缓存。逐题确认 46 个实际检索问题完全一致，三个方案错误数均为 0，改写回退均为 0。

缓存只保存问题、历史、模型名称对应的改写结果，不包含标准答案。每个独立实验使用新缓存，避免后续改写提示词或模型配置变化时复用旧结果。缓存和完整报告均在 Git 忽略的 outputs 目录。

BM25 与混合组的缓存命中不包含真实云端改写耗时，不能将三组总耗时直接解释为生产端到端延迟差异。

## 实测结果

| 指标 | 向量 + 改写 | BM25 + 改写 | 混合 + 改写 |
|---|---|---|---|
| Top-1 证据命中 | 35/41，85.37% | 28/41，68.29% | 36/41，87.80% |
| Top-3 证据命中 | 41/41，100% | 41/41，100% | 40/41，97.56% |
| Top-5 证据命中 | 41/41，100% | 41/41，100% | 41/41，100% |
| MRR@3（平均倒数排名） | 0.9268 | 0.8293 | 0.9268 |
| 标注证据块召回率@3 | 96.79% | 92.44% | 93.86% |
| 无答案题检索拒绝率 | 0/5 | 0/5 | 0/5 |

混合方案 Top-1 多命中 1 题，但 Top-3 少命中 1 题，不能宣称全面提升。当前保留 dense 为聊天默认模式，混合方案作为可切换实验。

具体变化：

- q003 清蒸鲈鱼葱姜调味料：正确原料块由第二升到第一。
- q061/q86 清蒸鲈鱼蒸制追问：正确操作块由第二升到第一。
- q81 双菜蒸制时间：含有一份正确证据的块升到第一，但这不表示第一条覆盖两道菜。
- q045 水煮牛肉腌制、q047/q88 糖醋里脊复炸：正确操作块由第一降到第二。
- q033 清蒸鲈鱼大火蒸制时间：正确操作块由第二降到第四，导致混合方案 Top-3 漏检。前面仍是同一道菜的原料、附加内容、计算块；菜名匹配不能代替具体证据匹配。

5 道无答案题都仍返回了结果：关键词相关不代表资料包含答案，融合本身不能完成拒答判断。

这些分数仅代表当前小规模开发集的标注证据检索能力，不是最终回答准确率。未修改题库标注、未调 RRF 权重或候选数量以追求本次分数，也未运行 44 道保留测试题。

报告目录：`outputs/bm25_comparison_v1/{dense,bm25,hybrid}/`。

## 聊天切换

项目 `.env` 支持以下配置；更改后重启后端，不需要重新编译 Qt。

```dotenv
RAG_RETRIEVAL_MODE=hybrid
RAG_CANDIDATE_K=20
RAG_RRF_CONSTANT=60
RAG_MAX_DISTANCE=
```

`dense` 使用原向量检索；`bm25` 单独使用关键词检索；`hybrid` 合并两路。未设置模式时默认 dense。本次没有修改本地 `.env`。

## 复现命令

在项目根目录、rag 环境执行。会加载已有 BGE-M3，第一组的有历史题会调用已配置云端改写接口，不生成最终聊天回答。

```powershell
$runDir = "backend/evals/outputs/bm25_$(Get-Date -Format yyyyMMdd_HHmmss)"
$options = @{rewrite_cache="$runDir/queries.json"} | ConvertTo-Json -Compress
python backend/evals/evaluate_retrieval.py --split dev --adapter evals.adapters:create_rewrite_dense --options $options --output "$runDir/dense"
python backend/evals/evaluate_retrieval.py --split dev --adapter evals.adapters:create_rewrite_bm25 --options $options --output "$runDir/bm25"
python backend/evals/evaluate_retrieval.py --split dev --adapter evals.adapters:create_rewrite_hybrid --options $options --output "$runDir/hybrid"
python backend/evals/compare_runs.py "$runDir/dense/report.json" "$runDir/hybrid/report.json"
```

不启用多轮改写时，适配器分别为 `create_dense`、`create_bm25`、`create_hybrid`，无需提供改写缓存；不要将有无改写的变化归因为 BM25。
