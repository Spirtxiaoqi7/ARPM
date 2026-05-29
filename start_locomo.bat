@echo off
setlocal
chcp 65001 >nul

echo ==========================================
echo   LOCOMO QA Console
echo ==========================================

set "APP_ROOT=%~dp0"
for %%I in ("%APP_ROOT%.") do set "APP_ROOT=%%~fI"

set "WORKSPACE_ROOT=%APP_ROOT%\..\.."
for %%I in ("%WORKSPACE_ROOT%") do set "WORKSPACE_ROOT=%%~fI"

set "VENV_PY=%WORKSPACE_ROOT%\env\arpm-venv\Scripts\python.exe"
set "PYTHON_EXE=python"

if exist "%VENV_PY%" (
    set "PYTHON_EXE=%VENV_PY%"
    echo [INFO] Using venv: %VENV_PY%
) else (
    echo [WARN] Venv not found, using system Python.
)

set "PYTHONNOUSERSITE=1"
set "LOCOMO_PORT=5050"

echo [INFO] App root: %APP_ROOT%
echo [INFO] URL: http://127.0.0.1:%LOCOMO_PORT%

if /i "%LOCOMO_STARTUP_TEST%"=="1" (
    "%PYTHON_EXE%" -m py_compile "%APP_ROOT%\LOCOMO\web_app.py"
    exit /b %errorlevel%
)

cd /d "%APP_ROOT%"
start "" "http://127.0.0.1:%LOCOMO_PORT%"
"%PYTHON_EXE%" "%APP_ROOT%\LOCOMO\web_app.py"

pause
exit /b %errorlevel%
