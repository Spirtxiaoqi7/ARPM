# VectHare 功能集成说明

ARPM 现已集成 VectHare 的三项核心增强功能：

## 1. BM25+ 增强检索

### 功能特性
- **Porter Stemmer**: 英文词干提取（如 running → run, adventurers → adventurer）
- **停用词过滤**: 中英文停用词自动过滤（190+ 英文词 + 中文常用词）
- **字段加权**: 标题和标签 4x 加权，内容 1x
- **覆盖率奖励**: 所有查询词都匹配时 +10% 得分
- **BM25+ 公式**: delta 平滑防止负 IDF

### 代码实现
```python
# modules/bm25_plus.py
from modules.bm25_plus import BM25PlusScorer

# 创建评分器
scorer = BM25PlusScorer(
    k1=1.5,          # 词频饱和度
    b=0.75,          # 长度归一化
    delta=0.5,       # IDF 平滑参数
    field_boosting=True,    # 启用字段加权
    coverage_bonus=True,    # 启用覆盖率奖励
    use_stemmer=True,       # 启用词干提取
    remove_stopwords=True   # 启用停用词过滤
)

# 索引文档
documents = [
    {'text': '文档内容', 'title': '标题', 'tags': ['标签1', '标签2']},
    ...
]
scorer.index_documents(documents)

# 搜索
results = scorer.search("查询词", top_k=10)
```

---

## 2. 时间盲标记 (Temporally Blind)

### 功能说明
标记重要的知识块，使其不受 ARPM 时间衰减影响。被标记的 chunk 始终获得 `PERMANENT_WEIGHT` (默认 1.0) 的权重。

### API 接口

#### 设置时间盲标记
```http
POST /api/knowledge/{chunk_idx}/blind
Content-Type: application/json

{
    "blind": true
}
```

#### 取消时间盲标记
```http
DELETE /api/knowledge/{chunk_idx}/blind
```

### 前端集成示例
```javascript
// 标记为时间盲
fetch(`/api/knowledge/${chunkIndex}/blind`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({blind: true})
});

// 取消标记
fetch(`/api/knowledge/${chunkIndex}/blind`, {
    method: 'DELETE'
});
```

### 使用场景
- 角色定义（永远不会忘记角色是谁）
- 世界观设定（重要背景信息）
- 关键剧情节点（必须记住的事件）

---

## 3. 条件激活系统

### 功能说明
为知识块设置激活条件，只有满足条件时才会被检索。

### 支持的规则类型

| 类型 | 说明 | 参数 |
|------|------|------|
| `keyword` | 关键词匹配 | `keywords`, `match_mode` (any/all), `case_sensitive` |
| `regex` | 正则表达式匹配 | `patterns`, `match_mode` |
| `round_range` | 轮次范围 | `min_round`, `max_round` |
| `recency` | 最近性检查 | `max_messages_ago` |
| `random` | 随机概率 | `probability` (0-100) |

### 逻辑组合
- `AND`: 所有规则必须满足
- `OR`: 任一规则满足即可
- `negate`: 规则取反

### API 接口

#### 获取条件
```http
GET /api/knowledge/{chunk_idx}/conditions
```

#### 设置条件
```http
POST /api/knowledge/{chunk_idx}/conditions
Content-Type: application/json

{
    "conditions": {
        "enabled": true,
        "logic": "AND",
        "rules": [
            {
                "type": "keyword",
                "settings": {
                    "keywords": ["重要", "关键"],
                    "match_mode": "any",
                    "case_sensitive": false
                },
                "negate": false
            },
            {
                "type": "regex",
                "settings": {
                    "patterns": ["\\d{4}-\\d{2}-\\d{2}"],
                    "match_mode": "any"
                }
            },
            {
                "type": "round_range",
                "settings": {
                    "min_round": 1,
                    "max_round": 10
                }
            }
        ]
    }
}
```

#### 清除条件
```http
DELETE /api/knowledge/{chunk_idx}/conditions
```

### 使用场景
- **情感条件**: 只在特定情绪下激活相关记忆
- **时间条件**: 只在特定轮次范围内激活
- **关键词触发**: 特定话题出现时激活相关背景

---

## 配置文件更新

### 新增环境变量
```bash
# RRF 融合常数（默认 60）
RRF_K=60

# 其他原有配置
DECAY_RATE=20.0
PERMANENT_WEIGHT=1.0
```

---

## 数据结构变更

### 元数据格式
```json
{
    "timestamp": 1,
    "source": "upload",
    "permanent": false,
    "temporally_blind": false,  // 新增：时间盲标记
    "conditions": {              // 新增：条件激活规则
        "enabled": true,
        "logic": "AND",
        "rules": [...]
    },
    "title": "文档标题",         // 新增：用于 BM25+ 字段加权
    "tags": ["标签1", "标签2"]    // 新增：用于 BM25+ 字段加权
}
```

---

## 迁移说明

### 兼容性
- 旧数据无需修改，自动兼容
- `temporally_blind` 默认为 `false`
- `conditions` 默认为空（无条件，始终激活）

### 性能影响
- BM25+ 的词干提取使用 LRU 缓存，性能开销极小
- 条件激活只在检索时计算，对索引无影响

---

## 前端 UI 建议

### 1. 时间盲标记按钮
```html
<button onclick="toggleBlind(${chunkIndex})" class="${chunk.temporally_blind ? 'active' : ''}">
    ${chunk.temporally_blind ? '🔒 已锁定' : '🔓 点击锁定'}
</button>
```

### 2. 条件规则编辑器
```html
<div class="condition-editor">
    <select id="logic">
        <option value="AND">满足所有条件</option>
        <option value="OR">满足任一条件</option>
    </select>
    <div id="rules">
        <!-- 动态添加规则 -->
    </div>
    <button onclick="addRule()">+ 添加规则</button>
</div>
```

### 3. 检索结果显示
```html
<div class="search-result">
    <div class="score">相似度: ${result.score}</div>
    <div class="meta">
        ${result.temporally_blind ? '🔒 已锁定' : ''}
        ${result.conditions?.enabled ? '📋 有条件' : ''}
    </div>
</div>
```
