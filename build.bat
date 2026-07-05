@echo off
chcp 65001 >nul
echo ========================================
echo   扫描全能王水印去除工具 - 打包脚本
echo ========================================
echo.

REM 检查 Python 环境
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 安装依赖
echo [1/3] 安装依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

REM 清理旧构建
echo [2/3] 清理旧构建...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "全能王水印去除工具.spec" del /q "全能王水印去除工具.spec"

REM 打包
echo [3/3] 开始打包...
pyinstaller --noconfirm --onedir --windowed ^
  --name "全能王水印去除工具" ^
  --add-data "app;app" ^
  --add-data "core;core" ^
  main.py

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成！
echo   EXE 位置: dist\全能王水印去除工具\全能王水印去除工具.exe
echo ========================================
pause
