"""Global keyboard shortcut listener using pynput."""

import logging
import threading
from typing import Callable, Optional

from pynput import keyboard

logger = logging.getLogger(__name__)

# Map friendly names to pynput keys
KEY_MAP = {
    "f1": keyboard.Key.f1,
    "f2": keyboard.Key.f2,
    "f3": keyboard.Key.f3,
    "f4": keyboard.Key.f4,
    "f5": keyboard.Key.f5,
    "f6": keyboard.Key.f6,
    "f7": keyboard.Key.f7,
    "f8": keyboard.Key.f8,
    "f9": keyboard.Key.f9,
    "f10": keyboard.Key.f10,
    "f11": keyboard.Key.f11,
    "f12": keyboard.Key.f12,
}


class GlobalHotkey:
    """Listens for a global keyboard shortcut and fires a callback."""

    def __init__(self, key_name: str, callback: Callable[[], None]):
        self.key_name = key_name.lower()
        self.callback = callback
        self.is_running = False
        self._listener: Optional[keyboard.Listener] = None
        self._target_key = KEY_MAP.get(self.key_name)

        if self._target_key is None:
            logger.warning("Unknown hotkey '%s', defaulting to F1", key_name)
            self._target_key = keyboard.Key.f1

    def _on_press(self, key) -> None:
        """Called on every key press."""
        try:
            if key == self._target_key:
                logger.info("Hotkey %s pressed", self.key_name)
                self.callback()
        except Exception as e:
            logger.error("Hotkey callback error: %s", e)

    def start(self) -> None:
        """Start listening for the global hotkey in a background thread."""
        if self.is_running:
            return
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()
        self.is_running = True
        logger.info("Global hotkey listener started: %s", self.key_name)

    def stop(self) -> None:
        """Stop the hotkey listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None
        self.is_running = False
        logger.info("Global hotkey listener stopped")
