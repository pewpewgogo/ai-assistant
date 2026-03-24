import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from assistant.config import Settings


def test_default_hotkey():
    s = Settings()
    assert s.hotkey == "f1"


def test_default_overlay_enabled():
    s = Settings()
    assert s.overlay_enabled is True


def test_default_overlay_timeout():
    s = Settings()
    assert s.overlay_timeout == 8


def test_default_overlay_color():
    s = Settings()
    assert s.overlay_color == "#ff6b6b"


def test_default_mode():
    s = Settings()
    assert s.default_mode == "guide"


def test_default_knowledge_dir():
    s = Settings()
    assert s.knowledge_dir == ""
