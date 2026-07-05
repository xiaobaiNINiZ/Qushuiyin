"""后台处理线程，避免批量处理时界面冻结。"""
import os

from PyQt5.QtCore import QThread, pyqtSignal

from core.remover import remove_watermark, get_output_path


class BatchWorker(QThread):
    """批量自动去水印工作线程。

    信号:
        progress(int current, int total, str filename): 进度更新
        fileDone(str input_path, str output_path): 单个文件完成
        fileFailed(str input_path, str error): 单个文件失败
        allDone(int success, int failed): 全部完成
    """

    progress = pyqtSignal(int, int, str)
    fileDone = pyqtSignal(str, str)
    fileFailed = pyqtSignal(str, str)
    allDone = pyqtSignal(int, int)

    def __init__(self, file_paths, output_dir, mode='auto'):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir
        self.mode = mode
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        success = 0
        failed = 0
        total = len(self.file_paths)

        for i, path in enumerate(self.file_paths, 1):
            if self._cancel:
                break

            filename = os.path.basename(path)
            self.progress.emit(i, total, filename)

            try:
                output_path = get_output_path(path, self.output_dir)
                remove_watermark(path, output_path, mode=self.mode)
                self.fileDone.emit(path, output_path)
                success += 1
            except Exception as e:
                self.fileFailed.emit(path, str(e))
                failed += 1

        self.allDone.emit(success, failed)
