from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.engine import analyze_text


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Keil报错诊断器")
        self.resize(1180, 720)
        self.last_feedback_text = ""

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout()
        layout = QHBoxLayout()

        left_box = QVBoxLayout()
        center_box = QVBoxLayout()
        right_box = QVBoxLayout()

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            "把 Keil 编译输出完整粘贴到这里。\n\n"
            "建议直接复制 Build Output 全部内容，不要只截一小段。"
        )

        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)

        self.tip_edit = QTextEdit()
        self.tip_edit.setReadOnly(True)
        self.tip_edit.setPlainText(
            "使用建议：\n"
            "1. 先粘贴完整编译输出\n"
            "2. 重点只看第一条 error\n"
            "3. 不要一上来就处理后面一长串连带报错\n"
            "4. 修完第一条后重新编译，再看新的第一条错误\n"
            "5. 如果准备求助，优先复制“求助文本”发给学长或群里\n"
        )

        analyze_button = QPushButton("开始分析")
        analyze_button.clicked.connect(self.handle_analyze)

        copy_button = QPushButton("复制诊断结果")
        copy_button.clicked.connect(self.handle_copy)

        copy_feedback_button = QPushButton("复制求助文本")
        copy_feedback_button.clicked.connect(self.handle_copy_feedback)

        clear_button = QPushButton("清空")
        clear_button.clicked.connect(self.handle_clear)

        left_box.addWidget(QLabel("输入区"))
        left_box.addWidget(self.input_edit)
        left_box.addWidget(analyze_button)

        center_box.addWidget(QLabel("诊断结果"))
        center_box.addWidget(self.result_edit)
        center_box.addWidget(copy_button)
        center_box.addWidget(copy_feedback_button)

        right_box.addWidget(QLabel("使用提示"))
        right_box.addWidget(self.tip_edit)
        right_box.addWidget(clear_button)

        layout.addLayout(left_box, 4)
        layout.addLayout(center_box, 4)
        layout.addLayout(right_box, 2)

        root.addLayout(layout)
        central.setLayout(root)

    def handle_analyze(self) -> None:
        text = self.input_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "请先粘贴 Keil 编译输出。")
            return

        result = analyze_text(text)
        self.result_edit.setPlainText(result["report"])
        self.last_feedback_text = result.get("feedback_text", "")

    def handle_copy(self) -> None:
        text = self.result_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "当前没有可复制的诊断结果。")
            return

        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "提示", "诊断结果已复制。")

    def handle_copy_feedback(self) -> None:
        if not self.last_feedback_text.strip():
            QMessageBox.information(self, "提示", "请先完成一次分析，再复制求助文本。")
            return

        QApplication.clipboard().setText(self.last_feedback_text)
        QMessageBox.information(self, "提示", "求助文本已复制，可以直接发给学长或群里。")

    def handle_clear(self) -> None:
        self.input_edit.clear()
        self.result_edit.clear()
        self.last_feedback_text = ""
