# 三段式状态协议规范

本文说明当前 ARPM 主聊天后端采用的三段式输出协议，以及关系状态记忆（Relationship State, RST）的写入规则。

## 1. 输入是什么

每轮生成时，LLM 接收以下输入：

1. 用户设定与角色设定。
2. 当前结构化状态。
   - 当前仅包含关系状态字段。
   - 该字段来自上一轮 `<state_update>` 通过状态机确认后的结果。
   - 它不是 RAG 召回内容，不参与向量检索。
3. RAG 召回内容。
   - 知识库片段。
   - 角色可见历史对话片段。
   - 按时间/轮次从早到晚排列。
4. 当前用户消息。

当前 prompt 顺序为：

```text
【用户设定 / 角色设定】

【当前结构化状态】
关系状态：...

【情境记忆】
RAG 召回内容

【当前用户消息】
用户说：“...”

【状态判定任务】
输出 <state_update>...</state_update>

【分析任务】
输出 <analysis>...</analysis>

【生成任务】
输出 <response>...</response>
```

## 2. 输出字段是什么

模型必须输出三个标签：

```text
<state_update>{...}</state_update>
<analysis>...</analysis>
<response>...</response>
```

### 2.1 `<state_update>`

用途：判断当前用户消息是否包含关系状态变更。

格式：JSON。

字段：

```json
{
  "has_state_change": true,
  "state_type": "relationship",
  "target": "用户与女朋友",
  "event_type": "breakup",
  "new_status": "已分手",
  "temporal_scope": "current",
  "explicitness": "explicit",
  "evidence": "我分手了",
  "confidence": 0.96,
  "update_action": "update"
}
```

字段说明：

| 字段 | 含义 |
|---|---|
| `has_state_change` | 当前消息是否包含状态变化 |
| `state_type` | 当前只使用 `relationship` 或 `none` |
| `target` | 关系对象，例如“用户与女朋友” |
| `event_type` | `breakup`、`reconcile`、`new_relationship`、`married`、`divorced`、`conflict`、`none` |
| `new_status` | 新关系状态，例如“已分手”“复合”“恋爱中” |
| `temporal_scope` | `current`、`past`、`future_intent`、`hypothetical`、`uncertain` |
| `explicitness` | `explicit`、`implicit`、`uncertain` |
| `evidence` | 当前用户消息中的短证据 |
| `confidence` | 0 到 1 的置信度 |
| `update_action` | `update`、`pending_confirm`、`ignore` |

注意：

- `<state_update>` 不包含 `previous_status` 字段。
- `previous_status` 只能由状态机从当前 persistent RST 自动复制，不能由 LLM 填写。
- `conflict` 表示关系压力，不等于关系身份状态变更。
- `event_type = conflict` 默认不得升级 persistent RST，只能使用 `pending_confirm` 或 `ignore`。
- 如果用户明确表达“因为冲突已经分手/离婚”，应将 `event_type` 归类为 `breakup` 或 `divorced`，而不是 `conflict`。

无关系变化时输出：

```json
{
  "has_state_change": false,
  "state_type": "none",
  "target": "",
  "event_type": "none",
  "new_status": "",
  "temporal_scope": "uncertain",
  "explicitness": "uncertain",
  "evidence": "",
  "confidence": 0,
  "update_action": "ignore"
}
```

### 2.2 `<analysis>`

用途：本轮角色行动指导。

要求：

- 一句话。
- 50 字以内。
- 只描述角色自身下一步表达方向、情绪姿态或行动倾向。
- 不涉及用户。
- 不展开推理过程。
- 不进入下一轮 prompt。
- 不进入 RAG。

示例：

```text
<analysis>保持温和克制，先承接情绪再给出简短陪伴。</analysis>
```

### 2.3 `<response>`

用途：最终角色可见回复。

要求：

- 以角色口吻输出。
- 依据 `<analysis>` 和当前用户消息生成。
- 不暴露 `<state_update>` 或 `<analysis>`。
- 写入聊天记录。
- 写入 RAG 向量库，作为后续角色可见记忆。

## 3. 哪些字段进入下一轮 prompt

| 字段 | 是否进入下一轮 prompt | 进入方式 |
|---|---:|---|
| persistent RST | 是 | 固定注入【当前结构化状态】 |
| `<state_update>` 原始 JSON | 否 | 只用于本轮状态机判定和日志 |
| `<analysis>` | 否 | 只服务本轮生成 |
| `<response>` | 可能 | 作为角色可见历史，经 RAG 召回进入 |
| 用户当前消息 | 可能 | 与 response 组成历史对话，经 RAG 召回进入 |
| RAG 召回内容 | 否 | 每轮重新检索，不直接持久注入 |

下一轮固定注入的是状态机确认后的结构化字段，例如：

```text
【当前结构化状态】
关系状态：用户与女朋友 = 已分手
更新时间：第 128 轮，2026-05-30T14:20:00
依据：我分手了
置信度：0.96
注意：这是当前状态；旧历史记忆只能作为过去事实，不得覆盖该状态。
```

## 4. 哪些字段绝不入库

以下内容绝不写入 RAG 向量库：

| 字段 | 是否入 RAG 向量库 | 原因 |
|---|---:|---|
| `<state_update>` | 否 | 这是状态机控制字段，不是角色可见记忆 |
| persistent RST | 否 | 固定结构化注入，不靠召回 |
| `<analysis>` | 否 | 本轮隐式行动指导，不是角色记忆 |
| `state_update_log` | 否 | 调试与审计日志 |
| admin C cot 日志 | 否 | 协议诊断，不应污染角色记忆 |

允许写入 RAG 的只有角色可见内容：

```text
用户输入 + AI 最终 <response>
```

当前实现中，向量化文本仍是：

```text
{user_name}: {user_input}
{character_name}: {response}
```

## 5. 什么条件升级为 persistent RST

`<state_update>` 不会直接成为 persistent RST。它必须通过状态机守卫。

当前升级条件：

```text
has_state_change == true
state_type == "relationship"
update_action == "update"
temporal_scope == "current"
explicitness == "explicit"
event_type != "conflict"
confidence >= 0.85
new_status 非空
```

只有全部满足，才写入：

```json
{
  "structured_state": {
    "relationship": {
      "target": "用户与女朋友",
      "status": "已分手",
      "previous_status": "恋爱中",
      "event_type": "breakup",
      "changed_at_round": 128,
      "changed_at_time": "2026-05-30T14:20:00",
      "evidence": "我分手了",
      "confidence": 0.96,
      "source": "state_update",
      "active": true
    }
  }
}
```

## 6. 不升级的情况

以下情况不会覆盖 persistent RST：

| 用户表达 | 原因 | 推荐动作 |
|---|---|---|
| “我想分手了” | 未来意图，不是已发生事实 | `pending_confirm` |
| “如果我分手了怎么办” | 假设 | `ignore` |
| “之前我分手过” | 过去事件 | `ignore` |
| “我们好像结束了” | 不确定 | `pending_confirm` |
| “我们吵架了” | 关系压力，不是关系身份变更 | `pending_confirm` |
| “我们冷战了” | 短程关系压力，不覆盖长期状态 | `pending_confirm` |
| 旧 RAG 中出现“我和女朋友很甜” | 历史事实，不能覆盖当前状态 | `ignore` |

## 7. 设计原则

1. RST 是当前世界状态，不是普通 episodic memory。
2. RST 只由当前用户消息中的明确状态事件更新。
3. 旧 RAG 只能提供历史背景，不能推翻当前 RST。
4. `<analysis>` 是本轮生成中间变量，不作为记忆。
5. `<response>` 是唯一进入角色可见语义记忆的模型输出。
6. 状态层、分析层、回复层必须保持通道隔离。

## 8. 当前实现位置

| 功能 | 文件 |
|---|---|
| 三段式 prompt 构建 | `backend/core/generator.py` |
| `<state_update>/<analysis>/<response>` 解析 | `backend/utils/text_utils.py` |
| RST 状态机写入 | `backend/api/chat.py` |
| 前端协议诊断显示 | `backend/web/static/js/chat.js` |
