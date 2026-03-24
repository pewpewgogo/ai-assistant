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
from ui.overlay import OverlayWindow
from assistant.hotkey import GlobalHotkey

logger = logging.getLogger(__name__)


class SignalBridge(QObject):
    """Bridge to emit signals from worker threads to the UI thread."""
    state_changed = pyqtSignal(object)
    transcript_received = pyqtSignal(str)
    response_received = pyqtSignal(str)
    highlight_received = pyqtSignal(str, int, int, int, int, str)
    hotkey_pressed = pyqtSignal()


class MainWindow(QMainWindow):
    """Main chat-like window for the assistant."""

    def __init__(self, engine: AssistantEngine, settings: Settings):
        super().__init__()
        self.engine = engine
        self.settings = settings
        self._is_recording = False

        self.setWindowTitle("ЧПУ Помощник")
        self.setMinimumSize(420, 600)
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Status indicator — big, centered
        status_layout = QVBoxLayout()
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_icon = QLabel("\U0001f7e2")
        self.status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_icon.setStyleSheet("font-size: 36px;")
        status_layout.addWidget(self.status_icon)

        self.status_label = QLabel("\u0413\u043e\u0442\u043e\u0432 \u043f\u043e\u043c\u043e\u0447\u044c")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #a6e3a1;"
        )
        status_layout.addWidget(self.status_label)
        layout.addLayout(status_layout)

        # Chat log — large readable text
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setStyleSheet(
            "QTextEdit {"
            "  background-color: #313244;"
            "  color: #cdd6f4;"
            "  border: none;"
            "  border-radius: 12px;"
            "  padding: 14px;"
            "  font-size: 16px;"
            "}"
        )
        layout.addWidget(self.chat_log, stretch=1)

        # Big talk button
        self.listen_btn = QPushButton("\U0001f3a4  \u041d\u0410\u0416\u041c\u0418 \u0427\u0422\u041e\u0411\u042b \u0413\u041e\u0412\u041e\u0420\u0418\u0422\u042c")
        self.listen_btn.setMinimumHeight(70)
        self.listen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.listen_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #89b4fa;"
            "  color: #1e1e2e;"
            "  border: none;"
            "  border-radius: 16px;"
            "  font-size: 22px;"
            "  font-weight: bold;"
            "  padding: 18px;"
            "}"
            "QPushButton:hover { background-color: #74c7ec; }"
            "QPushButton:pressed { background-color: #89dceb; }"
        )
        self.listen_btn.clicked.connect(self._on_listen_clicked)
        layout.addWidget(self.listen_btn)

        # Stop button — smaller, red
        self.stop_btn = QPushButton("\u2b1b  \u0421\u0422\u041e\u041f")
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #f38ba8;"
            "  color: #1e1e2e;"
            "  border: none;"
            "  border-radius: 12px;"
            "  font-size: 16px;"
            "  font-weight: bold;"
            "  padding: 12px;"
            "}"
            "QPushButton:hover { background-color: #eba0ac; }"
        )
        self.stop_btn.clicked.connect(self._on_stop)
        layout.addWidget(self.stop_btn)

        # Settings link — small, at bottom
        settings_btn = QPushButton("\u2699  \u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438")
        settings_btn.setFlat(True)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(
            "QPushButton { color: #6c7086; font-size: 13px; border: none; }"
            "QPushButton:hover { color: #cdd6f4; }"
        )
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Hotkey hint
        hotkey_label = QLabel(f"\u0418\u043b\u0438 \u043d\u0430\u0436\u043c\u0438\u0442\u0435 {self.settings.hotkey.upper()} \u043d\u0430 \u043a\u043b\u0430\u0432\u0438\u0430\u0442\u0443\u0440\u0435")
        hotkey_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hotkey_label.setStyleSheet("color: #585b70; font-size: 12px;")
        layout.addWidget(hotkey_label)

        # Window properties
        self.setWindowTitle("\u0427\u041f\u0423 \u041f\u043e\u043c\u043e\u0449\u043d\u0438\u043a")
        self.setMinimumSize(420, 600)
        self.resize(420, 650)

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self.engine.reload_settings(self.settings)

    def _on_listen_clicked(self):
        if self._is_recording:
            # Stop recording
            self.engine.voice.stop()
            self._is_recording = False
            self.listen_btn.setText("\U0001f3a4  \u041d\u0410\u0416\u041c\u0418 \u0427\u0422\u041e\u0411\u042b \u0413\u041e\u0412\u041e\u0420\u0418\u0422\u042c")
        else:
            # Start recording
            self._is_recording = True
            self.listen_btn.setText("\U0001f534  \u0421\u041b\u0423\u0428\u0410\u042e... (\u043d\u0430\u0436\u043c\u0438 \u0447\u0442\u043e\u0431\u044b \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c)")
            self.engine.listen_and_respond()

    def _on_stop(self):
        self._is_recording = False
        self.engine.stop()
        self.listen_btn.setText("\U0001f3a4  \u041d\u0410\u0416\u041c\u0418 \u0427\u0422\u041e\u0411\u042b \u0413\u041e\u0412\u041e\u0420\u0418\u0422\u042c")

    def _on_state_change(self, state):
        if isinstance(state, str):
            state = AssistantState(state)
        state_map = {
            AssistantState.IDLE: ("\U0001f7e2", "\u0413\u043e\u0442\u043e\u0432 \u043f\u043e\u043c\u043e\u0447\u044c", "#a6e3a1"),
            AssistantState.LISTENING: ("\U0001f7e0", "\u0421\u043b\u0443\u0448\u0430\u044e...", "#fab387"),
            AssistantState.THINKING: ("\U0001f535", "\u0414\u0443\u043c\u0430\u044e...", "#89b4fa"),
            AssistantState.ACTING: ("\U0001f7e1", "\u0412\u044b\u043f\u043e\u043b\u043d\u044f\u044e...", "#f9e2af"),
            AssistantState.SPEAKING: ("\U0001f7e3", "\u0413\u043e\u0432\u043e\u0440\u044e...", "#cba6f7"),
        }
        icon, text, color = state_map.get(state, ("\U0001f7e2", "\u0413\u043e\u0442\u043e\u0432 \u043f\u043e\u043c\u043e\u0447\u044c", "#a6e3a1"))
        self.status_icon.setText(icon)
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")

        # Update button state (uses self._is_recording to match existing __init__)
        if state == AssistantState.IDLE:
            self.listen_btn.setText("\U0001f3a4  \u041d\u0410\u0416\u041c\u0418 \u0427\u0422\u041e\u0411\u042b \u0413\u041e\u0412\u041e\u0420\u0418\u0422\u042c")
            self.listen_btn.setEnabled(True)
            self._is_recording = False
        elif state == AssistantState.LISTENING:
            self.listen_btn.setText("\U0001f534  \u0421\u041b\u0423\u0428\u0410\u042e... (\u043d\u0430\u0436\u043c\u0438 \u0447\u0442\u043e\u0431\u044b \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c)")

    def _on_transcript(self, text: str):
        self.chat_log.append(
            f'<p style="color:#89b4fa; font-size:16px; margin:8px 0;">'
            f'\U0001f5e3 <b>\u0412\u044b:</b> {text}</p>'
        )

    def _on_response(self, text: str):
        import html
        clean = html.escape(text)
        self.chat_log.append(
            f'<p style="color:#a6e3a1; font-size:16px; margin:8px 0;">'
            f'\U0001f916 {clean}</p>'
        )

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    @staticmethod
    def _stylesheet() -> str:
        return """
            QMainWindow {
                background-color: #1e1e2e;
            }
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: Arial, sans-serif;
            }
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

    # Create overlay
    overlay = OverlayWindow(
        timeout=settings.overlay_timeout,
        color=settings.overlay_color,
    )

    # Wire overlay via signal (thread-safe)
    window.signals.highlight_received.connect(
        lambda h_type, x, y, w, h, label: overlay.show_highlight(h_type, x, y, w, h, label)
    )

    def on_highlight(h_type, x, y, w, h, label):
        window.signals.highlight_received.emit(h_type, x, y, w, h, label)

    engine.set_overlay_callback(on_highlight)

    # Wire hotkey via signal (thread-safe)
    window.signals.hotkey_pressed.connect(window._on_listen_clicked)

    def on_hotkey():
        window.signals.hotkey_pressed.emit()

    hotkey = GlobalHotkey(key_name=settings.hotkey, callback=on_hotkey)
    hotkey.start()

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

    def cleanup():
        hotkey.stop()
        overlay.clear()

    app.aboutToQuit.connect(cleanup)

    window.show()
    sys.exit(app.exec())
