# ARPM v3.0 - Analysis-Based Role-Playing with Memory

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-3.0-green.svg)](https://github.com/yourusername/ARPM)

基于**自适应检索增强与认知记忆建模**的角色一致性对话系统，支持长期人设保持与RAG增强生成。

## ✨ 核心特性

### 🧠 认知记忆架构
- **ARPM轮次协议**: 第一轮静默分析 → 第二轮起全量输出，确保对话连贯性
- **时间感知记忆**: 支持记忆衰减与怀旧增强双模式
- **场景感知记忆**: 剧情段落整体管理，跨场景智能衰减
- **实时归档**: 超长上下文自动切分归档，保留语义连贯

### 🔍 增强检索 (RAG)
- **BM25+混合检索**: Porter词干提取 + 字段加权 + 覆盖率奖励
- **向量语义检索**: 基于text2vec的中文语义编码
- **RRF融合**: 向量+关键词双重检索智能融合
- **关键词提升**: 动态权重调整与防滥用机制

### 🔬 消融测试支持
- **ARPM总开关**: 一键切换纯LLM对话与增强模式
- **组件级控制**: BM25+、CoT重排序、时间衰减、关键词提升独立开关
- **偏好学习**: 点赞/差评反馈收集，支持回复重新生成
- **内容安全**: 举报机制与不合规内容归档

### 🛡️ 生产级功能
- **系统诊断**: 8项健康检查与自动修复
- **知识库管理**: 支持4537+片段的高效管理
- **聊天记录管理**: 单条删除、整会话清空、二次确认
- **多会话隔离**: 严格会话边界，防止消息混淆

## 🚀 快速开始

### 环境要求
- Python 3.10+
- 8GB+ RAM (推荐16GB)
- 支持CPU运行 (无需GPU)

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/ARPM.git
cd ARPM

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 下载模型 (首次运行自动下载)
# 或手动放置到 models/shibing624/text2vec-base-chinese/
```

### 启动服务

```bash
# Windows 双击启动
start.bat

# 或命令行
python app.py
```

访问 http://localhost:5000

### 首次配置

1. 点击右上角"设置"
2. 配置API密钥 (支持DeepSeek/OpenAI等)
3. 可选：上传知识库文档 (.txt/.md/.json)
4. 开始对话

## 📖 使用指南

### 基础对话流程

```
第1轮: 用户输入 → 系统检索 → 存储分析 → 提示"首轮分析完成"
第2轮+: 用户输入 → 检索增强 → 结合历史 → 输出完整回复
```

### 知识库管理

**上传文档**:
- 设置面板 → 选择文件 → 自动分块入库
- 支持分页管理 (20/50/100/200条/页)
- RAG语义检索功能

**片段标记**:
- 🔒 时间锁定: 免疫时间衰减
- 📜 怀旧模式: 越久越重要
- 📋 条件激活: 规则触发检索
- 🔑 关键词提升: 动态加权
- 🎬 场景记忆: 剧情段落管理

### 消融测试

设置面板 → 🔬 消融测试:

| 开关 | 功能 | 建议用途 |
|------|------|----------|
| ARPM总开关 | 启用/禁用整个RAG系统 | 对比纯LLM效果 |
| BM25+检索 | 关键词检索融合 | 测试语义vs关键词 |
| CoT重排序 | 思维链分析 | 测试推理对排序影响 |
| 时间衰减 | 记忆权重时间计算 | 测试长期记忆效果 |
| 关键词提升 | 动态权重调整 | 测试关键词干预效果 |

### 消息反馈

每条AI回复支持:
- 👍 **点赞**: 记录偏好，用于学习
- 👎 **差评**: 记录不喜欢的风格
- 🚫 **举报**: 内容不合规时重新生成并归档

### 聊天记录管理

- **单条删除**: 鼠标悬停消息 → 点击🗑️
- **清空记录**: 底部"🗑️ 清空记录" → 二次确认
- **自动归档**: 超过10K字符自动归档到知识库

## 🏗️ 项目结构

```
ARPM/
├── app.py                  # Flask主应用
├── start.bat              # Windows启动脚本
├── requirements.txt       # Python依赖
├── README.md             # 项目说明
├── LICENSE               # MIT许可证
│
├── core/                 # 核心引擎
│   ├── memory_async.py   # 异步记忆管理
│   └── ...
│
├── modules/              # 功能模块
│   ├── retriever.py      # RAG检索引擎
│   ├── llm_client.py     # LLM客户端
│   ├── bm25_plus.py      # BM25+实现
│   ├── chunker.py        # 文本分块
│   └── diagnostics.py    # 系统诊断
│
├── static/               # 前端资源
│   ├── css/style.css
│   └── js/
│       ├── chat.js       # 主逻辑
│       ├── kb-manager.js # 知识库管理
│       └── ...
│
├── templates/            # HTML模板
│   └── index.html
│
├── data/                 # 数据存储 (运行时创建)
│   ├── vector_db/        # 向量数据库
│   ├── memory_db/        # 会话历史
│   ├── feedback/         # 用户反馈日志
│   └── archive/          # 不合规内容归档
│
└── models/               # 模型文件
    └── shibing624/
        └── text2vec-base-chinese/  # 语义编码模型
```

## ⚙️ 配置说明

### 环境变量 (.env)

```env
PORT=5000
DEBUG=True
CHUNK_SIZE=600
CHUNK_OVERLAP=100
DECAY_RATE=20.0
PERMANENT_WEIGHT=1.0
RETRIEVAL_K=5
RRF_K=60.0
```

### 界面配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| API密钥 | LLM服务API Key | - |
| 接口地址 | API基础URL | https://api.deepseek.com |
| 模型名称 | 使用的模型 | deepseek-chat |
| 分块大小 | 文档切分长度 | 600 |
| 检索数量 | Top-K检索 | 5 |
| 衰减率 | 时间权重衰减 | 20 |

## 🔧 故障排查

### 常见问题

**Q: 模型加载失败**
```bash
模型网盘（国内）：https://pan.quark.cn/s/899cdf543685
# 手动下载模型
pip install modelscope
python -c "from modelscope import snapshot_download; snapshot_download('shibing624/text2vec-base-chinese', cache_dir='models')"
```

**Q: FAISS安装失败**
```bash
# 使用conda安装 (推荐)
conda install -c pytorch faiss-cpu

# 或使用pip
pip install faiss-cpu --no-cache-dir
```

**Q: NumPy版本冲突**
```bash
# 降级到兼容版本
pip install numpy==1.26.2
```

**Q: API连接失败**
- 检查密钥格式是否正确 (sk-...)
- 检查接口地址是否包含https://
- 检查网络连接

**Q: 内存不足**
- 减少CHUNK_SIZE (默认600 → 400)
- 减少RETRIEVAL_K (默认5 → 3)
- 关闭其他占用内存的程序

## 📚 技术文档

- [系统功能说明](docs/ARPM系统功能说明.txt)
- [技术总结](docs/技术引入总结.md)
- [更新日志](docs/CHANGELOG.md)

## 🤝 贡献指南

欢迎提交Issue和PR！

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证


**注意**: 本项目仅供学习和研究使用，请遵守相关API服务条款。
