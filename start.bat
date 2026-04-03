@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [错误] 未找到虚拟环境
    echo 请先运行: python -m venv venv
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo 正在启动 ARPM 服务...
echo 访问地址: http://localhost:5000
echo.

python app.py

pause
