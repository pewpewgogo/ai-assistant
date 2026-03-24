"""Smoke tests — verify all modules import and basic wiring works."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Mock modules that may not be installed in dev/CI
sys.modules.setdefault("pyautogui", MagicMock())


def test_all_imports():
    from assistant.config import Settings
    from assistant.hotkey import GlobalHotkey
    from actions.executor import execute_actions
    from knowledge.loader import KnowledgeLoader


def test_settings_new_fields():
    from assistant.config import Settings
    s = Settings()
    assert hasattr(s, "hotkey")
    assert hasattr(s, "overlay_enabled")
    assert hasattr(s, "overlay_timeout")
    assert hasattr(s, "overlay_color")
    assert hasattr(s, "default_mode")
    assert hasattr(s, "knowledge_dir")


def test_knowledge_loads_bundled():
    from knowledge.loader import KnowledgeLoader
    loader = KnowledgeLoader(str(Path(__file__).parent.parent / "src" / "knowledge"))
    assert len(loader.sections) > 0


def test_executor_handles_highlight():
    from actions.executor import _run_action
    result = _run_action({
        "action": "highlight",
        "type": "point",
        "x": 100, "y": 200,
        "label": "Test"
    })
    assert result["action"] == "highlight"


def test_system_prompt_has_cnc():
    from assistant.config import Settings
    s = Settings()
    assert "TTC450" in s.system_prompt
    assert "highlight" in s.system_prompt
    assert "Candle" in s.system_prompt
