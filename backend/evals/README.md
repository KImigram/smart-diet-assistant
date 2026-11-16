# 固定菜谱检索测评 v1

更新：默认题库现为 `rag_questions_v2.jsonl`，只修正开发集等价证据，详见 [ANNOTATION_V2.md](ANNOTATION_V2.md)。原 `rag_questions.jsonl` 保留，复现旧标注可用 `--questions` 指定。

目标：为当前 BGE-M3 稠密检索建立可复用基线，未来在同一题库和语料上比较 BM25、混合检索、重排序和问题改写。
本系统只评价菜谱检索，不调用云端模型、不评价最终回答质量，也不修改现有索引。

## 题库与标注

`rag_questions.jsonl` 共 90 题：60 道单轮菜谱题、10 道多轮指代追问、5 道双证据题、5 道话题切换题和 10 道无答案题。
覆盖全部 30 篇菜谱，涉及食材、用量、步骤、语义改写、相似菜干扰与具体细节。
问题人工编写，证据来自本项目清洗后的菜谱；程序只检查证据存在，不代表人工语义标注永远正确。运行前可人工复核一次，冻结后不要为改善分数修改题目或答案。

每题包含：固定 id、dev/test（开发/保留测试）划分、category（类别）、question（问题）、history（对话历史）、answerable（菜谱库是否可回答）、evidence（来源、章节、原文证据）。
跟进问题另有 oracle_question（人工完整问题），仅用于参考上限。
有多个 evidence 条目时，表示回答需要覆盖多份证据；每份证据可匹配一个或多个文本块。

dev/test 按菜谱分组，同一道菜的基础问题、追问和双证据题不会跨两个划分。
这是为避免同菜改写题在调参与验收时互相泄漏，不是要求测试菜谱不进入知识库。
dev 用于调整 K、阈值和检索策略；保留 test 到最终比较时再跑。由于题库文件可见，这是人为约定，不是技术隔离。

“无答案”限定为当前菜谱语料无法提供完整证据：包括未收录菜、清洗掉的营养精确值、需用户数据库的信息、无关问题和缺少医学依据的问题。
这些题并不表示整个聊天系统不能通过其他途径回答；例如用户昨日摄入应查 MySQL。不要把此处空结果要求推广到全部聊天功能。
社区菜谱事实不等于医学或食品安全权威结论，评测题只检测检索原文的能力。

## 指标

- document_hit@K（菜谱命中）：前 K 块至少一块来自标准菜谱，属于较宽松指标。
- evidence_hit@K（证据命中）：至少命中一块标注证据。
- evidence_recall@K（标注证据块召回率）：命中的标准相关块数 / 标准相关块总数。
- evidence_precision@K（标注证据块精确率）：相关块数 / K，返回不足 K 条时分母仍取 K，避免少返回结果使指标虚高。
- MRR@K（平均倒数排名）：第一条相关块排名的倒数，前 K 无命中记 0。
- nDCG@K（归一化折损累计增益）：本版本使用二元相关性，衡量相关结果是否靠前。
- evidence_group_coverage@K（证据组覆盖率）：双证据题应覆盖两个事实来源；找到同一事实的重复块不能代替另一事实。
- negative_rejection_rate（无答案题检索拒绝率）：无答案题经适配器过滤后没有结果的比例，不等于模型最终拒答准确率。
- positive_empty_rate（可回答题空结果率）：有答案题被过滤到没有结果的比例。
- 冷启动时间、第一题时间、其余成功查询的 P50/P95（延迟分位数）。固定执行顺序，只跑一遍时不能当成稳定性能测量。

相关性定义是“来源+章节+原文证据匹配”，不是完整人工穷举的语义相关性。因此召回率和精确率应报告为标注证据指标，不能直接宣称全知识库真实召回率。
每份报告同时保存过滤前 raw_metrics（原始排序指标）与过滤后 accepted_metrics（接纳结果指标），避免阈值过滤掩盖召回质量。
错误题仍进入总体分母、记录错误；无答案题出错不会被记为成功拒绝。所有错误都需要先排查。

## 运行

在项目根目录、激活 rag 环境后执行：

```powershell
conda activate rag
cd "D:\my program\Python work\smart_diet"
python backend/evals/evaluate_retrieval.py --validate-only
```

以上只验证题库与当前分块，不加载模型。

以下命令会加载本地 BGE-M3。需用户确认运行；不会下载模型或调用云端 API。

```powershell
python backend/evals/evaluate_retrieval.py --split dev --ks 1 3 5 --output backend/evals/outputs/dense_dev_raw
```

默认直接用追问检索，与当前聊天检索行为一致；适配器不会读 evidence 标准答案。
比较人工补全追问的参考上限：

```powershell
python backend/evals/evaluate_retrieval.py --split dev --mode oracle --output backend/evals/outputs/dense_dev_oracle
python backend/evals/compare_runs.py backend/evals/outputs/dense_dev_raw/report.json backend/evals/outputs/dense_dev_oracle/report.json --allow-mode-change
```

oracle 分数不能称为实际自动问题改写的效果。未来真正的问题改写适配器应使用 raw 模式，自己读取 history 并生成查询。

测试距离阈值（0.5 只是命令示例，不是推荐阈值）：

```powershell
python backend/evals/evaluate_retrieval.py --split dev --max-distance 0.5 --output backend/evals/outputs/dense_dev_threshold
```

评测配置不会自动读取聊天的 RAG_MAX_DISTANCE，必须显式用命令参数配置，避免不同终端隐藏配置使实验不可复现。

正式保留测试：选定配置后使用 `--split test`。`--split all` 仅作全题诊断，不用来边调参边声称保留测试成绩。

## 报告与对比

每次写入新的输出目录，拒绝覆盖旧报告。`outputs` 已被项目 .gitignore 忽略。
`summary.md` 是摘要；`report.json` 保存逐题问题、实际查询、排名正文、分数、接纳情况、证据、指标、异常和耗时。
报告还包含题库摘要、分块语料摘要、代码摘要、Git 版本、包版本、索引与适配器配置。

```powershell
python backend/evals/compare_runs.py 旧报告/report.json 新报告/report.json
```

默认拒绝比较不同题库、不同分块语料、不同题号集合、不同 K 或模式的报告。
比较分块策略时应单独标记实验版本，重新校验证据；本版严格对比器不会把不同分块的块级指标直接混比。

## 将来增加模块

新增适配器工厂并通过 `--adapter package.module:factory --options '{...}'` 选择。
工厂接收 options 字典，返回带 `retrieve(question, history, k)` 方法的对象。
方法返回按最终排名排序的字典列表：chunk_id、source（必须为 local_path）、content、score、accepted（布尔值）。
必须使用当前分块的真实 ID 和正文；程序会拒绝语料之外或修改后的文本。
可通过对象的 info 字典记录候选池大小、融合参数、重排模型版本、查询改写配置等。
score 只作诊断：BM25 分数、余弦距离、重排分数不能使用同一阈值；各适配器自行决定 accepted。
最终返回 K 条与第一阶段召回候选池数量应分开配置，后者记录在 options 中。
这样 BM25、混合检索、重排序和问题改写只需要替换适配器，题库、标注和计分保持不变。

## 当前尚未完成

没有正式基线得分；尚未加载真实模型运行本题库。
没有云端生成答案评测、引用支持度判定、自动 LLM 裁判或生产流量统计。
下一步先确认运行 dev 基线，检查失败案例，再决定是否加入新检索模块。
