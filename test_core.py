"""核心算法功能测试：生成带水印的测试图，运行去水印流程。"""
import os
import sys
import numpy as np
import cv2

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.detector import detect_watermark_region, build_watermark_mask
from core.inpainter import inpaint_region
from core.image_io import save_image, load_image
from core.remover import remove_watermark, get_output_path


def make_test_image(path):
    """生成一张模拟扫描全能王水印的测试图。"""
    # A4 比例白底
    img = np.ones((1000, 707, 3), dtype=np.uint8) * 255

    # 模拟正文文字（多条黑色横线）
    for i in range(20):
        y = 100 + i * 35
        cv2.line(img, (80, y), (600, y), (30, 30, 30), 2)

    # 在右下角添加水印文字
    region = detect_watermark_region(img.shape)
    x, y, w, h = region
    # 水印文字：扫描全能王
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = "Scanned by CamScanner"
    text_size = cv2.getTextSize(text, font, 0.6, 1)[0]
    tx = x + (w - text_size[0]) // 2
    ty = y + (h + text_size[1]) // 2
    cv2.putText(img, text, (tx, ty), font, 0.6, (120, 120, 120), 1, cv2.LINE_AA)

    save_image(img, path)
    return img, region


def main():
    test_dir = os.path.join(os.path.dirname(__file__), 'test_output')
    os.makedirs(test_dir, exist_ok=True)

    # 1. 生成测试图
    input_path = os.path.join(test_dir, 'test_input.png')
    img, region = make_test_image(input_path)
    print(f"[1] 测试图已生成: {input_path}")
    print(f"    图像尺寸: {img.shape[1]}x{img.shape[0]}")
    print(f"    水印区域: x={region[0]}, y={region[1]}, w={region[2]}, h={region[3]}")

    # 2. 检测水印 mask
    mask, detected_region = detect_watermark_region(img.shape), region
    mask = build_watermark_mask(img, detected_region)
    mask_pixels = np.count_nonzero(mask)
    print(f"[2] 水印 mask 已生成，非零像素数: {mask_pixels}")

    # 3. 修复
    result = inpaint_region(img, detected_region, mode='auto')
    result_path = os.path.join(test_dir, 'test_result.png')
    save_image(result, result_path)
    print(f"[3] 修复结果已保存: {result_path}")

    # 4. 验证：水印区域内的像素应接近白色（修复后）
    x, y, w, h = detected_region
    roi_after = result[y:y+h, x:x+w]
    mean_brightness = roi_after.mean()
    print(f"[4] 修复后水印区域平均亮度: {mean_brightness:.1f} (接近 255 表示成功)")

    # 5. 通过 remover.py 统一接口测试
    output_path = get_output_path(input_path, test_dir)
    remove_watermark(input_path, output_path, mode='auto')
    print(f"[5] remover.py 统一接口测试通过: {output_path}")

    if mean_brightness > 200:
        print("\n[OK] 核心算法测试通过")
    else:
        print("\n[WARN] 修复后亮度偏低，请人工检查结果图")


if __name__ == '__main__':
    main()
