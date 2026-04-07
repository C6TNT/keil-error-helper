from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from core.ai_client import (
        AIClientError,
        ai_is_configured,
        run_ai_analysis,
        test_ai_connection,
    )
    from core.config_store import (
        DEFAULT_BASE_URL,
        DEFAULT_MODEL,
        load_ai_config,
        mask_api_key,
        save_ai_config,
    )
    from core.engine import analyze_text
except ModuleNotFoundError:
    from ..core.ai_client import (
        AIClientError,
        ai_is_configured,
        run_ai_analysis,
        test_ai_connection,
    )
    from ..core.config_store import (
        DEFAULT_BASE_URL,
        DEFAULT_MODEL,
        load_ai_config,
        mask_api_key,
        save_ai_config,
    )
    from ..core.engine import analyze_text


SAMPLE_ERRORS = {
    "示例1：函数参数个数不匹配": {
        "scene": "display",
        "text": "App\\app.c(128): error C208: '_SEG_SetCode': too many actual parameters",
    },
    "示例2：标识符未定义": {
        "scene": "page",
        "text": "App\\app.c(88): error C206: 'page_id': undefined identifier",
    },
    "示例3：头文件语法错误": {
        "scene": "display",
        "text": "BSP\\bsp_seg.h(36): error C141: syntax error near ')'",
    },
    "示例4：结构体里用了 bit": {
        "scene": "param",
        "text": "App\\app.c(18): error C150: 'pwm_enable': bit member in struct/union",
    },
    "示例5：Keil 控制参数错误": {
        "scene": "freq",
        "text": "C51 FATAL-ERROR -\n  ACTION:  PARSING INVOKE-/#PRAGMA-LINE\n  LINE:    D:\\Keil_v5\\C51\\BIN\\C51.EXE main.c OPTIMIZE(8,SPEED) BROWSE .\\\n  ERROR:   UNKNOWN CONTROL",
    },
}


class AIAnalysisWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, payload_json: str) -> None:
        super().__init__()
        self.payload_json = payload_json

    def run(self) -> None:
        try:
            text = run_ai_analysis(self.payload_json)
            self.succeeded.emit(text)
        except AIClientError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"AI 分析过程中发生未预期异常：{exc}")


class AITestWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def run(self) -> None:
        try:
            text = test_ai_connection()
            self.succeeded.emit(text)
        except AIClientError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"连接测试过程中发生未预期异常：{exc}")


class AISettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI 设置")
        self.resize(540, 240)

        config = load_ai_config()

        self.api_key_edit = QLineEdit(config.get("api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("在这里粘贴 API Key")

        self.base_url_edit = QLineEdit(config.get("base_url", DEFAULT_BASE_URL))
        self.base_url_edit.setPlaceholderText(DEFAULT_BASE_URL)

        self.model_edit = QLineEdit(config.get("model", DEFAULT_MODEL))
        self.model_edit.setPlaceholderText(DEFAULT_MODEL)

        form = QFormLayout()
        form.addRow("API Key", self.api_key_edit)
        form.addRow("Base URL", self.base_url_edit)
        form.addRow("Model", self.model_edit)

        tip = QLabel(
            "说明：配置会保存在当前应用目录下的 config.json。\n"
            "推荐新生直接在这里设置，不需要再打开 PowerShell。"
        )
        tip.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.handle_save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(tip)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def handle_save(self) -> None:
        save_ai_config(
            self.api_key_edit.text(),
            self.base_url_edit.text(),
            self.model_edit.text(),
        )
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Keil 报错诊断器")
        self.resize(1380, 820)
        self.last_feedback_text = ""
        self.last_ai_preview = ""
        self.last_ai_payload_json = ""
        self.ai_worker = None
        self.ai_test_worker = None

        central = QWidget()
        self.setCentralWidget(central)
        self._apply_styles()

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
        self.input_edit.setMinimumHeight(260)

        self.code_edit = QTextEdit()
        self.code_edit.setPlaceholderText(
            "补充代码片段（可选）\n\n"
            "如果你愿意，可以把报错附近的函数、变量定义或调用位置一起贴进来。\n"
            "这样 AI 深入分析会更准确。"
        )
        self.code_edit.setMaximumHeight(160)

        self.scene_combo = QComboBox()
        self.scene_combo.addItem("未选择", "none")
        self.scene_combo.addItem("页面", "page")
        self.scene_combo.addItem("按键", "key")
        self.scene_combo.addItem("参数", "param")
        self.scene_combo.addItem("温度", "temp")
        self.scene_combo.addItem("频率", "freq")
        self.scene_combo.addItem("超声波", "ultra")
        self.scene_combo.addItem("显示", "display")

        self.sample_combo = QComboBox()
        self.sample_combo.addItem("未选择示例", "")
        for sample_name in SAMPLE_ERRORS:
            self.sample_combo.addItem(sample_name, sample_name)

        self.priority_label = QLabel("先修第一条错误")
        self.priority_label.setObjectName("priorityTitle")
        self.priority_text = QTextEdit()
        self.priority_text.setReadOnly(True)
        self.priority_text.setMaximumHeight(76)
        self.priority_text.setObjectName("priorityBox")

        self.card_error = QTextEdit()
        self.card_error.setReadOnly(True)
        self.card_error.setMaximumHeight(92)
        self.card_error.setObjectName("cardBox")

        self.card_type = QTextEdit()
        self.card_type.setReadOnly(True)
        self.card_type.setMaximumHeight(92)
        self.card_type.setObjectName("cardBox")

        self.card_checks = QTextEdit()
        self.card_checks.setReadOnly(True)
        self.card_checks.setMaximumHeight(92)
        self.card_checks.setObjectName("cardBox")

        self.card_next = QTextEdit()
        self.card_next.setReadOnly(True)
        self.card_next.setMaximumHeight(92)
        self.card_next.setObjectName("cardBox")

        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setObjectName("resultBox")

        self.ai_status_label = QLabel()
        self.ai_status_label.setObjectName("fieldTitle")
        self.ai_edit = QTextEdit()
        self.ai_edit.setReadOnly(True)
        self.ai_edit.setObjectName("aiBox")

        self.tip_edit = QTextEdit()
        self.tip_edit.setReadOnly(True)
        self.tip_edit.setObjectName("tipBox")
        self.tip_edit.setPlainText(
            "使用建议：\n"
            "1. 先粘贴完整编译输出\n"
            "2. 重点只看第一条 error\n"
            "3. 不要一上来就处理后面一长串连带报错\n"
            "4. 修完第一条后重新编译，再看新的第一条错误\n"
            "5. 如果准备求助，优先复制“求助文本”发给学长或群里\n"
            "6. AI 功能推荐先在“AI 设置”里填好 Key 再使用\n"
            "7. 如果不确定配得对不对，先点“测试连接”"
        )

        self.analyze_button = QPushButton("开始分析")
        self.analyze_button.clicked.connect(self.handle_analyze)

        self.load_sample_button = QPushButton("载入示例")
        self.load_sample_button.clicked.connect(self.handle_load_sample)

        self.copy_button = QPushButton("复制诊断结果")
        self.copy_button.clicked.connect(self.handle_copy)

        self.copy_feedback_button = QPushButton("复制求助文本")
        self.copy_feedback_button.clicked.connect(self.handle_copy_feedback)

        self.ai_button = QPushButton("AI 深入分析")
        self.ai_button.clicked.connect(self.handle_ai_analysis)

        self.ai_settings_button = QPushButton("AI 设置")
        self.ai_settings_button.clicked.connect(self.handle_open_ai_settings)

        self.ai_test_button = QPushButton("测试连接")
        self.ai_test_button.clicked.connect(self.handle_test_ai_connection)

        self.copy_ai_button = QPushButton("复制 AI 内容")
        self.copy_ai_button.clicked.connect(self.handle_copy_ai)

        self.clear_button = QPushButton("清空")
        self.clear_button.clicked.connect(self.handle_clear)

        input_title = QLabel("输入区")
        input_title.setObjectName("sectionTitle")
        scene_title = QLabel("我现在在改什么")
        scene_title.setObjectName("fieldTitle")
        sample_title = QLabel("示例报错")
        sample_title.setObjectName("fieldTitle")
        code_title = QLabel("补充代码片段（可选）")
        code_title.setObjectName("fieldTitle")
        result_title = QLabel("诊断结果")
        result_title.setObjectName("sectionTitle")
        ai_title = QLabel("AI 深入分析")
        ai_title.setObjectName("sectionTitle")
        tip_title = QLabel("使用提示")
        tip_title.setObjectName("sectionTitle")

        left_box.addWidget(input_title)
        left_box.addWidget(scene_title)
        left_box.addWidget(self.scene_combo)
        left_box.addWidget(sample_title)
        left_box.addWidget(self.sample_combo)
        left_box.addWidget(self.load_sample_button)
        left_box.addWidget(self.input_edit)
        left_box.addWidget(code_title)
        left_box.addWidget(self.code_edit)
        left_box.addWidget(self.analyze_button)

        center_box.addWidget(self.priority_label)
        center_box.addWidget(self.priority_text)

        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(12)
        cards_layout.setVerticalSpacing(10)
        cards_layout.addWidget(self._make_card_title("第一条错误"), 0, 0)
        cards_layout.addWidget(self._make_card_title("这是什么问题"), 0, 1)
        cards_layout.addWidget(self.card_error, 1, 0)
        cards_layout.addWidget(self.card_type, 1, 1)
        cards_layout.addWidget(self._make_card_title("先看哪 3 个地方"), 2, 0)
        cards_layout.addWidget(self._make_card_title("下一步先做什么"), 2, 1)
        cards_layout.addWidget(self.card_checks, 3, 0)
        cards_layout.addWidget(self.card_next, 3, 1)

        center_box.addWidget(result_title)
        center_box.addLayout(cards_layout)
        center_box.addWidget(self.result_edit)
        center_box.addWidget(self.copy_button)
        center_box.addWidget(self.copy_feedback_button)

        ai_button_row = QHBoxLayout()
        ai_button_row.addWidget(self.ai_button)
        ai_button_row.addWidget(self.ai_settings_button)
        ai_button_row.addWidget(self.ai_test_button)
        ai_button_row.addWidget(self.copy_ai_button)

        right_box.addWidget(ai_title)
        right_box.addWidget(self.ai_status_label)
        right_box.addWidget(self.ai_edit)
        right_box.addLayout(ai_button_row)
        right_box.addWidget(tip_title)
        right_box.addWidget(self.tip_edit)
        right_box.addWidget(self.clear_button)

        layout.addLayout(left_box, 4)
        layout.addLayout(center_box, 5)
        layout.addLayout(right_box, 3)

        root.addLayout(layout)
        central.setLayout(root)
        self.refresh_ai_status()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f6f8fb;
            }
            QLabel#sectionTitle {
                font-size: 18px;
                font-weight: 700;
                color: #17324d;
                padding: 4px 0 6px 0;
            }
            QLabel#fieldTitle {
                font-size: 13px;
                font-weight: 600;
                color: #35516d;
                padding-top: 4px;
            }
            QLabel#cardTitle {
                font-size: 13px;
                font-weight: 700;
                color: #24476b;
                padding: 2px 0;
            }
            QLabel#priorityTitle {
                font-size: 15px;
                font-weight: 800;
                color: #8a3b12;
                padding: 2px 0 4px 0;
            }
            QTextEdit, QComboBox, QLineEdit {
                background: #ffffff;
                color: #1f2f3f;
                border: 1px solid #cfd8e3;
                border-radius: 10px;
                padding: 8px;
                font-size: 13px;
                selection-background-color: #1f6feb;
                selection-color: #ffffff;
            }
            QLineEdit {
                color: #1f2f3f;
            }
            QLineEdit[echoMode="2"] {
                color: #1f2f3f;
            }
            QTextEdit#priorityBox {
                background: #fff1e8;
                border: 1px solid #f3c8a6;
                border-radius: 12px;
                color: #6a3314;
                font-size: 13px;
                font-weight: 700;
            }
            QTextEdit#cardBox {
                background: #eef5ff;
                border: 1px solid #bdd3f2;
                border-radius: 12px;
                color: #18324d;
                font-size: 13px;
                font-weight: 600;
            }
            QTextEdit#resultBox {
                background: #ffffff;
                border: 1px solid #cfd8e3;
                border-radius: 12px;
                color: #1f2f3f;
            }
            QTextEdit#aiBox {
                background: #eefaf3;
                border: 1px solid #bfe4cb;
                border-radius: 12px;
                color: #173b28;
            }
            QTextEdit#tipBox {
                background: #fff8e8;
                border: 1px solid #f0d79a;
                border-radius: 12px;
                color: #5a4611;
            }
            QPushButton {
                background: #1f6feb;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 9px 14px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #185cc0;
            }
            QPushButton:pressed {
                background: #134895;
            }
            """
        )

    def _make_card_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("cardTitle")
        return label

    def refresh_ai_status(self) -> None:
        config = load_ai_config()
        self.ai_status_label.setText(
            f"当前 AI 配置：Key={mask_api_key(config.get('api_key', ''))} | "
            f"Model={config.get('model', DEFAULT_MODEL) or DEFAULT_MODEL}"
        )
        if ai_is_configured():
            self.ai_edit.setPlaceholderText(
                "这里会显示 AI 深入分析结果。\n"
                "当前已经配置好 API Key，可以直接使用 AI。"
            )
        else:
            self.ai_edit.setPlaceholderText(
                "这里会显示 AI 深入分析结果。\n"
                "当前还没配置 API Key，建议先点“AI 设置”。"
            )

    def handle_analyze(self) -> None:
        text = self.input_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "请先粘贴 Keil 编译输出。")
            return

        self.analyze_button.setEnabled(False)
        self.analyze_button.setText("分析中...")
        QApplication.processEvents()

        try:
            code_snippet = self.code_edit.toPlainText().strip()
            result = analyze_text(text, self.scene_combo.currentData(), code_snippet)
            self.priority_label.setText(result.get("priority_level", "先修第一条错误"))
            self.priority_text.setPlainText(result.get("priority_text", ""))
            self.card_error.setPlainText(result.get("card_error", ""))
            self.card_type.setPlainText(result.get("card_type", ""))
            self.card_checks.setPlainText(result.get("card_checks", ""))
            self.card_next.setPlainText(result.get("card_next", ""))
            self.result_edit.setPlainText(result.get("report", ""))
            self.last_feedback_text = result.get("feedback_text", "")
            self.last_ai_preview = result.get("ai_preview", "")
            self.last_ai_payload_json = result.get("ai_payload_json", "")

            if ai_is_configured():
                self.ai_edit.setPlainText(
                    "当前已经整理好 AI 输入。\n"
                    "如果你补充了报错附近代码，AI 会一起参考。\n"
                    "如果你想拿到更深入的解释和排查建议，可以点下面的“AI 深入分析”。"
                )
            else:
                self.ai_edit.setPlainText(
                    "当前已经整理好 AI 输入，但你还没有在应用里配置 API Key。\n"
                    "如果你补充了报错附近代码，后面 AI 预览里也会一起带上。\n"
                    "现在点“AI 深入分析”会先展示结构化预览，建议先去“AI 设置”里补配置。"
                )
        except Exception as exc:
            error_message = (
                "开始分析时发生异常，请把下面这段信息反馈给学长：\n\n"
                f"{type(exc).__name__}: {exc}"
            )
            self.priority_label.setText("分析过程中发生异常")
            self.priority_text.setPlainText("工具已经捕获到异常，请先复制报错信息反馈。")
            self.card_error.setPlainText("开始分析时发生异常")
            self.card_type.setPlainText(type(exc).__name__)
            self.card_checks.setPlainText("先看输入内容是否完整，再把异常信息反馈出来。")
            self.card_next.setPlainText("复制异常信息，反馈给维护者继续修复。")
            self.result_edit.setPlainText(error_message)
            self.last_feedback_text = error_message
            self.last_ai_preview = ""
            self.last_ai_payload_json = ""
            self.ai_edit.setPlainText("分析阶段出现异常，已停止 AI 深入分析。")
            QMessageBox.critical(self, "分析异常", error_message)
        finally:
            self.analyze_button.setEnabled(True)
            self.analyze_button.setText("开始分析")

    def handle_load_sample(self) -> None:
        sample_name = self.sample_combo.currentData()
        if not sample_name:
            QMessageBox.information(self, "提示", "请先选择一个示例报错。")
            return

        sample = SAMPLE_ERRORS.get(sample_name)
        if not sample:
            QMessageBox.information(self, "提示", "当前示例不存在，请重新选择。")
            return

        self.input_edit.setPlainText(str(sample["text"]))
        self.code_edit.clear()
        scene_value = str(sample["scene"])
        index = self.scene_combo.findData(scene_value)
        if index >= 0:
            self.scene_combo.setCurrentIndex(index)
        QMessageBox.information(self, "提示", "示例报错已载入，现在可以直接点“开始分析”。")

    def handle_open_ai_settings(self) -> None:
        dialog = AISettingsDialog(self)
        if dialog.exec():
            self.refresh_ai_status()
            QMessageBox.information(self, "提示", "AI 配置已保存。后面直接双击 exe 就能继续使用。")

    def handle_test_ai_connection(self) -> None:
        if not ai_is_configured():
            QMessageBox.information(self, "提示", "请先在“AI 设置”里填好 API Key、Base URL 和 Model。")
            return

        self.ai_test_button.setEnabled(False)
        self.ai_test_button.setText("测试中...")
        self.ai_edit.setPlainText("正在测试 AI 连接，请稍等几秒...")

        self.ai_test_worker = AITestWorker()
        self.ai_test_worker.succeeded.connect(self.handle_ai_test_success)
        self.ai_test_worker.failed.connect(self.handle_ai_test_failure)
        self.ai_test_worker.finished.connect(self.handle_ai_test_finished)
        self.ai_test_worker.start()

    def handle_ai_test_success(self, text: str) -> None:
        self.ai_edit.setPlainText(text)

    def handle_ai_test_failure(self, message: str) -> None:
        self.ai_edit.setPlainText(message)

    def handle_ai_test_finished(self) -> None:
        self.ai_test_button.setEnabled(True)
        self.ai_test_button.setText("测试连接")
        self.ai_test_worker = None

    def handle_ai_analysis(self) -> None:
        if not self.last_ai_preview.strip():
            QMessageBox.information(self, "提示", "请先完成一次分析，再使用 AI 深入分析。")
            return

        if not ai_is_configured():
            self.ai_edit.setPlainText(
                "当前还没有在应用里配置 API Key，所以暂时无法调用真实 AI。\n\n"
                "你现在看到的是 AI 预览输入，后续接入模型时就会把下面这些内容发给 AI。\n\n"
                f"{self.last_ai_preview}"
            )
            return

        self.ai_button.setEnabled(False)
        self.ai_button.setText("AI 正在分析...")
        self.ai_edit.setPlainText("AI 正在分析，请稍等几秒...")

        self.ai_worker = AIAnalysisWorker(self.last_ai_payload_json)
        self.ai_worker.succeeded.connect(self.handle_ai_success)
        self.ai_worker.failed.connect(self.handle_ai_failure)
        self.ai_worker.finished.connect(self.handle_ai_finished)
        self.ai_worker.start()

    def handle_ai_success(self, text: str) -> None:
        self.ai_edit.setPlainText(text)

    def handle_ai_failure(self, message: str) -> None:
        self.ai_edit.setPlainText(message)

    def handle_ai_finished(self) -> None:
        self.ai_button.setEnabled(True)
        self.ai_button.setText("AI 深入分析")
        self.ai_worker = None

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

    def handle_copy_ai(self) -> None:
        ai_text = self.ai_edit.toPlainText().strip()
        if not ai_text:
            QMessageBox.information(self, "提示", "当前没有可复制的 AI 内容。")
            return

        QApplication.clipboard().setText(ai_text)
        QMessageBox.information(self, "提示", "AI 内容已复制。")

    def handle_clear(self) -> None:
        self.input_edit.clear()
        self.code_edit.clear()
        self.priority_label.setText("先修第一条错误")
        self.priority_text.clear()
        self.card_error.clear()
        self.card_type.clear()
        self.card_checks.clear()
        self.card_next.clear()
        self.result_edit.clear()
        self.ai_edit.clear()
        self.last_feedback_text = ""
        self.last_ai_preview = ""
        self.last_ai_payload_json = ""
        self.refresh_ai_status()
