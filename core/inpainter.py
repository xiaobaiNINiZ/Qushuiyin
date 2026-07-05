"""图像修复（inpaint）封装。

支持两种模式：
- auto: 自动模式，根据水印区域内的文字像素生成 mask，仅修复文字像素
- manual: 手动模式，修复用户框选的整个矩形区域
"""
import cv2
import numpy as np

from .detector import build_watermark_mask


def inpaint_region(image, region, mode='auto', radius=3):
    """修复图像中的水印区域。

    Args:
        image: BGR 图像 (H, W, 3)
        region: (x, y, w, h) 水印区域
        mode: 'auto' 仅修复文字像素；'manual' 修复整个矩形
        radius: inpaint 邻域半径

    Returns:
        np.ndarray: 修复后的 BGR 图像
    """
    h_full, w_full = image.shape[:2]
    full_mask = np.zeros((h_full, w_full), dtype=np.uint8)

    if mode == 'auto':
        full_mask = build_watermark_mask(image, region)
    else:
        x, y, w, h = region
        x = max(0, min(x, w_full))
        y = max(0, min(y, h_full))
        x2 = min(x + w, w_full)
        y2 = min(y + h, h_full)
        full_mask[y:y2, x:x2] = 255

    if full_mask.max() == 0:
        return image.copy()

    return cv2.inpaint(image, full_mask, radius, cv2.INPAINT_TELEA)


def inpaint_regions(image, regions, mode='auto', radius=3):
    """对多个区域依次修复。"""
    result = image.copy()
    for region in regions:
        result = inpaint_region(result, region, mode, radius)
    return result
