# ARPM-v4 重生成机制与工程改进方案

## 一、当前重生成机制分析

### 1.1 触发机制现状

```python
# backend/core/generator.py

# 规则验证
is_valid, violation = self.validator.validate_response(reply)
if not is_valid:
    # 触发重生成（最多一次）
    safe_prompt = prompt + f"\n注意：你之前的回复违反了规则：{violation}，请修正。"
    response = self._call_llm(safe_prompt, api_config)
    if response:
        analysis, reply, _ = self.parser.parse_analysis_response(response)
```

**当前触发条件：**
- 仅基于正则匹配的硬规则（4条禁止模式）
- 违反时触发一次重生成
- 重生成时只在prompt追加警告信息

**当前问题：**
1. 规则过于简单（只有4条硬编码正则）
2. 没有LLM语义层验证
3. 没有历史一致性检查
4. 重生成次数限制为1次，无法保证质量
5. 没有用户反馈触发的重生成
6. 没有开关控制

---

## 二、主要工程缺失清单

### 2.1 核心功能缺失

| 序号 | 缺失项 | 严重程度 | 说明 |
|------|--------|----------|------|
| 1 | 角色规则配置文件 | 🔴高 | 硬编码规则无法适应不同角色 |
| 2 | LLM语义验证层 | 🔴高 | 正则无法捕捉语义层面的角色偏差 |
| 3 | 历史一致性检查 | 🟡中 | 无法检测与之前回复的矛盾 |
| 4 | 用户反馈重生成 | 🟡中 | 点赞/点踩无法触发模型优化 |
| 5 | 重生成开关控制 | 🟡中 | 用户无法关闭自动重生成 |
| 6 | 重生成次数配置 | 🟢低 | 固定1次，无法调整 |

### 2.2 工程化缺失

| 序号 | 缺失项 | 严重程度 | 说明 |
|------|--------|----------|------|
| 7 | 单元测试套件 | 🔴高 | `tests/`目录为空 |
| 8 | 结构化日志系统 | 🟡中 | 使用print，无日志文件 |
| 9 | API文档 | 🟡中 | 无OpenAPI/Swagger文档 |
| 10 | 配置文件系统 | 🟢低 | 只有环境变量，无YAML配置 |
| 11 | 性能监控 | 🟢低 | 无响应时间/召回率统计 |
| 12 | Docker部署 | 🟢低 | 无容器化配置 |

### 2.3 前端缺失

| 序号 | 缺失项 | 严重程度 | 说明 |
|------|--------|----------|------|
| 13 | 重生成状态显示 | 🟡中 | 用户不知道发生了重生成 |
| 14 | 规则违反提示 | 🟡中 | 用户看不到触发了什么规则 |
| 15 | 手动重生成按钮 | 🟡中 | 用户无法主动要求重生成 |

---

## 三、改进方案优先级排列

### 方案A：最小可行改进（1-2天）

**目标：** 修复最严重问题，不改动架构

**实现清单：**
1. ✅ 重生成开关（添加到消融实验面板）
2. ✅ 规则配置文件（JSON/YAML格式）
3. ✅ 重生成状态返回（前端显示）

**代码改动量：** ~200行

---

### 方案B：增强验证层（3-5天）

**目标：** 实现三层验证框架

**实现清单：**
1. 重生成开关
2. 角色规则配置文件
3. **LLM语义验证层**（新模块）
4. **简单的历史一致性检查**（向量相似度）
5. 重生成次数配置
6. 规则违反详细日志

**代码改动量：** ~800行

**新增模块：**
```
backend/core/
├── role_validator.py       # 增强版验证框架
│   ├── RegexValidator      # 正则层（当前）
│   ├── SemanticValidator   # LLM语义层（新增）
│   └── ConsistencyValidator # 历史一致性（新增）
```

---

### 方案C：完整反馈闭环（5-7天）

**目标：** 构建完整的角色一致性保障体系

**实现清单：**
1. 方案B全部内容
2. **用户反馈重生成**（点赞/点踩触发）
3. **偏好学习基础**（收集反馈数据）
4. 前端手动重生成按钮
5. 规则违反可视化提示
6. 基础测试套件（pytest）
7. 结构化日志（logging模块）

**代码改动量：** ~1500行

---

### 方案D：生产级工程化（7-10天）

**目标：** 达到可部署的生产级标准

**实现清单：**
1. 方案C全部内容
2. 完整测试套件（单元+集成）
3. API文档自动生成
4. 性能监控面板
5. Docker配置
6. 配置文件系统
7. 数据迁移脚本完善

**代码改动量：** ~2500行

---

## 四、推荐的实现顺序

```
Phase 1: 立即修复（方案A）
├── 1. 重生成开关
├── 2. 规则配置文件
└── 3. 状态显示

Phase 2: 核心增强（方案B的关键部分）
├── 4. LLM语义验证层
└── 5. 历史一致性基础检查

Phase 3: 体验完善（方案C的关键部分）
├── 6. 用户反馈重生成
└── 7. 前端手动重生成

Phase 4: 工程化（方案D）
└── 8. 测试+文档+部署
```

---

## 五、具体实现设计

### 5.1 重生成开关设计

```python
# config.py
class AblationConfig:
    # ... 现有开关 ...
    
    # 重生成控制
    REGENERATION_ENABLED = True           # 总开关
    REGENERATION_MAX_ATTEMPTS = 1         # 最大次数
    REGENERATION_REGEX_ENABLED = True     # 正则验证层
    REGENERATION_SEMANTIC_ENABLED = False # LLM语义验证层
    REGENERATION_CONSISTENCY_ENABLED = False # 一致性验证层
```

```javascript
// 前端UI - 新增在消融实验面板下方
<div class="config-section">
    <h3>🔄 重生成控制</h3>
    <div class="ablation-item">
        <input type="checkbox" id="cfg-regen-enabled">
        <label>启用自动重生成</label>
    </div>
    <div class="form-item">
        <label>最大重试次数</label>
        <input type="number" id="cfg-regen-max" value="1" min="0" max="3">
    </div>
    <div class="ablation-item">
        <input type="checkbox" id="cfg-regen-regex">
        <label>正则规则验证</label>
    </div>
    <div class="ablation-item">
        <input type="checkbox" id="cfg-regen-semantic">
        <label>LLM语义验证</label>
    </div>
</div>
```

### 5.2 角色规则配置设计

```yaml
# config/character_default.yaml
character:
  name: "默认助手"
  
  # 身份约束（禁止自我篡改）
  identity_constraints:
    forbidden_patterns:
      - "我是.*的父亲"
      - "我的背景故事是"
      - "实际上我不是"
    required_pronouns: ["我", "本人"]  # 必须用第一人称
    
  # 知识边界
  knowledge_boundary:
    knows: ["已知领域1", "已知领域2"]
    doesnt_know: ["未知领域1"]
    default_response: "这个问题我不太清楚..."
    
  # 性格特征（用于LLM语义验证）
  personality_traits:
    - "温柔体贴"
    - "知识渊博"
    - "幽默风趣"
    
  # 说话风格（用于一致性检查）
  speech_patterns:
    sentence_length: "medium"  # short/medium/long
    emoji_usage: "occasional"  # never/occasional/frequent
    formality: "casual"        # formal/neutral/casual
    
  # 历史一致性规则
  consistency_rules:
    check_previous_facts: true
    max_contradiction_score: 0.3
    
  # 安全规则
  safety_rules:
    forbidden_topics: ["暴力", "色情", "政治"]
    response_for_violation: "这个问题不太合适呢..."
```

### 5.3 增强验证框架设计

```python
# backend/core/role_validator.py

from enum import Enum
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

class ViolationType(Enum):
    REGEX = "regex"           # 正则违反
    SEMANTIC = "semantic"     # 语义违反
    CONSISTENCY = "consistency"  # 一致性违反
    SAFETY = "safety"         # 安全违反

@dataclass
class ValidationResult:
    is_valid: bool
    violation_type: Optional[ViolationType]
    message: str
    suggestion: str  # 给LLM的修正建议
    confidence: float  # 置信度

class RoleValidator:
    """三层验证框架"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.regex_validator = RegexValidator(self.config)
        self.semantic_validator = SemanticValidator(self.config)
        self.consistency_validator = ConsistencyValidator(self.config)
    
    def validate(
        self,
        response: str,
        character_config: dict,
        history: List[dict] = None,
        enabled_layers: List[str] = None
    ) -> ValidationResult:
        """
        执行启用的验证层
        
        Args:
            response: AI回复
            character_config: 角色配置
            history: 历史对话（用于一致性检查）
            enabled_layers: 启用的验证层 ["regex", "semantic", "consistency"]
        """
        enabled = enabled_layers or ["regex"]
        
        # L1: 正则验证（快速）
        if "regex" in enabled:
            result = self.regex_validator.validate(response)
            if not result.is_valid:
                return result
        
        # L2: LLM语义验证
        if "semantic" in enabled:
            result = self.semantic_validator.validate(response, character_config)
            if not result.is_valid:
                return result
        
        # L3: 历史一致性验证
        if "consistency" in enabled and history:
            result = self.consistency_validator.validate(response, history)
            if not result.is_valid:
                return result
        
        return ValidationResult(True, None, "", "", 1.0)
```

---

## 六、实现建议

### 6.1 立即可做（今天）

**重生成开关（30分钟）：**
1. 在 `config.py` 添加 `REGENERATION_ENABLED`
2. 在 `generator.py` 检查开关
3. 前端添加checkbox
4. 测试开关生效

### 6.2 本周完成

**规则配置文件 + 状态显示（2-3小时）：**
1. 创建 `config/characters/` 目录
2. 实现 YAML 加载器
3. 修改前端显示重生成状态
4. 返回规则违反信息给前端

### 6.3 下周完成

**LLM语义验证层（1-2天）：**
1. 设计语义验证prompt
2. 实现 `SemanticValidator`
3. 添加到生成流程
4. 测试不同角色的验证效果

---

## 七、技术决策点

### Q1: 语义验证用同一个LLM还是单独模型？
**建议：** 同一个，减少延迟和成本

### Q2: 历史一致性检查怎么做？
**建议：** 
- V1: 简单关键词匹配（快速）
- V2: 向量相似度计算（精准）
- V3: 专用contradiction detection模型（生产级）

### Q3: 用户反馈如何影响重生成？
**建议：**
- 点踩 → 立即触发重生成（用户选择原因）
- 点赞 → 记录到偏好数据库（用于未来微调）

---

**请确认要实施的方案级别，我立即开始编码！**