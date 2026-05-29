# LOCOMO 会话与 QA 说明

这个文件解释两个问题：

1. 每个 LOCOMO 会话到底是什么，需要体现哪些信息。
2. QA 问题放在哪里，为什么你在普通聊天界面里没直接看到 QA。

---

## 1. LOCOMO 里每个会话是什么

当前导入后，ARPM 里有 10 个 LOCOMO 会话：

```text
locomo_conv-26
locomo_conv-30
locomo_conv-41
locomo_conv-42
locomo_conv-43
locomo_conv-44
locomo_conv-47
locomo_conv-48
locomo_conv-49
locomo_conv-50
```

这些名字来自 LOCOMO 官方数据里的 `sample_id`：

```text
conv-26 -> locomo_conv-26
conv-30 -> locomo_conv-30
```

也就是说：

```text
一个 locomo_conv-xx = 一个 LOCOMO 官方长对话样本
```

它不是普通聊天里临时创建的一轮对话，而是 LOCOMO benchmark 的一个完整测试样本。

---

## 2. 每个会话需要体现什么

每个 LOCOMO 会话至少要体现这些信息：

```text
1. 会话 ID
2. 官方 sample_id
3. 对话双方是谁
4. 这个样本有多少个 session
5. 这个样本有多少条 dialogue turn
6. 这个样本有多少条 QA 问题
7. 每条 turn 的 dia_id
8. 每条 turn 的 speaker
9. 每条 turn 的原始文本
10. 每条 turn 所属的 session_num
11. 每条 turn 的物理时间 physical_time
12. 每条 turn 的全局 round_num
```

这些信息现在已经写入两个位置：

### 2.1 会话 JSON

位置：

```text
E:\flai\ARPM-v4备份\runtime\arpm-app\data\memory_db
```

例如：

```text
session_locomo_conv-26.json
session_locomo_conv-30.json
```

里面保存：

```text
session_id
session_name
messages
locomo_sample_id
locomo_speaker_a
locomo_speaker_b
locomo_qa
```

### 2.2 向量索引 metadata

位置：

```text
E:\flai\ARPM-v4备份\runtime\arpm-app\data\vector_db\chat
```

例如：

```text
locomo_conv-26\metadata.json
locomo_conv-30\metadata.json
```

里面每一条就是一个 LOCOMO dialogue turn。

每条大概长这样：

```json
{
  "chunk_id": "conv-26_D1_3",
  "text": "[LOCOMO sample=conv-26 session=1 time=1:56 pm on 8 May, 2023 round=3 speaker=Caroline dia_id=D1:3]\nCaroline: I went to a LGBTQ support group yesterday and it was so powerful.",
  "session_id": "locomo_conv-26",
  "timestamp": {
    "round_num": 3,
    "physical_time": "2023-05-08T13:56:00"
  },
  "benchmark": "locomo",
  "sample_id": "conv-26",
  "session_num": 1,
  "session_time_raw": "1:56 pm on 8 May, 2023",
  "speaker": "Caroline",
  "dia_id": "D1:3",
  "text_raw": "I went to a LGBTQ support group yesterday and it was so powerful."
}
```

---

## 3. 每个会话的数量区别

当前 10 个 LOCOMO 会话的规模如下：

```text
locomo_conv-26: 419 条 turn，199 条 QA
locomo_conv-30: 369 条 turn，105 条 QA
locomo_conv-41: 663 条 turn，193 条 QA
locomo_conv-42: 629 条 turn，260 条 QA
locomo_conv-43: 680 条 turn，242 条 QA
locomo_conv-44: 675 条 turn，158 条 QA
locomo_conv-47: 689 条 turn，190 条 QA
locomo_conv-48: 681 条 turn，239 条 QA
locomo_conv-49: 509 条 turn，196 条 QA
locomo_conv-50: 568 条 turn，204 条 QA
```

总计：

```text
5882 条 dialogue turn
1986 条 QA
```

---

## 4. QA 放在哪里了

QA 没有作为普通聊天消息显示在前端里。

原因是：

```text
QA 是 benchmark 测试题，不是原始对话内容。
```

如果把 QA 混进聊天记录，会污染检索记忆。

所以当前 QA 单独放在这里：

```text
E:\flai\ARPM-v4备份\code\arpm-app\LOCOMO\data\locomo_qa.jsonl
```

这个文件是一行一个问题。

例如：

```json
{
  "qa_id": "locomo_conv-26_q000",
  "sample_id": "conv-26",
  "session_id": "locomo_conv-26",
  "question": "When did Caroline go to the LGBTQ support group?",
  "gold_answer": "7 May 2023",
  "category": 2,
  "gold_evidence": ["D1:3"]
}
```

字段说明：

```text
qa_id：这条 QA 的编号
sample_id：官方 LOCOMO 样本编号
session_id：对应 ARPM 里的 LOCOMO 会话
question：英文问题
gold_answer：官方标准答案
category：官方问题类别
gold_evidence：官方证据 dia_id
```

---

## 5. 为什么普通聊天界面看不到 QA

普通聊天界面现在主要展示：

```text
会话消息
聊天记忆
知识库块
召回内容
```

但 LOCOMO QA 是测试集问题，不属于原始对话。

如果把 QA 也导入到聊天记忆里，会出现严重问题：

```text
模型可能直接从问题或答案里检索到答案
这会导致 benchmark 泄漏
实验结果不可信
```

因此当前设计是：

```text
LOCOMO 原始对话 -> 导入 ARPM chat memory
LOCOMO QA 问题 -> 单独保存在 LOCOMO\data\locomo_qa.jsonl
评测脚本读取 QA -> 检索对应会话 -> 调用模型回答
```

---

## 6. 评测结果放在哪里

检索评测结果放在：

```text
E:\flai\ARPM-v4备份\code\arpm-app\LOCOMO\results
```

常见文件：

```text
retrieval_chat_vector.jsonl
retrieval_chat_vector.summary.json
retrieval_chat_vector.zh.csv
```

其中：

```text
retrieval_chat_vector.jsonl
```

是每一道题的机器结果。

```text
retrieval_chat_vector.summary.json
```

是总分。

```text
retrieval_chat_vector.zh.csv
```

是给人看的中文表格，可以用 Excel 打开。

---

## 7. QA 到底怎么参与测试

测试流程是：

```text
读取 locomo_qa.jsonl 里的一个问题
找到它对应的 session_id
只在这个 session_id 的聊天记忆里检索
得到若干召回 turn
把召回 turn 的 dia_id 和官方 gold_evidence 对比
如果命中，说明检索找到了正确证据
如果需要生成答案，再把召回 turn 注入 prompt
调用模型生成答案
把模型答案和 gold_answer 对比
```

举例：

```text
问题：When did Caroline go to the LGBTQ support group?
对应会话：locomo_conv-26
官方证据：D1:3
```

脚本会做：

```text
只搜索 locomo_conv-26 的 419 条 turn
看召回列表里有没有 D1:3
```

不会去其他会话里搜。

---

## 8. 如果你想快速查看 QA

可以直接打开：

```text
E:\flai\ARPM-v4备份\code\arpm-app\LOCOMO\data\locomo_qa.jsonl
```

如果觉得 JSONL 不好看，可以先跑检索测试并生成中文 CSV：

```powershell
cd E:\flai\ARPM-v4备份\code\arpm-app
E:\flai\ARPM-v4备份\env\arpm-venv\Scripts\python.exe LOCOMO\run_retrieval_eval.py --method chat_vector --k 20 --limit 20
E:\flai\ARPM-v4备份\env\arpm-venv\Scripts\python.exe LOCOMO\make_zh_report.py --input LOCOMO\results\retrieval_chat_vector.jsonl
```

然后打开：

```text
E:\flai\ARPM-v4备份\code\arpm-app\LOCOMO\results\retrieval_chat_vector.zh.csv
```

---

## 9. 为什么会话命名看起来很统一

统一命名是为了防止评测错乱。

规则是：

```text
locomo_ + 官方 sample_id
```

例如：

```text
conv-26 -> locomo_conv-26
conv-50 -> locomo_conv-50
```

这样 QA 文件里的 `session_id` 可以直接对应到 ARPM 的会话索引。

统一命名不代表内容一样。

每个会话的说话人、时间线、turn 数、QA 数、证据 dia_id 都不同。

