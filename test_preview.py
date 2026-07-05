"""预览功能和文件夹拖入测试。"""
import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
app = QApplication(sys.argv)

from app.main_window import MainWindow
from core.detector import detect_watermark_region

window = MainWindow()

# ---------- 测试 1：预览功能 ----------
print("=" * 50)
print("测试 1：预览功能")
print("=" * 50)

test_img = os.path.join(os.path.dirname(__file__), 'test_output', 'test_input.png')
if not os.path.exists(test_img):
    print("[SKIP] 测试图片不存在，先运行 test_core.py")
    sys.exit(0)

window._add_files([test_img])
window.file_list.setCurrentRow(0)

original_image = window.current_preview_image.copy()
print(f"[1.1] 原图已加载，尺寸: {original_image.shape[1]}x{original_image.shape[0]}")
print(f"      is_previewing = {window.is_previewing}")
print(f"      按钮文本 = '{window.btn_preview.text()}'")
print(f"      画布框选启用 = {window.canvas._selection_enabled}")

# 自动模式下点击预览
window._on_toggle_preview()
print(f"\n[1.2] 点击预览后:")
print(f"      is_previewing = {window.is_previewing}")
print(f"      按钮文本 = '{window.btn_preview.text()}'")
print(f"      画布框选启用 = {window.canvas._selection_enabled}")
print(f"      预览结果图非空 = {window.preview_result_image is not None}")

# 验证预览图像的水印区域已变白
region = detect_watermark_region(original_image.shape)
x, y, w, h = region
roi_orig = original_image[y:y+h, x:x+w]
roi_preview = window.preview_result_image[y:y+h, x:x+w]
print(f"      原图水印区域亮度 = {roi_orig.mean():.1f}")
print(f"      预览图水印区域亮度 = {roi_preview.mean():.1f}")
if roi_preview.mean() > roi_orig.mean() + 5:
    print(f"      [OK] 预览成功去除了水印")
else:
    print(f"      [WARN] 预览效果不明显")

# 再次点击恢复原图
window._on_toggle_preview()
print(f"\n[1.3] 恢复原图后:")
print(f"      is_previewing = {window.is_previewing}")
print(f"      按钮文本 = '{window.btn_preview.text()}'")
print(f"      画布框选启用 = {window.canvas._selection_enabled}")

# ---------- 测试 2：文件夹扫描 ----------
print("\n" + "=" * 50)
print("测试 2：文件夹扫描")
print("=" * 50)

# 创建临时文件夹结构
test_dir = os.path.join(os.path.dirname(__file__), 'test_folder')
if os.path.exists(test_dir):
    shutil.rmtree(test_dir)
os.makedirs(os.path.join(test_dir, 'subdir'))

# 复制测试文件到文件夹和子文件夹
shutil.copy2(test_img, os.path.join(test_dir, 'file1.png'))
shutil.copy2(test_img, os.path.join(test_dir, 'subdir', 'file2.png'))
# 创建一个不支持的文件
with open(os.path.join(test_dir, 'readme.txt'), 'w') as f:
    f.write("not supported")

scanned = window._scan_directory(test_dir)
print(f"[2.1] 扫描文件夹: {test_dir}")
print(f"      找到 {len(scanned)} 个支持的文件")
for p in scanned:
    print(f"        - {os.path.basename(p)}")

if len(scanned) == 2:
    print(f"      [OK] 文件夹扫描正确（递归找到 2 个文件，忽略 .txt）")
else:
    print(f"      [FAIL] 期望 2 个文件，实际 {len(scanned)} 个")

# 添加扫描到的文件
window._add_files(scanned)
print(f"\n[2.2] 添加后文件列表项数: {window.file_list.count()}")

# 注意：不在此处删除 test_folder，因为文件还在列表中，
# 切换到这些文件时会因找不到文件而报错。清理放到程序退出后。

# ---------- 测试 3：切换文件退出预览 ----------
print("\n" + "=" * 50)
print("测试 3：切换文件时退出预览")
print("=" * 50)

window.file_list.setCurrentRow(0)
window._on_toggle_preview()
print(f"[3.1] 文件1 进入预览: is_previewing = {window.is_previewing}")

# 切换到第二个文件（test_folder/file1.png）
if window.file_list.count() > 1:
    window.file_list.setCurrentRow(1)
    print(f"[3.2] 切换到文件2: is_previewing = {window.is_previewing}")
    if not window.is_previewing:
        print(f"      [OK] 切换文件后自动退出预览")
    else:
        print(f"      [FAIL] 切换文件后仍在预览模式")

print("\n" + "=" * 50)
print("全部测试完成")
print("=" * 50)

QTimer.singleShot(300, app.quit)
window.show()
app.exec_()

# 程序退出后清理临时文件夹
if os.path.exists(test_dir):
    shutil.rmtree(test_dir)
    print("[清理] 已删除临时测试文件夹")
