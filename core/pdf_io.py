"""PDF 文件的加载、渲染、水印去除和重建。

PDF 处理流程：
1. 用 PyMuPDF (fitz) 以 200 DPI 渲染每页为图像
2. 对每页图像去水印
3. 用处理后的图像替换原页面内容
4. 保存为新 PDF

注意：此方案会将 PDF 栅格化（文字变图像），扫描全能王导出的 PDF
本就是图像型，无影响；矢量 PDF 会损失文字可选性。
"""
import os

import cv2
import fitz
import numpy as np

from .detector import detect_watermark_region
from .inpainter import inpaint_region, inpaint_regions

RENDER_DPI = 200


def is_pdf_file(path):
    return os.path.splitext(path)[1].lower() == '.pdf'


def pixmap_to_ndarray(pix):
    """将 fitz.Pixmap 转为 BGR ndarray。"""
    if pix.alpha:
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, 4
        )
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 1:
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, 1
        )
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    else:
        # PyMuPDF 的 RGB 通道顺序需转为 OpenCV 的 BGR
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return img.copy()


def ndarray_to_pixmap(img_bgr):
    """将 BGR ndarray 转为 fitz.Pixmap (RGB)。

    通过 PNG 字节流构造，兼容不同版本的 PyMuPDF API。
    """
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    ok, buf = cv2.imencode('.png', rgb)
    if not ok:
        raise ValueError("无法编码图像为 PNG")
    return fitz.Pixmap(buf.tobytes())


def render_page_to_image(page, dpi=RENDER_DPI):
    """渲染 PDF 页面为 BGR ndarray。"""
    pix = page.get_pixmap(dpi=dpi)
    return pixmap_to_ndarray(pix)


def replace_page_with_image(page, image):
    """用图像覆盖 PDF 页面内容。

    processed image 有白色不透明背景且覆盖整个页面 rect，
    用 overlay=True 放在最上层即可完全遮盖原内容。
    """
    rect = page.rect
    page.insert_image(rect, pixmap=ndarray_to_pixmap(image), overlay=True)


def remove_pdf_watermark(input_path, output_path, mode='auto',
                         regions_per_page=None, dpi=RENDER_DPI):
    """去除 PDF 每页水印并保存。

    Args:
        input_path: 输入 PDF
        output_path: 输出 PDF
        mode: 'auto' 自动检测右下角；'manual' 使用 regions_per_page
        regions_per_page: dict {page_index: [(x,y,w,h), ...]}，manual 模式用
                          键为页码（0-based），值为该页的框选区域列表
                          图像坐标系基于 dpi 渲染后的分辨率
        dpi: 渲染 DPI，影响输出清晰度
    """
    doc = fitz.open(input_path)
    try:
        for i, page in enumerate(doc):
            img = render_page_to_image(page, dpi)

            if mode == 'manual' and regions_per_page and i in regions_per_page:
                regions = regions_per_page[i]
                # 注意：regions 是基于预览图像坐标，需要换算到实际渲染分辨率
                # 这里假设调用方已按渲染分辨率传入，否则在 remover.py 中换算
                result = inpaint_regions(img, regions, mode='manual')
            else:
                region = detect_watermark_region(img.shape)
                result = inpaint_region(img, region, mode='auto')

            replace_page_with_image(page, result)

        doc.save(output_path, deflate=True, garbage=4)
    finally:
        doc.close()


def get_page_count(pdf_path):
    """返回 PDF 页数。"""
    doc = fitz.open(pdf_path)
    try:
        return doc.page_count
    finally:
        doc.close()


def render_page_for_preview(pdf_path, page_index, dpi=120):
    """渲染指定页为图像，用于预览（较低 DPI 提速）。"""
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_index]
        return render_page_to_image(page, dpi)
    finally:
        doc.close()
