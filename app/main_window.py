"""主窗口：文件列表 + 图片预览 + 工具栏。"""
import os
from datetime import datetime

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QToolBar, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox, QStatusBar, QProgressBar, QFrame, QSizePolicy,
    QApplication
)

from .image_canvas import ImageCanvas
from .worker import BatchWorker
from .styles import QSS, COLOR_PRIMARY, COLOR_ACCENT
from core.image_io import is_image_file, load_image
from core.pdf_io import is_pdf_file, get_page_count, render_page_for_preview
from core.remover import remove_watermark, get_output_path
from core.detector import detect_watermark_region
from core.inpainter import inpaint_region, inpaint_regions


PREVIEW_DPI = 120

STATUS_ICONS = {
    'pending': '○',
    'processing': '◌',
    'done': '✓',
    'failed': '✗',
}
STATUS_COLORS = {
    'pending': '#7F8C8D',
    'processing': '#F39C12',
    'done': '#27AE60',
    'failed': '#E74C3C',
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("扫描全能王水印去除工具")
        self.resize(1200, 780)
        self.setMinimumSize(900, 600)

        # 数据
        self.files = []                  # [(path, name), ...]
        self.file_states = {}            # path -> {'status', 'output'}
        self.current_path = None
        self.current_preview_image = None  # 当前预览的 cv2 图像

        # PDF 分页
        self.current_pdf_path = None
        self.current_page = 0
        self.pdf_page_count = 0

        # 手动选区
        self.image_manual_regions = {}   # path -> [(x,y,w,h), ...]
        self.pdf_manual_regions = {}     # path -> {page_idx: [(x,y,w,h), ...]}

        # 预览效果状态
        self.is_previewing = False       # 是否处于"预览去除效果"模式
        self.preview_result_image = None # 预览处理后的图像（预览分辨率）

        # 工作线程
        self.worker = None
        self.output_dir = None
        self.batch_output_dir = None  # 批量处理的输出子文件夹

        self._build_ui()
        self._connect_signals()
        self.setStyleSheet(QSS)

    def _build_ui(self):
        # 顶部工具栏
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(toolbar)

        self.act_add = toolbar.addAction("+ 添加文件")
        self.act_clear = toolbar.addAction("清空列表")
        toolbar.addSeparator()
        self.act_batch = toolbar.addAction("批量自动去除")
        self.act_export = toolbar.addAction("导出全部")
        toolbar.addSeparator()
        self.act_set_output = toolbar.addAction("设置输出目录")

        # 中央 splitter
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：文件列表
        left_panel = QFrame()
        left_panel.setMinimumWidth(220)
        left_panel.setMaximumWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)

        list_title = QLabel("文件列表")
        list_title.setStyleSheet(f"font-weight: bold; color: {COLOR_PRIMARY};")
        left_layout.addWidget(list_title)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SingleSelection)
        left_layout.addWidget(self.file_list)

        hint = QLabel("支持拖入 PDF / JPG / PNG")
        hint.setStyleSheet("color: #95A5A6; font-size: 8pt;")
        hint.setWordWrap(True)
        left_layout.addWidget(hint)

        # 右侧：预览 + 控制
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)

        # 文件信息栏
        info_bar = QHBoxLayout()
        self.label_file = QLabel("未选择文件")
        self.label_file.setStyleSheet(f"font-weight: bold; color: {COLOR_PRIMARY};")
        info_bar.addWidget(self.label_file)
        info_bar.addStretch()

        # PDF 翻页按钮
        self.btn_prev_page = QPushButton("上一页")
        self.btn_prev_page.setProperty("flat", True)
        self.btn_next_page = QPushButton("下一页")
        self.btn_next_page.setProperty("flat", True)
        self.label_page = QLabel("0/0")
        self.label_page.setStyleSheet("color: #7F8C8D;")
        info_bar.addWidget(self.btn_prev_page)
        info_bar.addWidget(self.label_page)
        info_bar.addWidget(self.btn_next_page)
        right_layout.addLayout(info_bar)

        # 画布
        self.canvas = ImageCanvas()
        right_layout.addWidget(self.canvas, stretch=1)

        # 选区信息
        self.label_selection = QLabel("已框选 0 个区域")
        self.label_selection.setStyleSheet("color: #7F8C8D;")
        right_layout.addWidget(self.label_selection)

        # 模式选择 + 操作按钮
        ctrl_bar = QHBoxLayout()

        mode_box = QHBoxLayout()
        mode_box.setSpacing(12)
        self.rb_auto = QRadioButton("自动检测")
        self.rb_manual = QRadioButton("手动框选")
        self.rb_auto.setChecked(True)
        mode_box.addWidget(QLabel("处理模式:"))
        mode_box.addWidget(self.rb_auto)
        mode_box.addWidget(self.rb_manual)
        mode_group = QWidget()
        mode_group.setLayout(mode_box)
        ctrl_bar.addWidget(mode_group)

        ctrl_bar.addStretch()

        self.btn_preview = QPushButton("预览效果")
        self.btn_preview.setProperty("flat", True)
        self.btn_remove = QPushButton("去除水印")
        self.btn_remove.setProperty("flat", False)
        self.btn_reset = QPushButton("重置选区")
        self.btn_reset.setProperty("flat", True)
        ctrl_bar.addWidget(self.btn_reset)
        ctrl_bar.addWidget(self.btn_preview)
        ctrl_bar.addWidget(self.btn_remove)
        right_layout.addLayout(ctrl_bar)

        # 操作提示
        tip = QLabel("自动模式：点【预览效果】查看去除结果，确认后点【去除水印】保存。\n"
                     "手动模式：先在图上拖拽框选水印区域，再点【预览效果】查看。\n"
                     "支持拖入文件或文件夹。")
        tip.setStyleSheet("color: #95A5A6; font-size: 8pt; padding: 4px;")
        tip.setWordWrap(True)
        right_layout.addWidget(tip)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        self.setCentralWidget(splitter)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # 启用拖拽
        self.setAcceptDrops(True)

        # 初始状态
        self._update_button_states()

    def _connect_signals(self):
        self.act_add.triggered.connect(self._on_add_files)
        self.act_clear.triggered.connect(self._on_clear)
        self.act_batch.triggered.connect(self._on_batch_process)
        self.act_export.triggered.connect(self._on_export_all)
        self.act_set_output.triggered.connect(self._on_set_output_dir)

        self.file_list.currentItemChanged.connect(self._on_file_selected)
        self.btn_remove.clicked.connect(self._on_remove_watermark)
        self.btn_reset.clicked.connect(self._on_reset_selection)
        self.btn_preview.clicked.connect(self._on_toggle_preview)
        self.btn_prev_page.clicked.connect(self._on_prev_page)
        self.btn_next_page.clicked.connect(self._on_next_page)

        self.canvas.regionSelected.connect(self._on_region_selected)

        self.rb_auto.toggled.connect(self._on_mode_changed)

    # ---------- 拖拽 ----------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if os.path.isfile(p) and self._is_supported(p):
                paths.append(p)
            elif os.path.isdir(p):
                paths.extend(self._scan_directory(p))
        if paths:
            self._add_files(paths)
            self.status_label.setText(f"已加载 {len(self.files)} 个文件")

    def _scan_directory(self, dir_path):
        """递归扫描目录，返回所有支持的文件路径。"""
        result = []
        for root, dirs, files in os.walk(dir_path):
            for f in files:
                full = os.path.join(root, f)
                if self._is_supported(full):
                    result.append(full)
        return result

    # ---------- 文件管理 ----------
    def _is_supported(self, path):
        return is_image_file(path) or is_pdf_file(path)

    def _add_files(self, paths):
        for p in paths:
            if p in self.file_states:
                continue
            self.files.append(p)
            self.file_states[p] = {'status': 'pending', 'output': None}
            item = QListWidgetItem(self._format_item_text(p, 'pending'))
            self.file_list.addItem(item)
        if self.current_path is None and self.files:
            self.file_list.setCurrentRow(0)
        self._update_button_states()
        self.status_label.setText(f"已加载 {len(self.files)} 个文件")

    def _format_item_text(self, path, status):
        name = os.path.basename(path)
        icon = STATUS_ICONS.get(status, '○')
        return f"  {icon}  {name}"

    def _update_file_item(self, path, status):
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if i < len(self.files) and self.files[i] == path:
                item.setText(self._format_item_text(path, status))
                color = QColor(STATUS_COLORS.get(status, '#7F8C8D'))
                item.setForeground(color)
                break

    def _on_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "",
            "支持的文件 (*.pdf *.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp);;所有文件 (*)"
        )
        if paths:
            self._add_files(paths)

    def _on_clear(self):
        self._exit_preview()
        self.file_list.clear()
        self.files.clear()
        self.file_states.clear()
        self.image_manual_regions.clear()
        self.pdf_manual_regions.clear()
        self.current_path = None
        self.current_pdf_path = None
        self.current_preview_image = None
        self.canvas.clear_image()
        self.label_file.setText("未选择文件")
        self._update_page_label()
        self._update_button_states()
        self.status_label.setText("已清空")

    # ---------- 预览 ----------
    def _on_file_selected(self, current, previous):
        # 切换文件时退出预览模式
        self._exit_preview()

        if current is None:
            self.current_path = None
            self.canvas.clear_image()
            self.label_file.setText("未选择文件")
            self._update_page_label()
            self._update_button_states()
            return

        row = self.file_list.row(current)
        if row < 0 or row >= len(self.files):
            return
        path = self.files[row]
        self.current_path = path
        self.canvas.clear_selections()
        self._update_selection_label()

        # 文件不存在时的容错处理
        if not os.path.exists(path):
            self.current_preview_image = None
            self.current_pdf_path = None
            self.pdf_page_count = 0
            self.canvas.clear_image()
            self.label_file.setText(f"{os.path.basename(path)}  (文件不存在)")
            self._update_page_label()
            self._update_button_states()
            return

        if is_pdf_file(path):
            self.current_pdf_path = path
            self.current_page = 0
            try:
                self.pdf_page_count = get_page_count(path)
            except Exception as e:
                self.pdf_page_count = 0
                QMessageBox.warning(self, "错误", f"无法打开 PDF:\n{e}")
            self._render_pdf_page()
        elif is_image_file(path):
            self.current_pdf_path = None
            self.pdf_page_count = 0
            self.current_page = 0
            try:
                img = load_image(path)
                self.current_preview_image = img
                self.canvas.set_image(img)
            except Exception as e:
                self.current_preview_image = None
                self.canvas.clear_image()
                QMessageBox.warning(self, "错误", f"无法加载图片:\n{e}")
        else:
            self.canvas.clear_image()

        self.label_file.setText(os.path.basename(path))
        self._update_page_label()
        self._update_button_states()
        self._restore_selections_for_current()

    def _render_pdf_page(self):
        if not self.current_pdf_path:
            return
        try:
            img = render_page_for_preview(self.current_pdf_path,
                                          self.current_page, dpi=PREVIEW_DPI)
            self.current_preview_image = img
            self.canvas.set_image(img)
        except Exception as e:
            self.canvas.clear_image()
            QMessageBox.warning(self, "错误", f"无法渲染 PDF 页面:\n{e}")

    def _update_page_label(self):
        if self.pdf_page_count > 0:
            self.label_page.setText(f"{self.current_page + 1}/{self.pdf_page_count}")
        else:
            self.label_page.setText("")

    def _on_prev_page(self):
        if self.current_pdf_path and self.current_page > 0:
            self._exit_preview()
            self.canvas.clear_selections()
            self.current_page -= 1
            self._render_pdf_page()
            self._update_page_label()
            self._restore_selections_for_current()

    def _on_next_page(self):
        if (self.current_pdf_path and
                self.current_page < self.pdf_page_count - 1):
            self._exit_preview()
            self.canvas.clear_selections()
            self.current_page += 1
            self._render_pdf_page()
            self._update_page_label()
            self._restore_selections_for_current()

    # ---------- 选区 ----------
    def _on_region_selected(self, x, y, w, h):
        if self.current_path is None or self.current_preview_image is None:
            return

        if is_pdf_file(self.current_path):
            if self.current_path not in self.pdf_manual_regions:
                self.pdf_manual_regions[self.current_path] = {}
            page_dict = self.pdf_manual_regions[self.current_path]
            if self.current_page not in page_dict:
                page_dict[self.current_page] = []
            page_dict[self.current_page].append((x, y, w, h))
        else:
            if self.current_path not in self.image_manual_regions:
                self.image_manual_regions[self.current_path] = []
            self.image_manual_regions[self.current_path].append((x, y, w, h))

        self._update_selection_label()

    def _on_reset_selection(self):
        self._exit_preview()
        self.canvas.clear_selections()
        if self.current_path:
            if is_pdf_file(self.current_path):
                self.pdf_manual_regions.get(self.current_path, {}).pop(
                    self.current_page, None)
            else:
                self.image_manual_regions.pop(self.current_path, None)
        self._update_selection_label()

    def _restore_selections_for_current(self):
        """切换文件/页面时恢复已有的选区显示。"""
        # 当前实现：选区仅在画布上保留，切换文件/页面后清空显示
        # 数据已保存在 self.image_manual_regions / self.pdf_manual_regions
        self._update_selection_label()

    def _update_selection_label(self):
        count = len(self.canvas.get_selections())
        self.label_selection.setText(f"已框选 {count} 个区域")

    def _on_mode_changed(self):
        # 切换模式时退出预览、清空当前画布选区
        self._exit_preview()
        self.canvas.clear_selections()
        self._update_selection_label()

    # ---------- 预览效果 ----------
    def _on_toggle_preview(self):
        """切换"预览去除效果"模式：在画布上显示处理后的图像，不保存文件。"""
        if self.current_preview_image is None:
            QMessageBox.information(self, "提示", "请先选择文件")
            return

        if self.is_previewing:
            self._exit_preview()
            return

        mode = 'auto' if self.rb_auto.isChecked() else 'manual'

        # 获取当前页面的选区（手动模式）
        if mode == 'manual':
            regions = self._get_current_regions()
            if not regions:
                QMessageBox.information(self, "提示",
                                        "请先在预览图上框选水印区域")
                return

        # 在预览分辨率图像上做内存处理（不读写文件）
        try:
            img = self.current_preview_image.copy()
            if mode == 'auto':
                region = detect_watermark_region(img.shape)
                result = inpaint_region(img, region, mode='auto')
            else:
                result = inpaint_regions(img, regions, mode='manual')
        except Exception as e:
            QMessageBox.warning(self, "预览失败", str(e))
            return

        self.preview_result_image = result
        self.is_previewing = True
        # 显示处理结果（隐藏选区框，禁用框选）
        self.canvas.set_selection_enabled(False)
        self.canvas.set_image(result)
        self.btn_preview.setText("恢复原图")
        self.label_selection.setText("【预览模式】查看去除效果，点【去除水印】保存")
        self.status_label.setText("预览中：点【恢复原图】返回，或点【去除水印】保存")

    def _exit_preview(self):
        """退出预览模式，恢复原图显示。"""
        if not self.is_previewing:
            return
        self.is_previewing = False
        self.preview_result_image = None
        if self.current_preview_image is not None:
            self.canvas.set_image(self.current_preview_image)
        self.canvas.set_selection_enabled(True)
        self.btn_preview.setText("预览效果")
        self._update_selection_label()

    def _get_current_regions(self):
        """获取当前文件/页面的手动选区列表。"""
        if self.current_path is None:
            return []
        if is_pdf_file(self.current_path):
            return self.pdf_manual_regions.get(
                self.current_path, {}).get(self.current_page, [])
        return self.image_manual_regions.get(self.current_path, [])

    # ---------- 处理 ----------
    def _on_remove_watermark(self):
        if self.current_path is None:
            QMessageBox.information(self, "提示", "请先选择文件")
            return

        path = self.current_path
        mode = 'auto' if self.rb_auto.isChecked() else 'manual'

        if mode == 'manual':
            if is_pdf_file(path):
                regions_per_page = self.pdf_manual_regions.get(path, {})
                if not regions_per_page or not any(
                        v for v in regions_per_page.values()):
                    QMessageBox.information(self, "提示",
                                            "请先在预览图上框选水印区域")
                    return
            else:
                regions = self.image_manual_regions.get(path, [])
                if not regions:
                    QMessageBox.information(self, "提示",
                                            "请先在预览图上框选水印区域")
                    return

        # 输出目录
        out_dir = self.output_dir or os.path.dirname(path)
        if not os.path.isdir(out_dir):
            out_dir = os.path.expanduser("~")

        output_path = get_output_path(path, out_dir)

        self.status_label.setText(f"正在处理: {os.path.basename(path)}")
        QApplication.processEvents()

        try:
            if mode == 'manual':
                if is_pdf_file(path):
                    remove_watermark(path, output_path, mode='manual',
                                     regions_per_page=regions_per_page)
                else:
                    regions = self.image_manual_regions.get(path, [])
                    remove_watermark(path, output_path, mode='manual',
                                     regions=regions)
            else:
                remove_watermark(path, output_path, mode='auto')

            self.file_states[path]['status'] = 'done'
            self.file_states[path]['output'] = output_path
            self._update_file_item(path, 'done')
            self.status_label.setText(f"已完成: {output_path}")

            # 处理后退出预览模式，显示处理后的结果
            self._exit_preview()
            if is_image_file(output_path):
                img = load_image(output_path)
                self.current_preview_image = img
                self.canvas.set_image(img)
            elif is_pdf_file(output_path):
                self.current_pdf_path = output_path
                try:
                    self.pdf_page_count = get_page_count(output_path)
                except Exception:
                    self.pdf_page_count = 0
                self.current_page = 0
                self._render_pdf_page()
                self._update_page_label()

            QMessageBox.information(self, "完成",
                                    f"水印已去除，输出到:\n{output_path}")
        except Exception as e:
            self.file_states[path]['status'] = 'failed'
            self._update_file_item(path, 'failed')
            self.status_label.setText(f"处理失败: {e}")
            QMessageBox.warning(self, "处理失败", str(e))

    def _on_batch_process(self):
        if not self.files:
            QMessageBox.information(self, "提示", "请先添加文件")
            return

        base_dir = self.output_dir
        if not base_dir or not os.path.isdir(base_dir):
            base_dir = QFileDialog.getExistingDirectory(self, "选择输出目录")
            if not base_dir:
                return
            self.output_dir = base_dir

        # 批量只支持自动模式
        paths = [p for p in self.files if self.file_states[p]['status'] != 'done']
        if not paths:
            QMessageBox.information(self, "提示", "所有文件已处理完成")
            return

        # 在输出目录下创建带时间戳的子文件夹
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(base_dir, f"去水印结果_{timestamp}")
        os.makedirs(out_dir, exist_ok=True)
        self.batch_output_dir = out_dir

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(paths))
        self.progress_bar.setValue(0)

        self.worker = BatchWorker(paths, out_dir, mode='auto')
        self.worker.progress.connect(self._on_batch_progress)
        self.worker.fileDone.connect(self._on_batch_file_done)
        self.worker.fileFailed.connect(self._on_batch_file_failed)
        self.worker.allDone.connect(self._on_batch_all_done)
        self.worker.start()

        self.status_label.setText("批量处理中...")
        self._update_button_states(batch_running=True)

    def _on_batch_progress(self, current, total, filename):
        self.progress_bar.setValue(current)
        self.status_label.setText(f"处理中 ({current}/{total}): {filename}")

    def _on_batch_file_done(self, input_path, output_path):
        self.file_states[input_path]['status'] = 'done'
        self.file_states[input_path]['output'] = output_path
        self._update_file_item(input_path, 'done')

    def _on_batch_file_failed(self, input_path, error):
        self.file_states[input_path]['status'] = 'failed'
        self._update_file_item(input_path, 'failed')

    def _on_batch_all_done(self, success, failed):
        self.progress_bar.setVisible(False)
        out_dir = getattr(self, 'batch_output_dir', '')
        msg = f"批量完成: 成功 {success} 个, 失败 {failed} 个"
        if out_dir:
            msg += f"\n输出文件夹: {out_dir}"
        self.status_label.setText(msg)
        self._update_button_states(batch_running=False)
        if failed > 0:
            QMessageBox.warning(self, "批量处理完成", msg)
        else:
            QMessageBox.information(self, "批量处理完成", msg)

    # ---------- 导出 ----------
    def _on_export_all(self):
        done_files = [(p, self.file_states[p]['output'])
                      for p in self.files
                      if self.file_states[p]['status'] == 'done'
                      and self.file_states[p]['output']]
        if not done_files:
            QMessageBox.information(self, "提示",
                                    "没有已处理的文件可导出。请先处理文件。")
            return

        base_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not base_dir:
            return

        # 在导出目录下创建带时间戳的子文件夹
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(base_dir, f"导出文件_{timestamp}")
        os.makedirs(out_dir, exist_ok=True)

        import shutil
        copied = 0
        for src_path, src_output in done_files:
            try:
                name = os.path.basename(src_output)
                dst = os.path.join(out_dir, name)
                # 处理重名
                if os.path.exists(dst):
                    base, ext = os.path.splitext(name)
                    i = 1
                    while os.path.exists(os.path.join(out_dir, f"{base}_{i}{ext}")):
                        i += 1
                    dst = os.path.join(out_dir, f"{base}_{i}{ext}")
                shutil.copy2(src_output, dst)
                copied += 1
            except Exception as e:
                pass

        QMessageBox.information(self, "导出完成",
                                f"已导出 {copied} 个文件到:\n{out_dir}")

    def _on_set_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            self.output_dir = d
            self.status_label.setText(f"输出目录: {d}")

    # ---------- 状态 ----------
    def _update_button_states(self, batch_running=False):
        has_files = bool(self.files)
        has_current = self.current_path is not None
        has_preview_image = self.current_preview_image is not None

        self.act_clear.setEnabled(has_files)
        self.act_batch.setEnabled(has_files and not batch_running)
        self.act_export.setEnabled(has_files and not batch_running)

        self.btn_remove.setEnabled(has_current and not batch_running)
        self.btn_reset.setEnabled(has_current and not self.is_previewing)
        self.btn_preview.setEnabled(has_preview_image and not batch_running)

        has_pdf = self.current_pdf_path is not None
        self.btn_prev_page.setEnabled(has_pdf and self.current_page > 0)
        self.btn_next_page.setEnabled(
            has_pdf and self.current_page < self.pdf_page_count - 1)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "确认退出",
                "批量处理正在进行中，确定退出吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            self.worker.cancel()
            self.worker.wait(3000)
        event.accept()
