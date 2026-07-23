@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ╔════════════════════════════════════════╗
echo ║  美鸥热点通 — 内容创作工坊             ║
echo ╚════════════════════════════════════════╝
echo.

REM 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，请先安装 Python 3.10+
    echo    下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查 .env 配置
if not exist ".env" (
    echo ❌ 未找到 .env 配置文件
    echo    请复制 .env.example 为 .env，填入 API Key
    pause
    exit /b 1
)

REM 安装依赖（首次运行）
if not exist "venv\" (
    echo 🔧 首次运行，正在创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo 🚀 启动服务器...
echo    打开浏览器访问: http://127.0.0.1:8888
echo    按 Ctrl+C 停止
echo.
python app.py
pause
