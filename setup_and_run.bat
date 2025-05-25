@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo [1/4] 检查虚拟环境...
IF NOT EXIST venv (
    echo [创建虚拟环境...]
    python -m venv venv
) ELSE (
    echo [虚拟环境已存在，跳过创建。]
)

echo [2/4] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [3/4] 检查依赖是否已安装...

IF EXIST .deps_installed.flag (
    echo [已检测到安装标记，跳过依赖安装。]
) ELSE (
    echo [正在安装依赖...]
    pip install -r requirements.txt
    IF %ERRORLEVEL% NEQ 0 (
        echo [!!! 安装失败，请检查网络或 requirements.txt。]
        pause
        exit /b 1
    )
    echo [安装成功，创建标记文件 .deps_installed.flag]
    echo deps installed > .deps_installed.flag
)

echo.
echo [4/4] 运行脚本 javdb_scraper.py ...
python javdb_scraper.py

echo.
pause
