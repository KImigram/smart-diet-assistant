# 扩库后的检索测评 v3

## 题库与划分

`rag_questions_v3.jsonl` 共 200 题，前 90 条与 v2 完全一致，新增 110 条。旧题作为 regression（回归题），新增题标为 new（新增题）。

| 范围 | 开发集 dev | 保留测试集 test | 总数 |
|---|---:|---:|---:|
| 原题 | 46 | 44 | 90 |
| 新题 | 57 | 53 | 110 |
| 合计 | 103 | 97 | 200 |
| 可回答题 | 89 | 81 | 170 |
| 无答案题 | 14 | 16 | 30 |

有证据标注的菜谱从原来的 30 篇扩到 60 篇，涉及全部七个目录。检索语料仍使用全部 300 篇、1342 个块，因此其他菜谱也会作为候选干扰。当前并未逐篇覆盖全部 300 篇。

新增 30 篇覆盖黄油虾的两种配方、水煮蛋的不同做法、南派与徽派红烧肉、烤鸡翅与红烧鸡翅、两种蒸米饭设备和两种鸡蛋羹设备等。每篇设置一个单轮事实题、一个依赖历史的追问，以及一个相似菜区分、话题切换或用户纠正题。

相近菜对及其在历史、干扰语句中的来源以 `related_sources` 记录。加载器同时检查证据来源和这些关联来源，避免同一文档被用在开发集与保留测试集两侧。旧题的原划分保持原样。

## 场景

| 类别 | 总题数 | 检查内容 |
|---|---:|---|
| quantity（用量） | 31 | 配方数量与份数 |
| ingredient（食材） | 22 | 真实原料 |
| procedure（步骤） | 13 | 操作顺序 |
| paraphrase（语义改写） | 6 | 非原文措辞 |
| hard_detail（细节） | 18 | 温度、时间和设备条件 |
| followup（追问） | 20 | 结合历史补全当前问题 |
| ellipsis（省略） | 10 | 当前问题省略菜名 |
| long_history_followup（长历史追问） | 10 | 8 条历史里切换过话题，定位最近有效对象 |
| similar_disambiguation（相似菜区分） | 10 | 当前明确指定目标配方，排除相近名称 |
| history_correction（历史纠正） | 10 | 用户纠正之前的菜名后，追问应跟随新对象 |
| topic_switch（话题切换） | 15 | 当前新对象覆盖旧话题 |
| multi_evidence（多证据） | 5 | 两个事实来源的覆盖 |
| unanswerable（无答案） | 30 | 当前菜谱证据不足 |

多轮题携带预先编写的 user/assistant 历史。运行 rewrite 适配器时，模型能读到这些历史。它们评测问题改写及随后的检索，尚未评测客户端连续生成答案、将生成答案回填历史的完整对话过程。

新增 20 道无答案题按六类记录 `negative_kind`，包括未收录菜谱、缺少精确营养数据、需要个人数据库、领域外问题、缺少医疗依据、缺少指定细节。原 10 道无答案题保留原始标注，报告中归入 legacy_unspecified（旧题未细分）。

个人数据库题的“无答案”仅限菜谱检索范围。混合检索有相关结果时，生成模型仍可能正确说明资料不足，因此检索拒绝率不能代表最终拒答准确率。

## 标注与验证

每道可回答题用真实来源、章节与原文引用定位证据。原文在多个章节重复同一事实时，可用 alternatives（等价证据）表达一个事实的多个有效位置。需要多个事实的题以多个 evidence（证据）项表达。

题目是依据原文编写的固定案例，尚未经过独立人工复核。自动检查可验证原文引用存在、来源隔离与字段格式，不能证明所有语义标注都完美。发现标注问题应修订题库版本并记录原因，不能为了改善某种检索器的分数扩大相关性标注。

本轮通过全部 200 题原文证据校验，以及 35 项无真实模型测试。未运行新题库的真实模型测评，未计算保留测试集成绩。

## 使用

在项目根目录激活 rag 环境。仅校验题库与当前语料，不加载模型。

```powershell
python backend/evals/evaluate_retrieval.py --suite expanded --validate-only
```

原题回归入口与之前 46 道开发题一致。下列正式测评命令会加载本地 BGE-M3，rewrite 适配器还可能调用已配置云端改写模型，需要用户授权后执行。

```powershell
python backend/evals/evaluate_retrieval.py --suite regression --split dev --adapter evals.adapters:create_rewrite_dense
```

扩展题库开发集为 103 题。比较两种检索时共用一次实验的改写缓存，避免云端改写变化影响结论。

```powershell
$runDir = "backend/evals/outputs/expanded_$(Get-Date -Format yyyyMMdd_HHmmss)"
$options = @{rewrite_cache="$runDir/queries.json"} | ConvertTo-Json -Compress
python backend/evals/evaluate_retrieval.py --suite expanded --split dev --adapter evals.adapters:create_rewrite_dense --options $options --output "$runDir/dense"
python backend/evals/evaluate_retrieval.py --suite expanded --split dev --adapter evals.adapters:create_rewrite_hybrid --options $options --output "$runDir/hybrid"
python backend/evals/compare_runs.py "$runDir/dense/report.json" "$runDir/hybrid/report.json"
```

共享缓存只包含问题与历史对应的改写，不包含答案。每轮新实验使用新目录。出现改写回退时，应先查看原因，再解释两组差异。

只检查新题中的多轮类问题时，可以筛选。

```powershell
python backend/evals/evaluate_retrieval.py --suite expanded --split dev --cohort new --category followup ellipsis long_history_followup history_correction --adapter evals.adapters:create_rewrite_dense
```

默认 `--suite expanded --split dev --cohort all`。`--questions` 与 `--suite` 互斥，前者允许传入历史或自定义题库。`--validate-only` 会校验所选题库的全部标注，不计算得分，也不会调用模型。

`summary.md` 现在分别列出旧题/新题、各问题类别、各无答案场景的成绩。`report.json` 保留逐题结果及 `by_cohort`、`by_category`、`by_negative_kind`。

参数固定后，可将 `--split dev` 改为 `--split test` 进行正式保留测试。`--split all` 仅用于全题诊断，混合得分不应被称为保留测试成绩。

## 三个概念

回归测试用于检查改动是否破坏之前已具备的能力。在本项目中，原 90 道题作为稳定的比较入口，开发阶段可反复运行其中 46 道旧开发题。另 44 道旧题仍遵守保留测试约定。

开发集用于反复分析错误并调整 K、距离阈值、改写提示词及融合参数。本版本有 103 道。由于这些题已经参与决策，它们的成绩应报告为开发集效果。

保留测试集用于方案固定后的验收。本版本有 97 道，日常调参阶段不运行成绩。若反复根据它的失败案例修改方案，它也会逐渐成为开发数据，需要另备独立验收题。

回归描述用途，开发/测试描述使用阶段。回归题也可以属于开发集或保留测试集，两种划分可以同时存在。

