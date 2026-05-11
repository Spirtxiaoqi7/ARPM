# ARPM-v4 公式与数值说明

本文档整理 ARPM-v4 当前代码实现中实际采用的核心公式、默认参数与论文撰写口径。依据代码位置包括 `backend/config.py`、`backend/core/retriever.py`、`backend/core/memory_manager.py`、`backend/storage/vector_store.py`、`backend/utils/bm25_plus.py`、`backend/core/generator.py` 与 `backend/core/role_validator.py`。

## 1. 总体检索框架

ARPM-v4 使用双源 RAG 检索：

- 知识库检索：全局共享知识库，使用向量检索 + BM25+，再通过 RRF 融合。
- 对话历史检索：按 `session_id` 隔离，每个会话维护独立向量索引。
- 时间权重重排：召回后再对知识库和对话历史分别施加双时态衰减。
- Prompt 注入：实际注入 prompt 时，知识库块和对话历史块会合并为同一时间线，并按 `round_num` 早到晚、同轮次按 `physical_time` 早到晚排列。

默认召回数量：

| 项目 | 默认值 | 可调范围 |
|---|---:|---:|
| 知识库召回 `knowledge_k` | 5 | 1-20 |
| 对话历史召回 `chat_history_k` | 10 | 1-30 |
| 相似度阈值 `similarity_threshold` | 0.5 | 0-1 |
| RRF 参数 `rrf_k` | 60.0 | 1-200 |

## 2. 向量检索公式

知识库与对话历史均使用 `SentenceTransformer` 编码，模型路径为：

```text
assets/models/shibing624/text2vec-base-chinese
```

FAISS 索引类型为：

```text
faiss.IndexFlatIP
```

即使用内积作为向量检索分数：

```text
score_vector(q, d) = q · d
```

对话历史检索中，系统额外计算归一化余弦相似度：

```text
semantic_score(q, d) = clip(cos(q, d), 0, 1)
```

其中：

```text
cos(q, d) = q_norm · d_norm
```

知识库检索当前主要保留 FAISS 内积分数；对话历史检索会将归一化后的 `semantic_score` 作为后续重排基础分数。

## 3. BM25+ 公式

知识库检索引入 BM25+ 关键词匹配。默认参数：

| 参数 | 默认值 |
|---|---:|
| `k1` | 1.5 |
| `b` | 0.75 |
| `delta` | 0.5 |

IDF 计算：

```text
idf(t) = max(0, log((N - df(t) + 0.5) / (df(t) + 0.5))) + delta
```

单文档 BM25+ 分数：

```text
score_BM25+(q, d) =
Σ_{t in q} idf(t) · [ tf(t,d) · (k1 + 1) /
(tf(t,d) + k1 · (1 - b + b · |d| / avgdl)) ]
```

说明：

- 中文使用 `jieba.cut` 分词。
- 英文使用简化 Porter Stemmer。
- 当前实现虽然命名为 BM25+，但 `delta` 实际加在 IDF 上，而不是经典 BM25+ 中加在 TF 饱和项后的常数项；论文中建议写作“BM25+ 风格关键词评分”或“带正偏置 IDF 的 BM25 变体”，避免与标准 BM25+ 完全等同。

## 4. RRF 融合公式

知识库检索中，向量结果和 BM25 结果使用 Reciprocal Rank Fusion 融合。

默认参数：

```text
rrf_k = 60.0
```

融合公式：

```text
score_RRF(d) = Σ_i 1 / (rrf_k + rank_i(d) + 1)
```

其中 `i` 表示不同检索器，例如向量检索和 BM25 检索；`rank_i(d)` 是文档 `d` 在第 `i` 个检索器中的排名，从 0 开始。

代码中 RRF 后会做最大值归一化：

```text
score_RRF_norm(d) = score_RRF(d) / max(score_RRF)
```

因此 RRF 融合后的知识库分数被压缩到约 0-1 区间，方便与相似度阈值、角色加权等后续步骤对齐。

## 5. 角色感知检索与加权

### 5.1 查询增强

若 `role_query_prefix_enabled = True`，系统会将用户名与角色名拼入查询：

```text
q' = [用户{user_name}][助手{character_name}] q
```

默认：

```text
role_query_prefix_enabled = True
```

### 5.2 知识库角色加权

知识库检索结果在融合后，根据角色相关性加权。

默认数值：

| 条件 | 加分 |
|---|---:|
| 知识块文本包含用户名 | +0.08 |
| 知识块文本包含角色名 | +0.08 |
| 来源文件名包含角色名 | +0.05 |

公式：

```text
score_kb_role(d) = score_base(d) + boost_user + boost_character + boost_source
```

随后进行最大值归一化：

```text
score_kb_final(d) = score_kb_role(d) / max(score_kb_role)
```

### 5.3 对话历史角色加权

对话历史检索结果根据同会话、用户名、角色名加权。

默认数值：

| 条件 | 加分 |
|---|---:|
| 同一会话 `session_id` 匹配 | +0.15 |
| `user_name` 完全匹配 | +0.10 |
| 文本中包含 `user_name` | +0.04 |
| `character_name` 完全匹配 | +0.10 |
| 文本中包含 `character_name` | +0.04 |

公式：

```text
score_chat_role(d) = semantic_score(d) + boost_session + boost_user + boost_character
```

## 6. 双时态遗忘权重

ARPM-v4 的时间权重由两个指数衰减项相乘：

```text
w_round = exp(-|r_current - r_chunk| / lambda_round)
```

```text
w_clock = exp(-Delta_hours / lambda_hours)
```

最终时间权重：

```text
w_temporal = w_round · w_clock
```

召回结果最终加权分数：

```text
score_weighted(d) = score_original(d) · w_temporal
```

默认参数：

| 参数 | 默认值 | 含义 |
|---|---:|---|
| `lambda_round` / `decay_rate_round` | 20.0 | 轮次衰减时间常数 |
| `lambda_hours` / `decay_rate_hours` | 168.0 小时 | 物理时间衰减时间常数 |
| `scene_factor` | 1.0 | 当前实际固定为 1.0 |
| `SCENE_DECAY_FACTOR` | 0.5 | 配置中保留，但当前主流程未启用 |

注意：当 `Delta_hours = 168` 小时时，

```text
w_clock = exp(-1) ≈ 0.3679
```

因此代码里的 168 小时不是“半衰期”，而是指数衰减的时间常数。对应半衰期为：

```text
t_1/2 = lambda_hours · ln(2) = 168 · 0.693 ≈ 116.4 小时 ≈ 4.85 天
```

同理，轮次维度半衰期为：

```text
r_1/2 = lambda_round · ln(2) = 20 · 0.693 ≈ 13.86 轮
```

## 7. 遗忘曲线是否为艾宾浩斯

结论：当前实现不是严格意义上的艾宾浩斯实验曲线，而是“艾宾浩斯遗忘思想的工程化指数衰减近似”。

理由如下：

1. 艾宾浩斯遗忘曲线描述的是人类记忆保持率随时间快速下降后逐渐趋缓的经验规律，常见简化形式可以写作指数衰减：

```text
R(t) = exp(-t / S)
```

2. 本项目物理时间权重确实采用：

```text
w_clock = exp(-Delta_hours / 168)
```

这与简化指数型艾宾浩斯曲线在数学形式上相似。

3. 但本项目还额外引入轮次衰减：

```text
w_round = exp(-Delta_round / 20)
```

并将两者相乘：

```text
w_temporal = exp(-Delta_round / 20) · exp(-Delta_hours / 168)
```

等价于：

```text
w_temporal = exp(-(Delta_round / 20 + Delta_hours / 168))
```

这已经不是单变量时间曲线，而是“轮次时间 + 物理时间”的双时态遗忘模型。

4. 当前参数 `20` 和 `168` 是工程超参数，未从艾宾浩斯原始实验数据或用户记忆保持实验中拟合得到。

论文建议表述：

> 本文采用受艾宾浩斯遗忘曲线启发的双时态指数衰减机制，对召回记忆进行时间重排。该机制同时考虑对话轮次距离与真实物理时间间隔，并以两个指数衰减项的乘积作为记忆保留权重。需要说明的是，该曲线并非对艾宾浩斯原始实验数据的拟合，而是面向对话系统记忆调度的工程化近似。

不建议直接写：

> 本系统使用艾宾浩斯遗忘曲线。

更稳妥写法：

> 本系统使用艾宾浩斯遗忘曲线启发的指数型遗忘函数。

或：

> 本系统采用类艾宾浩斯的双时态指数衰减记忆权重。

## 8. 消融实验开关

默认消融配置：

| 开关 | 默认值 | 说明 |
|---|---:|---|
| `rag_enabled` | True | RAG 总开关 |
| `kb_enabled` | True | 知识库召回 |
| `chat_enabled` | True | 对话历史召回 |
| `temporal_enabled` | True | 双时态遗忘权重 |
| `bm25_enabled` | True | BM25 关键词检索 |
| `disambiguation_enabled` | True in config, 实际聊天路径传 False | 模糊拆解接口保留 |
| `regeneration_enabled` | True | 角色校验后重生成 |
| `regen_regex` | True | 正则校验 |
| `regen_semantic` | False | LLM 语义校验 |
| `regen_consistency` | False | 历史一致性校验 |
| `regen_max_attempts` | 1 | 最多重生成次数 |

主开关逻辑：

```text
if rag_enabled = False:
    kb_enabled = False
    chat_enabled = False
    temporal_enabled = False
    bm25_enabled = False
```

即 RAG 总开关关闭时，相关子模块自动失效。

## 9. 生成模型参数

默认 LLM 配置：

| 参数 | 默认值 | 可调范围 |
|---|---:|---:|
| `model` | deepseek-chat | 前端/API 可传入 |
| `base_url` | https://api.deepseek.com | 前端/API 可传入 |
| `temperature` | 0.7 | 0-2 |
| `max_tokens` | 2000 | 64-8192 |
| `timeout` | 120 秒 | 固定配置 |

连接测试接口中使用：

| 参数 | 值 |
|---|---:|
| `max_tokens` | 2 |
| `temperature` | 0 |
| `timeout` | 15 秒 |

## 10. 角色校验与重生成参数

重生成控制默认值：

| 参数 | 默认值 |
|---|---:|
| `enabled` | True |
| `max_attempts` | 1 |
| `regex_enabled` | True |
| `semantic_enabled` | False |
| `consistency_enabled` | False |
| `strategy` | append_warning |
| `semantic_threshold` | 0.7 |
| `consistency_threshold` | 0.3 |

一致性校验当前使用 `SequenceMatcher` 计算回复与最近历史回复的平均相似度：

```text
avg_similarity = mean(SequenceMatcher(response, previous_response_i).ratio())
```

触发风格突变的代码条件：

```text
avg_similarity < 0.1 and len(response) > 50
```

需要注意：虽然配置中存在 `CONSISTENCY_THRESHOLD = 0.3`，但当前实际触发条件写死为 `0.1`。

语义校验如果开启，使用 LLM 进行 JSON 判定：

| 参数 | 值 |
|---|---:|
| `temperature` | 0.1 |
| `max_tokens` | 500 |
| `timeout` | 30 秒 |

## 11. 分块参数

默认知识分块参数：

| 参数 | 默认值 | 可调范围 |
|---|---:|---:|
| `child_size` | 200 | 50-1000 |
| `parent_size` | 600 | 100-3000 |
| `overlap_sentences` | 1 | 0-10 |

知识库写入时，会生成父块与子块；向量索引按子块写入，召回时映射回父块。

## 12. Prompt 注入顺序与日志

当前实现中，召回内容注入 prompt 前会合并：

- 知识库召回块 `knowledge`
- 对话历史召回块 `chat_history`

然后排序：

```text
sort_key = (round_num, physical_time)
```

即轮次早的在上，轮次晚的在下；同轮次按物理时间早到晚排列。每个注入块都会包含：

```text
source_type
source
round_num
physical_time
formatted_time
```

此外系统会在 prompt 最后追加当前用户输入作为最终锚点，避免模型最后读到的是规则文本而不是最新输入。

实验日志目录：

```text
runtime/arpm-app/admin/
```

日志文件：

| 文件 | 内容 |
|---|---|
| `A_recall.log` | 实际注入 prompt 的召回内容 |
| `B_dialog.log` | 用户输入与 AI 回复，包含模型型号 |
| `C_cot.log` | analysis / regeneration / protocol 信息，包含模型型号 |

## 13. 论文方法段可用表述

可以写作：

> ARPM-v4 采用双源检索增强生成框架，同时从全局知识库与会话级对话历史中召回候选记忆。知识库检索融合向量相似度与 BM25 关键词匹配，并通过 Reciprocal Rank Fusion 进行排序融合；对话历史检索基于会话隔离向量索引，并使用归一化余弦相似度作为语义匹配分数。召回结果进一步经过角色感知加权与双时态遗忘权重重排。双时态遗忘权重由对话轮次距离和真实物理时间间隔两个指数衰减项构成，形式为 `w = exp(-Δround/20) · exp(-Δhours/168)`。该机制可视为受艾宾浩斯遗忘规律启发的工程化指数衰减近似，而非对艾宾浩斯原始实验曲线的严格拟合。

## 14. 写作注意事项

建议避免以下表述：

- “严格复现艾宾浩斯遗忘曲线”
- “168 小时为半衰期”
- “场景衰减已经生效”
- “标准 BM25+ 完全实现”

建议采用以下表述：

- “类艾宾浩斯指数衰减”
- “168 小时为物理时间衰减常数”
- “场景衰减接口保留，当前主流程固定为 1.0”
- “BM25+ 风格关键词评分”

