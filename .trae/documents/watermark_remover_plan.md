# 扫描全能王水印去除工具 - 实现方案

## Context（背景）

用户需要一个 Windows EXE 桌面工具，用于去除国内扫描全能王（CamScanner）免费版在导出 PDF/图片时强制添加的右下角水印。该水印特征明确：
- **位置**：固定在文档页面右下角
- **尺寸**：宽度约为页面宽度的 1/3，高度约为页面高度的 1/14
- **样式**：半透明灰色文字（"扫描全能王"），可能带小图标

目标：构建一个支持 PDF/图片导入、批量处理、自动+手动两种去除模式的桌面应用，最终打包为 EXE。

## 技术选型

| 组件 | 技术 | 用途 |
|------|------|------|
| GUI | PyQt5 | 主界面、文件列表、图片预览、拖拽框选 |
| 图像处理 | OpenCV (cv2) | 阈值分割、形态学操作、inpaint 修复 |
| 图像 IO | Pillow (PIL) | 通用图片读写 |
| PDF 处理 | PyMuPDF (fitz) | PDF 渲染为图像、图像重建 PDF |
| 数组运算 | NumPy | 像素矩阵操作 |
| 打包 | PyInstaller | 生成 Windows EXE |

## 目录结构

```
d:\Trae\全能王水印去除\
├── main.py                    # 程序入口
├── app/
│   ├── __init__.py
│   ├── main_window.py         # 主窗口（文件列表 + 预览 + 工具栏）
│   ├── image_canvas.py        # 图片预览画布，支持拖拽框选
│   ├── worker.py              # 后台处理线程，避免界面卡死
│   └── styles.py              # QSS 样式表（3 色配色）
├── core/
│   ├── __init__.py
│   ├── remover.py             # 去水印主流程编排
│   ├── detector.py            # 水印区域检测（自动模式）
│   ├── inpainter.py           # 图像修复算法封装
│   ├── image_io.py            # 图片加载/保存
│   └── pdf_io.py              # PDF 加载/渲染/重建
├── requirements.txt
├── build.bat                  # PyInstaller 一键打包脚本
└── README.md
```

## 配色方案（不超过 3 色，简洁不花哨）

- **背景**：`#FFFFFF` 白色
- **主色**：`#2C3E50` 深蓝灰（文字、标题栏、列表项）
- **强调**：`#3498DB` 蓝色（按钮、选中高亮、链接）

字体：微软雅黑 9pt（正文）/ 11pt（标题）。

## 界面布局

```
┌──────────────────────────────────────────────────────────┐
│  扫描全能王水印去除工具                          [─][□][×]  │
├──────────────────────────────────────────────────────────┤
│  [+ 添加文件]  [清空列表]  [批量自动去除]  [导出全部]      │
├──────────────────┬───────────────────────────────────────┤
│ 文件列表 (可拖拽) │            图片预览区域                │
│ ┌──────────────┐ │   ┌─────────────────────────────┐    │
│ │ doc1.pdf  ✓ │ │   │                             │    │
│ │ doc2.jpg  ⏳│ │   │      [当前页面预览]          │    │
│ │ doc3.pdf    │ │   │   拖拽鼠标可框选水印区域    │    │
│ │ ...         │ │   │                             │    │
│ └──────────────┘ │   └─────────────────────────────┘    │
│                  │  [自动去除] [手动去除] [重置]          │
│                  │  处理模式: ○自动检测  ○手动框选        │
│                  │  状态: 已处理 2/3                      │
└──────────────────┴───────────────────────────────────────┘
```

## 核心算法

### 1. 自动检测模式（detector.py）

扫描全能王水印位置固定，采用"定位 + 阈值分割 + 修复"三步：

```python
def detect_watermark_region(img_shape):
    """返回水印默认区域 (x, y, w, h)"""
    h, w = img_shape[:2]
    wm_w = int(w * 0.34)   # 页宽 1/3
    wm_h = int(h * 0.075)  # 页高 1/14 ≈ 7%
    margin = int(w * 0.01) # 右下留 1% 边距
    x = w - wm_w - margin
    y = h - wm_h - margin
    return (x, y, wm_w, wm_h)

def build_watermark_mask(image, region):
    """在水印区域内通过阈值分割生成 mask"""
    x, y, w, h = region
    roi = cv2.cvtColor(image[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)
    # 水印文字像素比白色背景暗
    _, mask = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # 形态学膨胀，确保完全覆盖文字边缘
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.dilate(mask, kernel, iterations=2)
    return mask
```

### 2. 图像修复（inpainter.py）

```python
def inpaint_region(image, region, mode='auto'):
    """修复水印区域"""
    if mode == 'auto':
        mask = build_watermark_mask(image, region)
        # 将局部 mask 映射回全图
        full_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        x, y, w, h = region
        full_mask[y:y+h, x:x+w] = mask
    else:  # manual
        x, y, w, h = region
        full_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        full_mask[y:y+h, x:x+w] = 255
    # TELEA 算法对扫描文档效果好，速度快
    return cv2.inpaint(image, full_mask, 3, cv2.INPAINT_TELEA)
```

### 3. PDF 处理流程（pdf_io.py）

```python
def remove_pdf_watermark(input_path, output_path, mode='auto', regions=None):
    doc = fitz.open(input_path)
    for page in doc:
        # 以 200 DPI 渲染为图像（保证清晰度）
        pix = page.get_pixmap(dpi=200)
        img = pixmap_to_ndarray(pix)
        # 去水印
        if mode == 'auto':
            region = detect_watermark_region(img.shape)
            img = inpaint_region(img, region, 'auto')
        else:
            for r in regions:
                img = inpaint_region(img, r, 'manual')
        # 替换原页面为处理后的图像
        replace_page_with_image(page, img)
    doc.save(output_path)
```

> 注意：此方案会将 PDF 栅格化（文字变图像），对扫描件 PDF 没有影响（本来就是图像），但对矢量 PDF 会损失文字可选性。扫描全能王导出的 PDF 都是图像型，此方案适用。

## 工作流（用户操作路径）

1. **导入**：拖拽文件到窗口 或 点击"添加文件"，支持 PDF/JPG/PNG
2. **预览**：点击左侧列表项，右侧显示第一页预览
3. **单文件处理**：
   - 自动模式：选中文件 → 点"自动去除" → 自动定位右下角水印并修复
   - 手动模式：在预览图上拖拽框选水印 → 点"手动去除"
4. **批量处理**：点"批量自动去除" → 后台线程顺序处理所有文件，列表项显示进度（⏳→✓）
5. **导出**：点"导出全部" → 选择输出目录，处理后的文件以 `_no_watermark` 后缀保存
6. **PDF 多页**：PDF 文件预览时支持翻页（上一页/下一页按钮），每页独立处理

## 关键文件实现要点

### `main.py`
- 创建 QApplication，实例化 MainWindow，启动事件循环

### `app/main_window.py`
- QMainWindow + QSplitter（左列表 + 右预览）
- 顶部 QToolBar：添加文件、清空、批量处理、导出
- 左侧 QListWidget：显示文件名 + 状态图标
- 右侧 ImageCanvas + 控制按钮
- 支持 drag-drop 事件（QDropEvent）
- 批量处理时用 QThread（worker.py）防止界面冻结，通过信号更新进度

### `app/image_canvas.py`
- 继承 QWidget，重写 paintEvent 绘制图片
- 鼠标按下/移动/释放事件实现框选
- 框选完成后发出 `regionSelected(QRect)` 信号
- 坐标需在原始图像分辨率和显示分辨率间换算

### `app/worker.py`
- QThread 子类，处理批量任务
- 信号：`progress(int, int)`（当前/总数）、`fileDone(str)`、`error(str)`

### `core/remover.py`
- 统一入口 `remove_watermark(input_path, output_path, mode, regions)`
- 根据扩展名分发到 image_io 或 pdf_io

## 打包方案（build.bat）

```bat
pyinstaller --noconfirm --onedir --windowed ^
  --name "全能王水印去除工具" ^
  --icon icon.ico ^
  --add-data "app;app" ^
  --add-data "core;core" ^
  main.py
```

参数说明：
- `--onedir`：生成目录而非单文件，启动更快，避免 PyMuPDF 解压问题
- `--windowed`：不显示控制台窗口
- PyMuPDF 需要 `--add-data` 包含其依赖

## 依赖清单（requirements.txt）

```
PyQt5>=5.15
opencv-python>=4.8
Pillow>=10.0
PyMuPDF>=1.23
numpy>=1.24
pyinstaller>=6.0
```

## 验证方法

1. **安装依赖**：`pip install -r requirements.txt`
2. **运行测试**：`python main.py`，导入含扫描全能王水印的 PDF/图片
3. **自动模式验证**：导入文件 → 自动去除 → 检查右下角水印是否消失、底色是否自然
4. **手动模式验证**：拖拽框选水印 → 手动去除 → 检查修复效果
5. **批量验证**：导入 5+ 文件 → 批量处理 → 检查所有文件输出
6. **PDF 多页验证**：导入多页 PDF → 翻页检查每页水印均被去除
7. **打包验证**：运行 `build.bat` → 在 `dist/` 目录运行 EXE → 重复以上测试

## 已知限制

- PDF 处理后会栅格化（文字变图像），扫描件无影响，矢量 PDF 会损失文字可选性
- 自动模式依赖水印在右下角默认位置，若水印位置异常需切换手动模式
- 若水印下方原本有正文内容，该内容无法恢复（inpaint 只能基于周围像素填充）
- 需要约 200MB 磁盘空间存放 OpenCV、PyQt5 等依赖
