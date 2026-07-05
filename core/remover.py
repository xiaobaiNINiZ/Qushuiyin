"""去水印主流程编排：根据文件类型分发到 image_io 或 pdf_io。"""
import os

from .image_io import is_image_file, remove_image_watermark
from .pdf_io import is_pdf_file, remove_pdf_watermark, RENDER_DPI


def get_output_path(input_path, output_dir, suffix='_no_watermark'):
    """生成输出路径：原名 + 后缀 + 原扩展名。"""
    name, ext = os.path.splitext(os.path.basename(input_path))
    return os.path.join(output_dir, f"{name}{suffix}{ext}")


def remove_watermark(input_path, output_path, mode='auto',
                     regions=None, regions_per_page=None):
    """统一入口：去除文件水印。

    Args:
        input_path: 输入文件路径（图片或 PDF）
        output_path: 输出文件路径
        mode: 'auto' 自动检测；'manual' 使用 regions
        regions: 图片手动模式的框选区域 [(x,y,w,h), ...]
        regions_per_page: PDF 手动模式的逐页框选 {page_idx: [(x,y,w,h), ...]}
                          区域坐标基于预览 DPI 的图像，函数内部会换算到渲染 DPI

    Returns:
        str: 输出文件路径
    """
    if is_pdf_file(input_path):
        # PDF 手动模式：预览用低 DPI，处理用高 DPI，需要换算坐标
        if mode == 'manual' and regions_per_page:
            preview_dpi = 120  # 与 main_window 预览一致
            scale = RENDER_DPI / preview_dpi
            scaled_regions = {}
            for page_idx, page_regions in regions_per_page.items():
                scaled_regions[page_idx] = [
                    (int(x * scale), int(y * scale),
                     int(w * scale), int(h * scale))
                    for (x, y, w, h) in page_regions
                ]
            remove_pdf_watermark(input_path, output_path, mode='manual',
                                 regions_per_page=scaled_regions)
        else:
            remove_pdf_watermark(input_path, output_path, mode='auto')
    elif is_image_file(input_path):
        remove_image_watermark(input_path, output_path, mode=mode,
                               regions=regions)
    else:
        raise ValueError(f"不支持的文件类型: {input_path}")

    return output_path
