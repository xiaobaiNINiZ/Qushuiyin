"""图片文件的加载、保存和水印去除。"""
import os

import cv2
import numpy as np

from .detector import detect_watermark_region
from .inpainter import inpaint_region, inpaint_regions

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}


def is_image_file(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def load_image(path):
    """加载图片为 BGR ndarray。"""
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"无法加载图片: {path}")
    return img


def save_image(image, path):
    """保存 BGR 图片，支持中文路径。"""
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext or '.png', image)
    if not ok:
        raise ValueError(f"无法保存图片: {path}")
    buf.tofile(path)


def remove_image_watermark(input_path, output_path, mode='auto', regions=None):
    """去除图片水印并保存。

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        mode: 'auto' 自动检测右下角水印；'manual' 使用 regions 框选
        regions: manual 模式下的框选区域列表 [(x, y, w, h), ...]
    """
    image = load_image(input_path)

    if mode == 'manual':
        if not regions:
            raise ValueError("手动模式需要提供 regions")
        result = inpaint_regions(image, regions, mode='manual')
    else:
        region = detect_watermark_region(image.shape)
        result = inpaint_region(image, region, mode='auto')

    save_image(result, output_path)
    return result
