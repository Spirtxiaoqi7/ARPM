@echo off
setlocal
chcp 65001 >nul

echo ==========================================
echo   ARPM v4.0 启动脚本
echo ==========================================

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%.") do set "SCRIPT_DIR=%%~fI"
set "APP_ROOT="

call :try_app_root "%SCRIPT_DIR%"
call :try_app_root "%SCRIPT_DIR%arpm-app"
call :try_app_root "%SCRIPT_DIR%code\arpm-app"
call :try_app_root "%SCRIPT_DIR%ARPM\code\arpm-app"
call :try_app_root "%SCRIPT_DIR%..\arpm-app"
call :try_app_root "%SCRIPT_DIR%..\code\arpm-app"
call :try_app_root "%SCRIPT_DIR%..\ARPM\code\arpm-app"

if not defined APP_ROOT (
    echo [错误] 未找到应用目录。要求候选目录下存在 backend\app.py 和 requirements.txt
    echo [错误] 当前脚本目录: %SCRIPT_DIR%
    exit /b 1
)

set "WORKSPACE_ROOT=%APP_ROOT%"
set "VENV_DIR=%WORKSPACE_ROOT%\.venv"
set "ARPM_RUNTIME_DIR=%WORKSPACE_ROOT%\runtime\arpm-app"
set "ARPM_MODEL_ROOT=%WORKSPACE_ROOT%\assets\models"
set "PYTHON_EXE=python"
set "PIP_EXE=pip"
set "PYTHONNOUSERSITE=1"

echo [信息] 应用目录: %APP_ROOT%
echo [信息] 工作区目录: %WORKSPACE_ROOT%

if exist "%VENV_DIR%\Scripts\activate.bat" (
    call "%VENV_DIR%\Scripts\activate.bat"
    if exist "%VENV_DIR%\Scripts\python.exe" set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
    if exist "%VENV_DIR%\Scripts\pip.exe" set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"
    echo [成功] 已激活虚拟环境
) else (
    echo [警告] 未找到虚拟环境，将使用系统 Python
)

echo [检查] 正在检查依赖...
"%PYTHON_EXE%" -c "import flask" 2>nul || (
    echo [安装] 正在安装依赖...
    "%PIP_EXE%" install -r "%APP_ROOT%requirements.txt"
)

if /i "%ARPM_STARTUP_TEST%"=="1" (
    echo [测试] 启动前检查通过
    exit /b 0
)

echo [启动] 正在启动服务...
cd /d "%APP_ROOT%\backend"
"%PYTHON_EXE%" app.py

pause
exit /b %errorlevel%

:try_app_root
if defined APP_ROOT exit /b 0
set "CANDIDATE=%~f1"
if exist "%CANDIDATE%\backend\app.py" if exist "%CANDIDATE%\requirements.txt" (
    set "APP_ROOT=%CANDIDATE%"
)
exit /b 0
