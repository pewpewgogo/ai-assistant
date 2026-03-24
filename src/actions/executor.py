"""Action executor - translates AI action commands into desktop automation."""

import json
import logging
import subprocess
import sys
import time
from typing import Union

import pyautogui

logger = logging.getLogger(__name__)

# Safety: small pause between actions, move duration for clicks
pyautogui.PAUSE = 0.3
pyautogui.FAILSAFE = True  # move mouse to corner to abort


def execute_actions(response_text: str) -> list:
    """Parse AI response for action blocks and execute them.

    Returns a list of result descriptions for each action executed.
    """
    actions = _parse_actions(response_text)
    if not actions:
        return []

    results = []
    for action in actions:
        try:
            result = _run_action(action)
            results.append(result)
        except Exception as e:
            msg = f"Action failed: {action.get('action', '?')} - {e}"
            logger.error(msg)
            results.append(msg)

    return results


def _parse_actions(text: str) -> list[dict]:
    """Extract JSON action objects from the AI response text."""
    # Try to find JSON array or object in the response
    text = text.strip()

    # Look for ```json blocks first
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "action" in parsed:
            return [parsed]
    except json.JSONDecodeError:
        pass

    # Try to find inline JSON objects
    actions = []
    i = 0
    while i < len(text):
        if text[i] == "{":
            depth = 0
            start = i
            for j in range(i, len(text)):
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(text[start : j + 1])
                            if "action" in obj:
                                actions.append(obj)
                        except json.JSONDecodeError:
                            pass
                        i = j
                        break
        i += 1

    return actions


def _run_action(action: dict) -> Union[str, dict]:
    """Execute a single action dict."""
    act = action.get("action", "")

    if act == "click":
        x, y = int(action["x"]), int(action["y"])
        pyautogui.click(x, y)
        return f"Clicked at ({x}, {y})"

    elif act == "double_click":
        x, y = int(action["x"]), int(action["y"])
        pyautogui.doubleClick(x, y)
        return f"Double-clicked at ({x}, {y})"

    elif act == "right_click":
        x, y = int(action["x"]), int(action["y"])
        pyautogui.rightClick(x, y)
        return f"Right-clicked at ({x}, {y})"

    elif act == "type":
        text = action["text"]
        pyautogui.typewrite(text, interval=0.03) if text.isascii() else pyautogui.write(text)
        return f"Typed: {text[:50]}..."

    elif act == "hotkey":
        keys = action["keys"]
        pyautogui.hotkey(*keys)
        return f"Pressed hotkey: {'+'.join(keys)}"

    elif act == "scroll":
        x = int(action.get("x", 0))
        y = int(action.get("y", 0))
        clicks = int(action.get("clicks", 3))
        pyautogui.scroll(clicks, x, y)
        return f"Scrolled {clicks} at ({x}, {y})"

    elif act == "open":
        target = action["target"]
        if sys.platform == "win32":
            subprocess.Popen(["start", "", target], shell=True)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        return f"Opened: {target}"

    elif act == "wait":
        seconds = float(action.get("seconds", 1))
        time.sleep(seconds)
        return f"Waited {seconds}s"

    elif act == "highlight":
        logger.info("Highlight: type=%s x=%s y=%s label=%s",
                     action.get("type"), action.get("x"), action.get("y"), action.get("label"))
        return {
            "action": "highlight",
            "type": action.get("type", "point"),
            "x": action.get("x", 0),
            "y": action.get("y", 0),
            "w": action.get("w", 0),
            "h": action.get("h", 0),
            "label": action.get("label", ""),
        }

    else:
        return f"Unknown action: {act}"
