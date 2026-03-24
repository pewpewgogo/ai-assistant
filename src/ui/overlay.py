"""Transparent fullscreen overlay for visual guidance highlights."""

import logging
from typing import List

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt6.QtWidgets import QWidget, QApplication

logger = logging.getLogger(__name__)


class OverlayWindow(QWidget):
    """Transparent, click-through fullscreen overlay that draws highlights."""

    def __init__(self, timeout: int = 8, color: str = "#ff6b6b"):
        super().__init__()
        self._highlights: List[dict] = []
        self._opacity = 1.0
        self._color = QColor(color)
        self._timeout = timeout

        # Frameless, transparent, always on top, click-through
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Cover full primary screen
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        # Pulse animation timer
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_direction = -0.05

        # Auto-dismiss timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.clear)

    def _add_highlight(self, highlight_type: str, x: int, y: int,
                       w: int = 0, h: int = 0, label: str = "") -> None:
        """Add a highlight to the list."""
        self._highlights.append({
            "type": highlight_type,
            "x": x, "y": y, "w": w, "h": h,
            "label": label,
        })

    def show_highlight(self, highlight_type: str, x: int, y: int,
                       w: int = 0, h: int = 0, label: str = "") -> None:
        """Show a highlight on screen."""
        self._add_highlight(highlight_type, x, y, w, h, label)
        self._opacity = 1.0
        self.show()
        self.update()

        # Start pulse animation
        if not self._pulse_timer.isActive():
            self._pulse_timer.start(50)

        # Reset auto-dismiss
        self._dismiss_timer.stop()
        self._dismiss_timer.start(self._timeout * 1000)

    def clear(self) -> None:
        """Clear all highlights and hide."""
        self._highlights.clear()
        self._pulse_timer.stop()
        self._dismiss_timer.stop()
        self.hide()
        self.update()

    def _pulse(self) -> None:
        """Animate highlight opacity for pulsing effect."""
        self._opacity += self._pulse_direction
        if self._opacity <= 0.4:
            self._pulse_direction = 0.05
        elif self._opacity >= 1.0:
            self._pulse_direction = -0.05
        self.update()

    def paintEvent(self, event) -> None:
        """Draw all highlights."""
        if not self._highlights:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for h in self._highlights:
            if h["type"] == "point":
                self._draw_point(painter, h)
            elif h["type"] == "area":
                self._draw_area(painter, h)
            elif h["type"] == "steps":
                self._draw_step(painter, h)
            elif h["type"] == "tooltip":
                self._draw_tooltip(painter, h)

        painter.end()

    def _draw_point(self, painter: QPainter, h: dict) -> None:
        """Draw a pulsing circle with arrow and label."""
        color = QColor(self._color)
        color.setAlphaF(self._opacity)

        # Outer circle
        pen = QPen(color, 3)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        radius = 25
        painter.drawEllipse(QPointF(h["x"], h["y"]), radius, radius)

        # Glow
        glow = QColor(self._color)
        glow.setAlphaF(self._opacity * 0.3)
        painter.setPen(QPen(glow, 6))
        painter.drawEllipse(QPointF(h["x"], h["y"]), radius + 4, radius + 4)

        # Label below
        if h["label"]:
            self._draw_label(painter, h["x"], h["y"] + radius + 20, h["label"])

    def _draw_area(self, painter: QPainter, h: dict) -> None:
        """Draw a pulsing rectangle border with label."""
        color = QColor(self._color)
        color.setAlphaF(self._opacity)

        pen = QPen(color, 3)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        rect = QRectF(h["x"], h["y"], h["w"], h["h"])
        painter.drawRoundedRect(rect, 8, 8)

        # Glow
        glow = QColor(self._color)
        glow.setAlphaF(self._opacity * 0.3)
        painter.setPen(QPen(glow, 6))
        painter.drawRoundedRect(rect.adjusted(-3, -3, 3, 3), 10, 10)

        # Label below rect
        if h["label"]:
            self._draw_label(painter, h["x"] + h["w"] / 2, h["y"] + h["h"] + 20, h["label"])

    def _draw_step(self, painter: QPainter, h: dict) -> None:
        """Draw a numbered step circle."""
        color = QColor(self._color)
        color.setAlphaF(self._opacity)

        # Filled circle with number
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(h["x"], h["y"]), 16, 16)

        # Number text
        painter.setPen(QPen(QColor("#1e1e2e"), 1))
        font = QFont("Arial", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(h["x"] - 16, h["y"] - 16, 32, 32),
                         Qt.AlignmentFlag.AlignCenter, h["label"])

    def _draw_tooltip(self, painter: QPainter, h: dict) -> None:
        """Draw a floating text label."""
        if h["label"]:
            self._draw_label(painter, h["x"], h["y"], h["label"])

    def _draw_label(self, painter: QPainter, x: float, y: float, text: str) -> None:
        """Draw a label with background at the given position."""
        font = QFont("Arial", 13, QFont.Weight.Bold)
        painter.setFont(font)

        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()
        padding = 10

        bg_rect = QRectF(
            x - text_width / 2 - padding,
            y - text_height / 2 - padding / 2,
            text_width + padding * 2,
            text_height + padding,
        )

        # Background
        bg_color = QColor(self._color)
        bg_color.setAlphaF(self._opacity * 0.2)
        painter.setPen(QPen(QColor(self._color), 2))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(bg_rect, 8, 8)

        # Text
        text_color = QColor("#ffffff")
        text_color.setAlphaF(self._opacity)
        painter.setPen(QPen(text_color, 1))
        painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, text)
