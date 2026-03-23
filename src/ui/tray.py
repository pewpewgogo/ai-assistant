"""System tray application with PyQt6."""

import logging
import sys

from PyQt6.QtCore import QSize, Qt, pyqtSignal, QObject
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
    AssistantState.IDLE: "Ready",
    AssistantState.LISTENING: "Listening...",
    AssistantState.THINKING: "Thinking...",
    AssistantState.ACTING: "Performing actions...",
    AssistantState.SPEAKING: "Speaking...",
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

        self.setWindowTitle("AI Assistant")
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

        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        # Chat log
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setObjectName("chatLog")
        layout.addWidget(self.chat_log, stretch=1)

        # Controls
        btn_row = QHBoxLayout()

        self.listen_btn = QPushButton("Hold to Talk")
        self.listen_btn.setObjectName("listenBtn")
        self.listen_btn.setMinimumHeight(50)
        self.listen_btn.pressed.connect(self._on_listen_pressed)
        btn_row.addWidget(self.listen_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.clicked.connect(self.engine.stop)
        btn_row.addWidget(self.stop_btn)

        layout.addLayout(btn_row)

    def _on_listen_pressed(self):
        self.engine.listen_and_respond()

    def _on_state_change(self, state: AssistantState):
        self.status_label.setText(STATE_LABELS.get(state, str(state)))
        is_busy = state != AssistantState.IDLE
        self.listen_btn.setEnabled(not is_busy)

    def _on_transcript(self, text: str):
        self.chat_log.append(f'<p style="color:#4fc3f7"><b>You:</b> {text}</p>')

    def _on_response(self, text: str):
        # Escape HTML but preserve newlines
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace("\n", "<br>")
        self.chat_log.append(f'<p style="color:#a5d6a7"><b>Assistant:</b> {safe}</p>')

    def closeEvent(self, event):
        # Minimize to tray instead of closing
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
                border-radius: 8px; padding: 12px; font-size: 13px;
            }
            QPushButton#listenBtn {
                background: #89b4fa; color: #1e1e2e; font-size: 16px; font-weight: bold;
                border: none; border-radius: 8px;
            }
            QPushButton#listenBtn:hover { background: #74c7ec; }
            QPushButton#listenBtn:disabled { background: #585b70; color: #6c7086; }
            QPushButton#stopBtn {
                background: #f38ba8; color: #1e1e2e; font-size: 14px; font-weight: bold;
                border: none; border-radius: 8px;
            }
            QPushButton#stopBtn:hover { background: #eba0ac; }
        """


class SettingsDialog(QDialog):
    """Settings dialog for API keys and configuration."""

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)
        self.setStyleSheet("""
            QDialog { background: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QLineEdit, QComboBox, QSpinBox {
                background: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 4px; padding: 6px;
            }
            QCheckBox { color: #cdd6f4; }
            QPushButton {
                background: #89b4fa; color: #1e1e2e; font-weight: bold;
                border: none; border-radius: 4px; padding: 8px 16px;
            }
            QPushButton:hover { background: #74c7ec; }
        """)

        layout = QFormLayout(self)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["openai", "anthropic"])
        self.provider_combo.setCurrentText(settings.ai_provider)
        layout.addRow("AI Provider:", self.provider_combo)

        self.openai_key = QLineEdit(settings.openai_api_key)
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key.setPlaceholderText("sk-...")
        layout.addRow("OpenAI API Key:", self.openai_key)

        self.anthropic_key = QLineEdit(settings.anthropic_api_key)
        self.anthropic_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_key.setPlaceholderText("sk-ant-...")
        layout.addRow("Anthropic API Key:", self.anthropic_key)

        self.model_input = QLineEdit(settings.ai_model)
        layout.addRow("Model:", self.model_input)

        self.tts_check = QCheckBox("Enabled")
        self.tts_check.setChecked(settings.tts_enabled)
        layout.addRow("Text-to-Speech:", self.tts_check)

        self.tts_rate = QSpinBox()
        self.tts_rate.setRange(80, 300)
        self.tts_rate.setValue(settings.tts_rate)
        layout.addRow("TTS Rate:", self.tts_rate)

        save_btn = QPushButton("Save")
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

    show_action = QAction("Show", tray)
    show_action.triggered.connect(window.show)
    menu.addAction(show_action)

    settings_action = QAction("Settings", tray)

    def open_settings():
        dlg = SettingsDialog(settings, window)
        if dlg.exec():
            engine.reload_settings(settings)

    settings_action.triggered.connect(open_settings)
    menu.addAction(settings_action)

    menu.addSeparator()

    quit_action = QAction("Quit", tray)
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
