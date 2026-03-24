import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from actions.executor import _parse_actions, _run_action


def test_parse_highlight_action():
    response = '{"action": "highlight", "type": "point", "x": 100, "y": 200, "label": "Click here"}'
    actions = _parse_actions(response)
    assert len(actions) == 1
    assert actions[0]["action"] == "highlight"
    assert actions[0]["type"] == "point"


def test_run_highlight_returns_data():
    action = {"action": "highlight", "type": "point", "x": 150, "y": 40, "label": "Нажмите сюда"}
    result = _run_action(action)
    assert result is not None
    assert result["action"] == "highlight"
    assert result["type"] == "point"
    assert result["x"] == 150


def test_run_highlight_area():
    action = {"action": "highlight", "type": "area", "x": 50, "y": 50, "w": 200, "h": 100, "label": "Область"}
    result = _run_action(action)
    assert result["type"] == "area"
    assert result["w"] == 200
