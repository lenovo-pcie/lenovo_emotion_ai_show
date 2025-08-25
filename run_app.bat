@echo off
chcp 65001 >nul
title 多功能Python工具集

echo.
echo ================================================
echo           多功能Python工具集启动器
echo ================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python
    echo.
    echo 请访问 https://www.python.org/downloads/ 下载安装Python
    pause
    exit /b 1
)

echo ✅ Python已安装
echo.

REM 检查依赖
echo 🔍 检查依赖包...
python -c "import gradio, pandas, numpy, matplotlib, plotly, PIL, sklearn, cv2, wordcloud" >nul 2>&1
if errorlevel 1 (
    echo ❌ 缺少依赖包，正在安装...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ 依赖包安装失败
        pause
        exit /b 1
    )
    echo ✅ 依赖包安装完成
) else (
    echo ✅ 依赖包已安装
)

echo.
echo 🚀 启动应用...
echo 📱 应用将在浏览器中打开
echo 🌐 本地地址: http://localhost:7860
echo ⏹️  按 Ctrl+C 停止应用
echo.
echo ================================================
echo.

REM 启动应用
python main_app.py

echo.
echo 👋 应用已停止
pause
