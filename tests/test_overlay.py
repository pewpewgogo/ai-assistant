# tests/test_overlay.py
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Build proper mock modules for PyQt6 so that class inheritance works
_qt_core = MagicMock()
_qt_gui = MagicMock()
_qt_widgets = MagicMock()
_pyqt6 = MagicMock()


# QWidget needs to be a real class so OverlayWindow can inherit from it
class _FakeQWidget:
    def __init__(self, *args, **kwargs):
        pass

    def setWindowFlags(self, *a):
        pass

    def setAttribute(self, *a):
        pass

    def setGeometry(self, *a):
        pass

    def show(self):
        pass

    def hide(self):
        pass

    def update(self):
        pass


_qt_widgets.QWidget = _FakeQWidget
_qt_widgets.QApplication = MagicMock()

sys.modules["PyQt6"] = _pyqt6
sys.modules["PyQt6.QtCore"] = _qt_core
sys.modules["PyQt6.QtGui"] = _qt_gui
sys.modules["PyQt6.QtWidgets"] = _qt_widgets

from ui.overlay import OverlayWindow


def _make_overlay():
    """Create an OverlayWindow instance without calling __init__."""
    obj = object.__new__(OverlayWindow)
    obj._highlights = []
    return obj


def test_overlay_import():
    """Test that overlay module can be imported."""
    assert OverlayWindow is not None


def test_highlight_data():
    """Test highlight data structure without creating a real window."""
    overlay = _make_overlay()
    overlay._add_highlight("point", 100, 200, 0, 0, "Test")
    assert len(overlay._highlights) == 1
    assert overlay._highlights[0]["type"] == "point"
    assert overlay._highlights[0]["x"] == 100
    assert overlay._highlights[0]["y"] == 200
    assert overlay._highlights[0]["label"] == "Test"


def test_clear_highlights():
    """Test clearing highlights."""
    overlay = _make_overlay()
    overlay._add_highlight("point", 100, 200, 0, 0, "Test")
    overlay._highlights.clear()
    assert len(overlay._highlights) == 0
