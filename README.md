# ARPM 智能对话系统[V2.0]

基于异步轮次管理与检索增强生成技术的对话系统。

## 特性

- **ARPM 轮次管理**：第一轮静默分析存储记忆，第二轮起全量输出
- **混合检索**：BM25 + 向量检索 + RRF 融合
- **异步记忆**：非阻塞式记忆持久化(memory）
- **全前端配置**：API、模型参数通过界面设置

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动服务

**Windows**：双击 `start.bat`

**命令行**：
```bash
venv\Scripts\activate
python app.py
```

访问 http://localhost:5000

### 3. 配置使用

1. 点击右上角"设置"
2. 配置 API 密钥和接口地址
3. 可选：上传知识库文档
4. 开始对话

## 项目结构

```
ARPM/
├── app.py              # 主应用
├── start.bat           # 启动脚本
├── core/               # 核心引擎
├── modules/            # 功能模块
├── static/             # 前端资源
├── templates/          # HTML 模板
└── data/               # 数据存储
```

## 使用流程

1. **第 1 轮**：输入问题，系统检索并存储分析结果
2. **第 2+ 轮**：结合历史记忆输出完整回复

## 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| API 密钥 | LLM 服务密钥 | - |
| 接口地址 | API 基础 URL | https://api.deepseek.com |
| 模型名称 | 使用的模型 | deepseek-chat |
| 分块大小 | 文档切分长度 | 600 |
| 检索数量 | Top-K 检索 | 5 |
| 衰减率 | 时间权重衰减 | 20 |

## 常见问题

**模型加载失败**：确保模型文件在 `models/shibing624/text2vec-base-chinese/`

**API 连接失败**：检查密钥和接口地址格式

**依赖安装失败**：
```bash
pip install --upgrade pip
pip install faiss-cpu
```

## 许可

MIT
