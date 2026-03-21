@echo off
chcp 65001 >nul
set "PROJECT_DIR=C:\Users\Administrator\Desktop\AIProject\RAG-based Character-Consistent Response\DeepseekRAG\1.DeepseekV3"

echo 正在启动 RAG 服务（端口 8003）...
start "RAG Service" cmd /k "cd /d "%PROJECT_DIR%" && venv\Scripts\activate && cd api && uvicorn rag_api:app --reload --host 0.0.0.0 --port 8003"

echo 正在启动 DeepSeek 服务（端口 8004）...
start "DeepSeek Service" cmd /k "cd /d "%PROJECT_DIR%" && venv\Scripts\activate && cd api && uvicorn deepseek_api:app --reload --host 0.0.0.0 --port 8004"

echo 正在启动客户端...
start "Client" cmd /k "cd /d "%PROJECT_DIR%" && venv\Scripts\activate && python chat_loop.py"

echo 所有窗口已启动。按任意键退出此窗口...
pause >nul