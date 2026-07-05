"""扫描全能王水印区域检测。

扫描全能王免费版导出的 PDF/图片会在右下角添加固定位置的水印：
- 宽度约为页面宽度的 1/3
- 高度约为页面高度的 1/14
- 距右下边缘约 1% 边距
"""
import cv2
import numpy as np


def detect_watermark_region(img_shape):
    """根据图像尺寸返回水印默认区域 (x, y, w, h)。

    Args:
        img_shape: 图像形状 (H, W) 或 (H, W, C)

    Returns:
        tuple: (x, y, w, h) 水印区域在原图中的像素坐标
    """
    h, w = img_shape[0], img_shape[1]
    wm_w = int(w * 0.34)
    wm_h = int(h * 0.075)
    margin = max(int(w * 0.01), 4)
    x = w - wm_w - margin
    y = h - wm_h - margin
    return (x, y, wm_w, wm_h)


def build_watermark_mask(image, region):
    """在水印区域内通过阈值分割生成 mask。

    水印文字像素比白色背景暗，用 Otsu 自动阈值分割提取文字像素，
    再做形态学膨胀确保完全覆盖文字边缘。

    Args:
        image: BGR 图像 (H, W, 3)
        region: (x, y, w, h) 水印区域

    Returns:
        np.ndarray: 与 image 同尺寸的 mask，水印像素为 255，其余为 0
    """
    x, y, w, h = region
    h_full, w_full = image.shape[:2]
    x = max(0, min(x, w_full - 1))
    y = max(0, min(y, h_full - 1))
    x2 = min(x + w, w_full)
    y2 = min(y + h, h_full)

    roi = image[y:y2, x:x2]
    if roi.size == 0:
        return np.zeros((h_full, w_full), dtype=np.uint8)

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, local_mask = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    local_mask = cv2.dilate(local_mask, kernel, iterations=2)

    full_mask = np.zeros((h_full, w_full), dtype=np.uint8)
    full_mask[y:y2, x:x2] = local_mask
    return full_mask


def detect_watermark_mask(image):
    """一步到位：返回当前图像的水印 mask。"""
    region = detect_watermark_region(image.shape)
    return build_watermark_mask(image, region), region
