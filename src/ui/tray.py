"""System tray application with PyQt6 — Russian UI."""

import logging
import sys

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QCheckBox,
    QSpinBox,
)

from assistant.config import Settings
from assistant.engine import AssistantEngine, AssistantState

logger = logging.getLogger(__name__)

STATE_LABELS = {
    AssistantState.IDLE: "\u0413\u043e\u0442\u043e\u0432",
    AssistantState.LISTENING: "\u0421\u043b\u0443\u0448\u0430\u044e...",
    AssistantState.THINKING: "\u0414\u0443\u043c\u0430\u044e...",
    AssistantState.ACTING: "\u0412\u044b\u043f\u043e\u043b\u043d\u044f\u044e \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044f...",
    AssistantState.SPEAKING: "\u0413\u043e\u0432\u043e\u0440\u044e...",
}


class SignalBridge(QObject):
    """Bridge to emit signals from worker threads to the UI thread."""
    state_changed = pyqtSignal(object)
    transcript_received = pyqtSignal(str)
    response_received = pyqtSignal(str)


class MainWindow(QMainWindow):
    """Main chat-like window for the assistant."""

    def __init__(self, engine: AssistantEngine, settings: Settings):
        super().__init__()
        self.engine = engine
        self.settings = settings
        self._is_recording = False

        self.setWindowTitle("\u0410\u0441\u0441\u0438\u0441\u0442\u0435\u043d\u0442")
        self.setMinimumSize(500, 600)
        self.setStyleSheet(self._stylesheet())

        # Signal bridge for thread-safe UI updates
        self.signals = SignalBridge()
        self.signals.state_changed.connect(self._on_state_change)
        self.signals.transcript_received.connect(self._on_transcript)
        self.signals.response_received.connect(self._on_response)

        engine.set_callbacks(
            on_state_change=lambda s: self.signals.state_changed.emit(s),
            on_transcript=lambda t: self.signals.transcript_received.emit(t),
            on_response=lambda r: self.signals.response_received.emit(r),
        )

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)

        # Top row: status + settings button
        top_row = QHBoxLayout()

        self.status_label = QLabel("\u0413\u043e\u0442\u043e\u0432")
        self.status_label.setObjectName("status")
        top_row.addWidget(self.status_label, stretch=1)

        self.settings_btn = QPushButton("\u2699 \u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438")
        self.settings_btn.setObjectName("settingsBtn")
        self.settings_btn.clicked.connect(self._open_settings)
        top_row.addWidget(self.settings_btn)

        layout.addLayout(top_row)

        # Chat log
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setObjectName("chatLog")
        layout.addWidget(self.chat_log, stretch=1)

        # Controls
        btn_row = QHBoxLayout()

        self.listen_btn = QPushButton("\U0001f3a4 \u041d\u0430\u0436\u043c\u0438\u0442\u0435, \u0447\u0442\u043e\u0431\u044b \u0433\u043e\u0432\u043e\u0440\u0438\u0442\u044c")
        self.listen_btn.setObjectName("listenBtn")
        self.listen_btn.setMinimumHeight(60)
        self.listen_btn.clicked.connect(self._on_listen_clicked)
        btn_row.addWidget(self.listen_btn)

        self.stop_btn = QPushButton("\u0421\u0442\u043e\u043f")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setMinimumHeight(60)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self.stop_btn)

        layout.addLayout(btn_row)

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self.engine.reload_settings(self.settings)

    def _on_listen_clicked(self):
        if self._is_recording:
            # Stop recording
            self.engine.voice.stop()
            self._is_recording = False
            self.listen_btn.setText("\U0001f3a4 \u041d\u0430\u0436\u043c\u0438\u0442\u0435, \u0447\u0442\u043e\u0431\u044b \u0433\u043e\u0432\u043e\u0440\u0438\u0442\u044c")
            self.listen_btn.setStyleSheet("")
        else:
            # Start recording
            self._is_recording = True
            self.listen_btn.setText("\U0001f534 \u041d\u0430\u0436\u043c\u0438\u0442\u0435, \u0447\u0442\u043e\u0431\u044b \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c")
            self.engine.listen_and_respond()

    def _on_stop(self):
        self._is_recording = False
        self.engine.stop()
        self.listen_btn.setText("\U0001f3a4 \u041d\u0430\u0436\u043c\u0438\u0442\u0435, \u0447\u0442\u043e\u0431\u044b \u0433\u043e\u0432\u043e\u0440\u0438\u0442\u044c")

    def _on_state_change(self, state: AssistantState):
        self.status_label.setText(STATE_LABELS.get(state, str(state)))
        if state == AssistantState.IDLE:
            self._is_recording = False
            self.listen_btn.setEnabled(True)
            self.listen_btn.setText("\U0001f3a4 \u041d\u0430\u0436\u043c\u0438\u0442\u0435, \u0447\u0442\u043e\u0431\u044b \u0433\u043e\u0432\u043e\u0440\u0438\u0442\u044c")
        elif state == AssistantState.LISTENING:
            self.listen_btn.setEnabled(True)
            self.listen_btn.setText("\U0001f534 \u041d\u0430\u0436\u043c\u0438\u0442\u0435, \u0447\u0442\u043e\u0431\u044b \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c")
        else:
            self.listen_btn.setEnabled(False)

    def _on_transcript(self, text: str):
        self.chat_log.append(f'<p style="color:#4fc3f7"><b>\u0412\u044b:</b> {text}</p>')

    def _on_response(self, text: str):
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace("\n", "<br>")
        self.chat_log.append(f'<p style="color:#a5d6a7"><b>\u0410\u0441\u0441\u0438\u0441\u0442\u0435\u043d\u0442:</b> {safe}</p>')

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    @staticmethod
    def _stylesheet() -> str:
        return """
            QMainWindow { background: #1e1e2e; }
            QLabel#status {
                color: #cdd6f4; font-size: 14px; font-weight: bold;
                padding: 8px; background: #313244; border-radius: 6px;
            }
            QTextEdit#chatLog {
                background: #181825; color: #cdd6f4; border: 1px solid #313244;
                border-radius: 8px; padding: 12px; font-size: 14px;
            }
            QPushButton#listenBtn {
                background: #89b4fa; color: #1e1e2e; font-size: 18px; font-weight: bold;
                border: none; border-radius: 8px;
            }
            QPushButton#listenBtn:hover { background: #74c7ec; }
            QPushButton#listenBtn:disabled { background: #585b70; color: #6c7086; }
            QPushButton#stopBtn {
                background: #f38ba8; color: #1e1e2e; font-size: 16px; font-weight: bold;
                border: none; border-radius: 8px;
            }
            QPushButton#stopBtn:hover { background: #eba0ac; }
            QPushButton#settingsBtn {
                background: #45475a; color: #cdd6f4; font-size: 13px;
                border: none; border-radius: 6px; padding: 8px 14px;
            }
            QPushButton#settingsBtn:hover { background: #585b70; }
        """


class SettingsDialog(QDialog):
    """\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f."""

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438")
        self.setMinimumWidth(450)
        self.setStyleSheet("""
            QDialog { background: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 13px; }
            QLineEdit, QComboBox, QSpinBox {
                background: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 4px; padding: 6px; font-size: 13px;
            }
            QCheckBox { color: #cdd6f4; font-size: 13px; }
            QPushButton {
                background: #89b4fa; color: #1e1e2e; font-weight: bold;
                border: none; border-radius: 4px; padding: 10px 20px; font-size: 14px;
            }
            QPushButton:hover { background: #74c7ec; }
        """)

        layout = QFormLayout(self)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["openai", "anthropic"])
        self.provider_combo.setCurrentText(settings.ai_provider)
        layout.addRow("\u041f\u0440\u043e\u0432\u0430\u0439\u0434\u0435\u0440 AI:", self.provider_combo)

        self.openai_key = QLineEdit(settings.openai_api_key)
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key.setPlaceholderText("sk-...")
        layout.addRow("OpenAI API \u043a\u043b\u044e\u0447:", self.openai_key)

        self.anthropic_key = QLineEdit(settings.anthropic_api_key)
        self.anthropic_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_key.setPlaceholderText("sk-ant-...")
        layout.addRow("Anthropic API \u043a\u043b\u044e\u0447:", self.anthropic_key)

        self.model_input = QLineEdit(settings.ai_model)
        layout.addRow("\u041c\u043e\u0434\u0435\u043b\u044c:", self.model_input)

        self.tts_check = QCheckBox("\u0412\u043a\u043b\u044e\u0447\u0435\u043d\u043e")
        self.tts_check.setChecked(settings.tts_enabled)
        layout.addRow("\u041e\u0437\u0432\u0443\u0447\u043a\u0430:", self.tts_check)

        self.tts_rate = QSpinBox()
        self.tts_rate.setRange(80, 300)
        self.tts_rate.setValue(settings.tts_rate)
        layout.addRow("\u0421\u043a\u043e\u0440\u043e\u0441\u0442\u044c \u0440\u0435\u0447\u0438:", self.tts_rate)

        save_btn = QPushButton("\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c")
        save_btn.clicked.connect(self._save)
        layout.addRow(save_btn)

    def _save(self):
        self.settings.ai_provider = self.provider_combo.currentText()
        self.settings.openai_api_key = self.openai_key.text().strip()
        self.settings.anthropic_api_key = self.anthropic_key.text().strip()
        self.settings.ai_model = self.model_input.text().strip()
        self.settings.tts_enabled = self.tts_check.isChecked()
        self.settings.tts_rate = self.tts_rate.value()
        self.settings.save()
        self.accept()


def _create_icon() -> QIcon:
    """Create a simple colored icon for the system tray."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#89b4fa"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(4, 4, 56, 56)
    painter.setPen(QColor("#1e1e2e"))
    font = QFont("Arial", 28, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "A")
    painter.end()
    return QIcon(pixmap)


def run_app():
    """Launch the system tray application."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    settings = Settings.load()
    engine = AssistantEngine(settings)
    window = MainWindow(engine, settings)

    # System tray
    icon = _create_icon()
    tray = QSystemTrayIcon(icon, app)

    menu = QMenu()

    show_action = QAction("\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c", tray)
    show_action.triggered.connect(window.show)
    menu.addAction(show_action)

    settings_action = QAction("\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438", tray)
    settings_action.triggered.connect(window._open_settings)
    menu.addAction(settings_action)

    menu.addSeparator()

    quit_action = QAction("\u0412\u044b\u0445\u043e\u0434", tray)
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: window.show()
        if reason == QSystemTrayIcon.ActivationReason.Trigger
        else None
    )
    tray.show()

    window.show()
    sys.exit(app.exec())
