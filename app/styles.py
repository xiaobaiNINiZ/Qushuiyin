"""QSS 样式表 - 3 色配色方案（白/深蓝灰/蓝）。"""

# 配色常量
COLOR_BG = "#FFFFFF"        # 背景
COLOR_PRIMARY = "#2C3E50"   # 主色：深蓝灰
COLOR_ACCENT = "#3498DB"    # 强调：蓝

QSS = f"""
* {{
    font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
    font-size: 9pt;
    color: {COLOR_PRIMARY};
}}

QMainWindow, QWidget {{
    background-color: {COLOR_BG};
}}

/* 顶部工具栏 */
QToolBar {{
    background-color: {COLOR_BG};
    border: none;
    border-bottom: 1px solid #ECECEC;
    padding: 6px 10px;
    spacing: 8px;
}}

QToolBar QToolButton {{
    background-color: {COLOR_ACCENT};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    min-width: 80px;
}}

QToolBar QToolButton:hover {{
    background-color: #2980B9;
}}

QToolBar QToolButton:pressed {{
    background-color: #21618C;
}}

QToolBar QToolButton:disabled {{
    background-color: #BDC3C7;
}}

/* 文件列表 */
QListWidget {{
    background-color: {COLOR_BG};
    border: 1px solid #ECECEC;
    border-radius: 4px;
    padding: 4px;
    outline: none;
}}

QListWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid #F5F5F5;
}}

QListWidget::item:selected {{
    background-color: {COLOR_ACCENT};
    color: white;
}}

QListWidget::item:hover {{
    background-color: #EBF5FB;
}}

/* 普通按钮 */
QPushButton {{
    background-color: {COLOR_ACCENT};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    min-width: 70px;
}}

QPushButton:hover {{
    background-color: #2980B9;
}}

QPushButton:pressed {{
    background-color: #21618C;
}}

QPushButton:disabled {{
    background-color: #BDC3C7;
}}

QPushButton[flat="true"] {{
    background-color: transparent;
    color: {COLOR_PRIMARY};
    border: 1px solid #BDC3C7;
}}

QPushButton[flat="true"]:hover {{
    background-color: #F5F5F5;
    border-color: {COLOR_ACCENT};
    color: {COLOR_ACCENT};
}}

/* 单选按钮 */
QRadioButton {{
    spacing: 6px;
    padding: 4px;
}}

QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 1px solid #BDC3C7;
    background-color: {COLOR_BG};
}}

QRadioButton::indicator:checked {{
    background-color: {COLOR_ACCENT};
    border-color: {COLOR_ACCENT};
}}

/* 标签 */
QLabel {{
    background-color: transparent;
}}

/* 滚动区域 */
QScrollArea {{
    border: 1px solid #ECECEC;
    border-radius: 4px;
    background-color: {COLOR_BG};
}}

/* 状态栏 */
QStatusBar {{
    background-color: #F8F9FA;
    border-top: 1px solid #ECECEC;
    color: {COLOR_PRIMARY};
}}

/* 分组标题 */
QGroupBox {{
    border: 1px solid #ECECEC;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}

/* 进度条 */
QProgressBar {{
    border: 1px solid #ECECEC;
    border-radius: 3px;
    text-align: center;
    background-color: #F5F5F5;
    height: 18px;
}}

QProgressBar::chunk {{
    background-color: {COLOR_ACCENT};
    border-radius: 2px;
}}
"""
