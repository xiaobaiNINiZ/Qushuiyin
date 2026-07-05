"""PDF 处理测试：生成带水印的测试 PDF，运行去水印流程。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz
import cv2
import numpy as np

from core.pdf_io import (remove_pdf_watermark, get_page_count,
                          render_page_for_preview, RENDER_DPI)
from core.detector import detect_watermark_region


def make_test_pdf(path, pages=2):
    """生成一个带扫描全能王风格水印的测试 PDF。"""
    doc = fitz.open()
    for p in range(pages):
        # A4 尺寸（点）
        page = doc.new_page(width=595, height=842)
        # 白色背景
        page.draw_rect(page.rect, color=(1, 1, 1), fill=(1, 1, 1))
        # 模拟正文（多条横线）
        for i in range(15):
            y = 100 + i * 30
            page.draw_line(fitz.Point(80, y), fitz.Point(500, y),
                           color=(0.1, 0.1, 0.1), width=1)
        # 在右下角添加水印文字（深灰色，模拟扫描全能王水印）
        # 水印区域按 PDF 点坐标计算（与 detect_watermark_region 比例一致）
        w_pt = 595 * 0.34
        h_pt = 842 * 0.075
        margin = 595 * 0.01
        x_pt = 595 - w_pt - margin
        y_pt = 842 - h_pt - margin
        text_x = x_pt + 10
        text_y = y_pt + h_pt / 2 + 5
        page.insert_text(fitz.Point(text_x, text_y),
                         "Scanned by CamScanner",
                         fontsize=12, color=(0.2, 0.2, 0.2))
    doc.save(path)
    doc.close()
    return path


def main():
    test_dir = os.path.join(os.path.dirname(__file__), 'test_output')
    os.makedirs(test_dir, exist_ok=True)

    # 1. 生成测试 PDF
    input_pdf = os.path.join(test_dir, 'test_input.pdf')
    make_test_pdf(input_pdf, pages=2)
    print(f"[1] 测试 PDF 已生成: {input_pdf}")
    print(f"    页数: {get_page_count(input_pdf)}")

    # 2. 渲染第一页预览，检查水印可见
    preview = render_page_for_preview(input_pdf, 0, dpi=120)
    print(f"[2] 预览图尺寸: {preview.shape[1]}x{preview.shape[0]}")
    region = detect_watermark_region(preview.shape)
    print(f"    水印区域: {region}")

    # 检查水印区域是否有非白色像素（即水印存在）
    x, y, w, h = region
    roi = preview[y:y+h, x:x+w]
    has_watermark = (roi.mean() < 250)
    print(f"    水印区域平均亮度（处理前）: {roi.mean():.1f}")
    print(f"    是否检测到水印: {has_watermark}")

    # 3. 去水印
    output_pdf = os.path.join(test_dir, 'test_input_no_watermark.pdf')
    remove_pdf_watermark(input_pdf, output_pdf, mode='auto')
    print(f"[3] 去水印完成: {output_pdf}")

    # 4. 验证：渲染处理后的 PDF，检查水印区域是否变白
    preview_after = render_page_for_preview(output_pdf, 0, dpi=120)
    region_after = detect_watermark_region(preview_after.shape)
    x, y, w, h = region_after
    roi_after = preview_after[y:y+h, x:x+w]
    mean_after = roi_after.mean()
    print(f"[4] 处理后水印区域平均亮度: {mean_after:.1f} (接近 255 表示成功)")

    if mean_after > 240:
        print("\n[OK] PDF 处理测试通过")
    else:
        print("\n[WARN] 修复后亮度偏低，请人工检查")


if __name__ == '__main__':
    main()
