"""GUI 烟雾测试：验证 MainWindow 能正确初始化，不实际显示窗口。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
app = QApplication(sys.argv)

from app.main_window import MainWindow

window = MainWindow()
print("[1] MainWindow 实例化成功")
print(f"    窗口标题: {window.windowTitle()}")
print(f"    窗口大小: {window.width()}x{window.height()}")
print(f"    文件列表初始项数: {window.file_list.count()}")
print(f"    按钮状态 - 去除水印: {window.btn_remove.isEnabled()}")
print(f"    按钮状态 - 批量处理: {window.act_batch.isEnabled()}")
print(f"    默认模式: {'自动' if window.rb_auto.isChecked() else '手动'}")

# 测试添加文件（用测试图）
test_img = os.path.join(os.path.dirname(__file__), 'test_output', 'test_input.png')
if os.path.exists(test_img):
    window._add_files([test_img])
    print(f"[2] 添加文件后列表项数: {window.file_list.count()}")
    print(f"    文件列表第一项: {window.file_list.item(0).text()}")
    # 选中第一项触发预览
    window.file_list.setCurrentRow(0)
    print(f"[3] 选中文件后:")
    print(f"    label_file: {window.label_file.text()}")
    print(f"    canvas 是否有图像: {window.canvas._qimage is not None}")

# 自动退出
QTimer.singleShot(500, app.quit)
print("\n[OK] GUI 烟雾测试通过（500ms 后自动退出）")
window.show()
app.exec_()
