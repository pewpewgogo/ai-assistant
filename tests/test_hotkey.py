import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_hotkey_import():
    from assistant.hotkey import GlobalHotkey
    assert GlobalHotkey is not None


def test_hotkey_callback_stored():
    from assistant.hotkey import GlobalHotkey
    callback = MagicMock()
    hk = GlobalHotkey(key_name="f1", callback=callback)
    assert hk.callback is callback
    assert hk.key_name == "f1"


def test_hotkey_start_stop():
    from assistant.hotkey import GlobalHotkey
    callback = MagicMock()
    hk = GlobalHotkey(key_name="f1", callback=callback)
    hk.start()
    assert hk.is_running
    hk.stop()
    assert not hk.is_running
