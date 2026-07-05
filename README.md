# 全能王水印去除工具

一个用于去除"扫描全能王"水印的桌面应用，支持 PDF 和图片文件。

## 功能特性

- 去除扫描全能王水印（默认位于右下角）
- 支持 PDF 和图片文件（PNG/JPG/JPEG/BMP/TIFF/WEBP）
- 两种工作模式：
  - **自动模式**：自动处理右下角默认位置
  - **手动模式**：在预览图上拖拽框选水印区域
- **预览效果**：去除前可在画布上查看效果
- **批量处理**：一次处理多个文件，自动生成带时间戳的输出文件夹
- **拖拽支持**：支持拖入文件或文件夹（含递归扫描子目录）

## 截图

（可选：添加应用截图）

## 安装

### 方式一：直接使用打包好的 EXE

从 [Releases](../../releases) 下载最新版本的 zip 包，解压后双击 `全能王水印去除工具.exe` 即可运行。

### 方式二：从源码运行

需要 Python 3.8+。

```bash
git clone https://github.com/xiaobaiNINiZ/quannengwang-watermark-remover.git
cd quannengwang-watermark-remover
pip install -r requirements.txt
python main.py
```

## 打包 EXE

```bash
pyinstaller --noconfirm --onedir --windowed --name "全能王水印去除工具" --add-data "app;app" --add-data "core;core" main.py
```

打包结果在 `dist/全能王水印去除工具/` 目录下。

## 使用方法

1. 启动应用，拖拽文件/文件夹到文件列表区域
2. 选中文件，模式选择【自动】或【手动】
   - 手动模式需在预览图上拖拽框选水印区域
3. 点击【预览效果】查看去除结果
4. 满意后点击【去除水印】保存，或选择【批量处理】一次性处理所有文件

## 项目结构

```
.
├── main.py                 # 程序入口
├── app/                    # GUI 模块
│   ├── main_window.py      # 主窗口
│   ├── image_canvas.py     # 图片预览画布
│   ├── worker.py           # 后台批量处理线程
│   └── styles.py           # QSS 样式
├── core/                   # 核心处理模块
│   ├── remover.py          # 主流程编排
│   ├── detector.py         # 水印区域检测
│   ├── inpainter.py        # 图像修复
│   ├── image_io.py         # 图片 IO
│   └── pdf_io.py           # PDF 渲染/处理
├── test_*.py               # 测试脚本
├── requirements.txt        # 依赖列表
├── .gitignore
└── README.md
```

## 技术栈

- **GUI**：PyQt5
- **图像处理**：OpenCV（cv2）
- **PDF 处理**：pdf2image + PyMuPDF（fitz）

## 核心算法

水印检测采用「右下角固定区域 + Otsu 阈值」策略，定位水印位置后使用 TELEA inpaint 算法进行修复。检测和修复均在原图全分辨率上完成，保证最终输出质量。

## 已知限制

- 水印下方若有正文内容，无法恢复
- 矢量 PDF 处理后会栅格化（扫描件无影响）
- 打包后的 EXE 体积约 200MB（包含 Python 运行时 + OpenCV + Qt）

## 许可证

MIT License

## 致谢

本项目仅供学习交流使用，请勿用于商业用途。
