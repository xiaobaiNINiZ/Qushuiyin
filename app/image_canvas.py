"""图片预览画布，支持拖拽框选水印区域。"""
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPainter, QPen, QColor, QBrush, QPixmap
from PyQt5.QtWidgets import QWidget, QScrollArea

import cv2
import numpy as np


class ImageCanvas(QWidget):
    """显示图像并支持鼠标拖拽框选。

    信号:
        regionSelected(int x, int y, int w, int h): 框选完成，坐标基于原始图像分辨率
    """

    regionSelected = pyqtSignal(int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._qimage = None            # QImage 用于显示
        self._orig_size = (0, 0)       # 原始图像 (w, h)
        self._display_scale = 1.0      # 显示缩放比例（原图 → 显示）

        self._selecting = False
        self._start_point = QPoint()
        self._end_point = QPoint()
        self._selections = []          # 已确认的选区列表 [QRect, ...]（显示坐标）
        self._selection_enabled = True # 是否允许框选（预览模式下禁用）

        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self.setAutoFillBackground(True)
        self.setStyleSheet("background-color: #FAFAFA;")

    def set_image(self, cv_image):
        """设置显示的图像（BGR ndarray）。"""
        if cv_image is None:
            self._qimage = None
            self._orig_size = (0, 0)
            self._selections.clear()
            self.update()
            return

        rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        self._orig_size = (w, h)
        self._qimage = QImage(rgb.tobytes(), w, h, w * 3, QImage.Format_RGB888).copy()
        self._selections.clear()
        self._fit_to_widget()
        self.update()

    def set_selection_enabled(self, enabled):
        """启用/禁用框选功能（预览模式下禁用）。"""
        self._selection_enabled = enabled
        if not enabled:
            self._selecting = False
            self._start_point = QPoint()
            self._end_point = QPoint()
            self.update()

    def clear_image(self):
        self.set_image(None)

    def clear_selections(self):
        self._selections.clear()
        self._start_point = QPoint()
        self._end_point = QPoint()
        self.update()

    def get_selections(self):
        """返回所有选区，坐标基于原始图像分辨率。返回 [(x, y, w, h), ...]。"""
        result = []
        for rect_display in self._selections:
            orig = self._display_to_orig_rect(rect_display)
            if orig.width() > 0 and orig.height() > 0:
                result.append((orig.x(), orig.y(), orig.width(), orig.height()))
        return result

    def sizeHint(self):
        return QSize(800, 600)

    def _fit_to_widget(self):
        """计算缩放比例使图像适应 widget 大小。"""
        if self._qimage is None or self._orig_size == (0, 0):
            self._display_scale = 1.0
            return
        w_orig, h_orig = self._orig_size
        w_avail = max(self.width() - 20, 100)
        h_avail = max(self.height() - 20, 100)
        scale_w = w_avail / w_orig
        scale_h = h_avail / h_orig
        self._display_scale = min(scale_w, scale_h, 1.0)

    def _display_offset(self):
        """图像在 widget 中的居中偏移。"""
        if self._qimage is None:
            return QPoint(0, 0)
        w_disp = int(self._orig_size[0] * self._display_scale)
        h_disp = int(self._orig_size[1] * self._display_scale)
        x = (self.width() - w_disp) // 2
        y = (self.height() - h_disp) // 2
        return QPoint(max(x, 0), max(y, 0))

    def _display_to_orig_rect(self, rect_display):
        """显示坐标 QRect → 原图坐标 QRect。"""
        offset = self._display_offset()
        scale = self._display_scale if self._display_scale > 0 else 1.0
        x1 = int((rect_display.left() - offset.x()) / scale)
        y1 = int((rect_display.top() - offset.y()) / scale)
        x2 = int((rect_display.right() - offset.x()) / scale)
        y2 = int((rect_display.bottom() - offset.y()) / scale)
        x1 = max(0, min(x1, self._orig_size[0]))
        y1 = max(0, min(y1, self._orig_size[1]))
        x2 = max(0, min(x2, self._orig_size[0]))
        y2 = max(0, min(y2, self._orig_size[1]))
        return QRect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

    def resizeEvent(self, event):
        self._fit_to_widget()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#FAFAFA"))

        if self._qimage is None:
            painter.setPen(QColor("#999999"))
            painter.drawText(self.rect(), Qt.AlignCenter,
                             "请从左侧选择文件预览\n或拖入文件")
            return

        offset = self._display_offset()
        w_disp = int(self._orig_size[0] * self._display_scale)
        h_disp = int(self._orig_size[1] * self._display_scale)
        target_rect = QRect(offset.x(), offset.y(), w_disp, h_disp)
        painter.drawImage(target_rect, self._qimage)

        # 绘制已确认的选区（半透明蓝色边框 + 半透明填充）
        for rect in self._selections:
            pen = QPen(QColor("#3498DB"), 2)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(52, 152, 219, 40)))
            painter.drawRect(rect)

        # 绘制当前拖拽中的选区
        if self._selecting:
            pen = QPen(QColor("#E74C3C"), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(231, 76, 60, 30)))
            current = QRect(self._start_point, self._end_point).normalized()
            painter.drawRect(current)

    def mousePressEvent(self, event):
        if (event.button() == Qt.LeftButton and self._qimage is not None
                and self._selection_enabled):
            self._selecting = True
            self._start_point = event.pos()
            self._end_point = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            rect = QRect(self._start_point, self._end_point).normalized()
            # 只接受大于 10x10 的选区
            if rect.width() > 10 and rect.height() > 10:
                self._selections.append(rect)
                orig = self._display_to_orig_rect(rect)
                self.regionSelected.emit(orig.x(), orig.y(),
                                          orig.width(), orig.height())
            self._start_point = QPoint()
            self._end_point = QPoint()
            self.update()
