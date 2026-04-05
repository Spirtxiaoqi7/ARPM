#!/bin/bash

# ARPM v3.0 启动脚本 (Linux/Mac)

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}  ARPM v3.0 智能对话系统${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 Python3${NC}"
    echo "请先安装 Python 3.10+"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv venv
fi

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source venv/bin/activate

# 检查依赖
if ! python -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}安装依赖...${NC}"
    pip install -r requirements.txt
fi

# 创建数据目录
mkdir -p data/vector_db
mkdir -p data/memory_db
mkdir -p data/feedback
mkdir -p data/archive

echo ""
echo -e "${GREEN}启动服务...${NC}"
echo -e "访问地址: ${YELLOW}http://localhost:5000${NC}"
echo ""

# 启动应用
python app.py

# 退出时停用虚拟环境
deactivate
