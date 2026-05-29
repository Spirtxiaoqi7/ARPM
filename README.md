# ARPM v4.1 - Analysis-Based Role-Playing with Memory

ARPM v4 是新一代角色一致性对话系统，采用双时态记忆架构和实时原子化存储。

## V4.1 更新

- **三段式生成协议**：新增 `<state_update>`、`<analysis>`、`<response>` 三段式输出。
- **关系状态记忆 RST**：显式关系变更可升级为 persistent Relationship State，下一轮固定注入 prompt，不依赖 RAG 命中。
- **状态/RAG 隔离**：`state_update`、persistent RST、`analysis` 绝不写入向量库；只有用户输入与可见 `<response>` 写入对话记忆。
- **保守状态机守卫**：仅当关系变更为当前、显式、高置信度且非 `conflict` 时升级 persistent RST。
- **角色行动指导**：`analysis` 改为 50 字内行动指导，仅服务本轮回复生成，不进入下一轮 prompt。
- **回复格式规范**：`<response>` 中中文引号“”表示说话内容，圆括号（）表示动作、神态、心理或其他非对白描述。
- **LOCOMO 隔离**：LOCOMO 测评代码与主 ARPM 运行时数据分离，避免基准数据污染主前端知识库。

## 🚀 核心特性

### 双时态记忆系统
- **轮次时态**: 基于对话轮次的指数衰减
- **物理时态**: 基于真实时间的权重计算
- **双索引结构**: 知识库索引 + 对话历史索引分离存储

### 实时原子写入
- 每轮对话立即向量化存储
- 无需等待10K字符阈值
- 对话历史参与RAG检索（Top-10）

### 模糊问题拆解
- LLM自动判断问题清晰度
- 召回不匹配时自动拆解为子问题
- 多路检索结果智能合并

### 双源召回
- **知识库**: 父子块结构，BM25+向量融合，召回5块
- **对话历史**: 原子块结构，纯向量检索，召回10块

## 📁 项目结构

```
ARPM-v4/
├── backend/
│   ├── app.py                 # Flask主入口
│   ├── config.py              # 配置中心
│   ├── requirements.txt       # 依赖列表
│   ├── api/
│   │   ├── chat.py            # 对话接口（含模糊拆解）
│   │   ├── knowledge.py       # 知识库管理
│   │   ├── session.py         # 会话管理
│   │   └── diagnose.py        # 诊断接口
│   ├── core/
│   │   ├── retriever.py       # 双源检索器
│   │   ├── memory_manager.py  # 双时态权重
│   │   ├── generator.py       # 生成器（含规则验证）
│   │   └── diagnostician.py   # 系统诊断
│   ├── storage/
│   │   ├── vector_store.py    # 双索引存储
│   │   ├── memory_store.py    # 会话存储
│   │   └── schema.py          # 数据模型
│   ├── utils/
│   │   ├── chunker.py         # 分块器
│   │   ├── bm25_plus.py       # BM25+实现
│   │   ├── time_utils.py      # 双时态工具
│   │   └── text_utils.py      # 文本工具
│   └── web/
│       ├── static/css/style.css
│       └── templates/index.html
├── scripts/
│   └── migrate_v3_to_v4.py    # v3数据迁移
├── start.bat                    # Windows启动脚本
└── README_V4.md
```

## 🛠️ 快速开始

### 1. 数据迁移（如有v3数据）
```bash
python scripts/migrate_v3_to_v4.py
```

### 2. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 3. 启动服务
```bash
# Windows
start.bat

# 或手动
cd backend
python app.py
```

### 4. 访问
打开浏览器访问: http://localhost:5000

## ⚙️ 配置说明

在设置面板中配置：
- **API密钥**: 支持 DeepSeek/OpenAI 兼容接口
- **系统提示词**: 定义AI角色行为
- **消融测试开关**:
  - ARPM检索总开关
  - BM25+混合检索
  - 模糊问题拆解

## 🗃️ 数据存储

### 双索引结构
```
data/vector_db/
├── knowledge/           # 知识库索引
│   ├── metadata.json    # 父块元数据（含chunk_id, timestamp, children）
│   └── faiss.index      # FAISS向量索引
└── chat/                # 对话历史索引
    ├── metadata.json    # 原子块元数据
    └── faiss.index      # FAISS向量索引

data/memory_db/
└── session_{id}.json    # 会话数据（消息+结构化记忆）
```

### 时间戳格式
```json
{
  "round_num": 5,
  "physical_time": "2026-04-07T22:31:00"
}
```

## 🔍 检索流程

```
用户输入
    ↓
[知识库检索] ──向量+BM25+RRF──→ 5个父块
[对话检索] ──────向量────────→ 10个原子块
    ↓
时态权重计算 (轮次+物理时间+场景)
    ↓
合并15块上下文
    ↓
LLM分析（判断清晰度）
    ↓
模糊? → 拆解子问题 → 重新检索 → 合并
清晰? → 直接生成
    ↓
规则验证 → 保存回复
    ↓
实时原子化写入向量库
```

## 🧪 与v3的主要差异

| 特性 | v3 | v4 |
|------|-----|-----|
| 时间模型 | 单一时态（轮次） | 双时态（轮次+物理） |
| 写入策略 | 10K阈值批量写入 | 实时原子写入 |
| 存储结构 | 单索引 | 双索引（知识+对话分离） |
| 召回来源 | 仅知识库 | 知识库+对话历史 |
| 模糊处理 | 无 | 自动拆解子问题 |
| 手动加权 | 关键词/怀旧/锁定 | **已移除** |
| 场景结构 | 嵌套支持 | 扁平结构 |

## 📝 API 端点

- `POST /api/chat` - 对话（含模糊拆解）
- `POST /api/test` - 测试API连接
- `GET /api/knowledge` - 获取知识库
- `POST /api/knowledge` - 上传文件
- `DELETE /api/knowledge?index=x` - 删除片段
- `GET /api/sessions` - 会话列表
- `GET /api/history/{id}` - 会话历史
- `POST /api/diagnostics` - 系统诊断

## 🐛 故障排除

### FAISS索引损坏
```bash
# 自动修复
POST /api/diagnostics {"auto_fix": true}
```

### 模型加载失败
确保 models/shibing624/text2vec-base-chinese/ 存在

### 数据不兼容
运行迁移脚本：python scripts/migrate_v3_to_v4.py

## 📄 许可证

MIT License

## Docker 部署

本仓库包体不包含虚拟环境、运行时向量库、实验日志和模型本体。容器默认读取：

- 运行数据：`./runtime:/app/runtime`
- 本地模型：`./assets:/app/assets`

启动方式：

```bash
docker compose up --build
```

启动后访问：

```text
http://localhost:5000
```

如需使用本地向量模型，请按文档下载到 `assets/models/`，或通过环境变量 `ARPM_MODEL_ROOT` 指向已有模型父目录。
