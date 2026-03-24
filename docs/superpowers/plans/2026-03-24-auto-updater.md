# Auto-Updater Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one-click self-updating via GitHub Releases so the user never manually downloads a new `.exe`.

**Architecture:** A standalone updater module checks the GitHub Releases API on startup, compares versions, and shows an update banner in the main window. On click, it downloads the new exe and launches a batch script to replace itself and restart.

**Tech Stack:** Python stdlib (`urllib.request`, `json`, `subprocess`, `sys`, `os`), PyQt6 (banner widget)

**Spec:** `docs/superpowers/specs/2026-03-24-auto-updater-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `src/assistant/updater.py` | Check GitHub for updates, download exe, trigger replacement |
| `tests/test_updater.py` | Tests for version comparison, API response parsing, skip conditions |

### Modified Files
| File | What Changes |
|------|-------------|
| `src/ui/tray.py` | Add update banner widget to MainWindow, trigger check in run_app() |

---

## Task 1: Updater Module — Version Check

**Files:**
- Create: `src/assistant/updater.py`
- Create: `tests/test_updater.py`

- [ ] **Step 1: Write failing tests for version comparison and API parsing**

```python
# tests/test_updater.py
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from assistant.updater import is_newer_version, parse_release_info, APP_VERSION


def test_newer_version_true():
    assert is_newer_version("v0.3.0", "0.2.0") is True


def test_newer_version_false_same():
    assert is_newer_version("v0.2.0", "0.2.0") is False


def test_newer_version_false_older():
    assert is_newer_version("v0.1.0", "0.2.0") is False


def test_newer_version_patch():
    assert is_newer_version("v0.2.1", "0.2.0") is True


def test_newer_version_major():
    assert is_newer_version("v1.0.0", "0.2.0") is True


def test_newer_version_invalid_tag():
    assert is_newer_version("latest", "0.2.0") is False


def test_parse_release_info():
    api_response = {
        "tag_name": "v0.3.0",
        "assets": [
            {"name": "AI.Assistant.exe", "browser_download_url": "https://example.com/AI.Assistant.exe"},
            {"name": "source.zip", "browser_download_url": "https://example.com/source.zip"},
        ],
    }
    info = parse_release_info(api_response)
    assert info["version"] == "v0.3.0"
    assert info["download_url"] == "https://example.com/AI.Assistant.exe"


def test_parse_release_info_no_exe():
    api_response = {
        "tag_name": "v0.3.0",
        "assets": [
            {"name": "source.zip", "browser_download_url": "https://example.com/source.zip"},
        ],
    }
    info = parse_release_info(api_response)
    assert info is None


def test_app_version_is_string():
    assert isinstance(APP_VERSION, str)
    assert "." in APP_VERSION
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python3 -m pytest tests/test_updater.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'assistant.updater'`

- [ ] **Step 3: Implement updater module — version check and parsing**

```python
# src/assistant/updater.py
"""Auto-updater — checks GitHub Releases for new versions and self-updates."""

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

APP_VERSION = "0.2.1"

GITHUB_API_URL = "https://api.github.com/repos/pewpewgogo/ai-assistant/releases/latest"
EXE_ASSET_NAME = "AI.Assistant.exe"


def is_newer_version(remote_tag: str, local_version: str) -> bool:
    """Compare a GitHub tag (e.g. 'v0.3.0') to a local version (e.g. '0.2.0').

    Returns True if remote is strictly newer.
    """
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", remote_tag)
    if not match:
        return False
    remote = tuple(int(x) for x in match.groups())

    match_local = re.match(r"v?(\d+)\.(\d+)\.(\d+)", local_version)
    if not match_local:
        return False
    local = tuple(int(x) for x in match_local.groups())

    return remote > local


def parse_release_info(api_response: dict) -> Optional[dict]:
    """Extract version and exe download URL from GitHub API response.

    Returns dict with 'version' and 'download_url', or None if no exe asset found.
    """
    tag = api_response.get("tag_name", "")
    assets = api_response.get("assets", [])

    for asset in assets:
        if asset.get("name") == EXE_ASSET_NAME:
            return {
                "version": tag,
                "download_url": asset["browser_download_url"],
            }

    return None


def check_for_update() -> Optional[dict]:
    """Check GitHub for a newer release.

    Returns dict with 'version' and 'download_url' if update available, else None.
    Silently returns None on any error (no internet, rate limit, etc.).
    """
    if not getattr(sys, "frozen", False):
        logger.debug("Not running as frozen exe, skipping update check.")
        return None

    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "ai-assistant"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        info = parse_release_info(data)
        if info and is_newer_version(info["version"], APP_VERSION):
            logger.info("Update available: %s (current: %s)", info["version"], APP_VERSION)
            return info

    except Exception as e:
        logger.debug("Update check failed (this is OK): %s", e)

    return None


def download_and_apply_update(download_url: str, progress_callback=None) -> bool:
    """Download the new exe and launch the replacement batch script.

    Args:
        download_url: URL to download the new exe from
        progress_callback: Optional callable(bytes_downloaded, total_bytes) for progress

    Returns True if the update was initiated (app should exit), False on failure.
    """
    if not getattr(sys, "frozen", False):
        logger.warning("Cannot self-update when not running as frozen exe.")
        return False

    current_exe = Path(sys.executable)
    temp_exe = current_exe.with_name("_update_new.exe")
    batch_path = current_exe.with_name("_update.bat")

    try:
        # Download new exe
        logger.info("Downloading update from %s", download_url)
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "ai-assistant"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(temp_exe, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(downloaded, total)

        logger.info("Download complete: %s (%d bytes)", temp_exe, downloaded)

        # Write batch script
        script = (
            '@echo off\n'
            'timeout /t 2 /nobreak >nul\n'
            f'copy /y "{temp_exe}" "{current_exe}"\n'
            f'del "{temp_exe}"\n'
            f'start "" "{current_exe}"\n'
            'del "%~f0"\n'
        )
        batch_path.write_text(script, encoding="utf-8")

        # Launch batch script and exit
        logger.info("Launching update script: %s", batch_path)
        subprocess.Popen(
            ["cmd.exe", "/c", str(batch_path)],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return True

    except Exception as e:
        logger.exception("Update failed: %s", e)
        # Cleanup temp files on failure
        if temp_exe.exists():
            temp_exe.unlink(missing_ok=True)
        if batch_path.exists():
            batch_path.unlink(missing_ok=True)
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python3 -m pytest tests/test_updater.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/assistant/updater.py tests/test_updater.py
git commit -m "feat: add auto-updater module with version check and download"
```

---

## Task 2: Update Banner in Main Window

**Files:**
- Modify: `src/ui/tray.py` (MainWindow._build_ui and run_app)

- [ ] **Step 1: Add update banner widget to _build_ui()**

In `src/ui/tray.py`, in `MainWindow._build_ui()`, add a hidden update banner as the FIRST widget in the layout (before the status indicator). Insert after `layout.setSpacing(16)` (line ~78):

```python
        # Update banner — hidden by default
        self.update_banner = QWidget()
        self.update_banner.setVisible(False)
        banner_layout = QHBoxLayout(self.update_banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)

        self.update_label = QLabel("")
        self.update_label.setStyleSheet("color: #1e1e2e; font-size: 14px; font-weight: bold;")
        banner_layout.addWidget(self.update_label, stretch=1)

        self.update_btn = QPushButton("Обновить")
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #1e1e2e;"
            "  color: #f9e2af;"
            "  border: none;"
            "  border-radius: 8px;"
            "  padding: 6px 16px;"
            "  font-size: 13px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover { background-color: #313244; }"
        )
        banner_layout.addWidget(self.update_btn)

        self.update_banner.setStyleSheet(
            "background-color: #f9e2af; border-radius: 10px;"
        )
        layout.addWidget(self.update_banner)
```

- [ ] **Step 2: Add show_update_available() and _start_update() methods to MainWindow**

Add these methods to the MainWindow class (after `_on_response`):

```python
    def show_update_available(self, version: str, download_url: str):
        """Show the update banner with version info."""
        self._update_url = download_url
        self.update_label.setText(f"Доступно обновление {version}!")
        self.update_btn.setText("Обновить")
        self.update_btn.setEnabled(True)
        self.update_btn.clicked.connect(self._start_update)
        self.update_banner.setVisible(True)

    def _start_update(self):
        """Download and apply the update."""
        from assistant.updater import download_and_apply_update

        self.update_btn.setEnabled(False)
        self.update_label.setText("Скачивание обновления...")
        self.update_btn.setText("⏳")

        def do_update():
            def on_progress(downloaded, total):
                pct = int(downloaded / total * 100) if total else 0
                # Update label from worker thread via signal
                self.signals.response_received.emit(f"__UPDATE_PROGRESS__{pct}")

            success = download_and_apply_update(self._update_url, progress_callback=on_progress)
            if success:
                import sys
                sys.exit(0)
            else:
                self.signals.response_received.emit("__UPDATE_FAILED__")

        import threading
        threading.Thread(target=do_update, daemon=True).start()
```

- [ ] **Step 3: Handle update progress/failure messages in _on_response**

In `MainWindow._on_response()`, add handling for special update messages at the top of the method:

```python
    def _on_response(self, text: str):
        # Handle update progress messages
        if text.startswith("__UPDATE_PROGRESS__"):
            pct = text.replace("__UPDATE_PROGRESS__", "")
            self.update_label.setText(f"Скачивание обновления... {pct}%")
            return
        if text == "__UPDATE_FAILED__":
            self.update_label.setText("Ошибка загрузки обновления")
            self.update_btn.setText("Повторить")
            self.update_btn.setEnabled(True)
            return

        import html
        clean = html.escape(text)
        self.chat_log.append(
            f'<p style="color:#a6e3a1; font-size:16px; margin:8px 0;">'
            f'🤖 {clean}</p>'
        )
```

- [ ] **Step 4: Trigger update check in run_app()**

In `run_app()`, after `window = MainWindow(engine, settings)` and before the overlay setup, add:

```python
    # Check for updates (non-blocking, runs in background)
    def check_updates():
        from assistant.updater import check_for_update
        result = check_for_update()
        if result:
            # Use signal to safely call UI from background thread
            window.signals.response_received.emit(
                f"__UPDATE_AVAILABLE__{result['version']}||{result['download_url']}"
            )

    import threading
    threading.Thread(target=check_updates, daemon=True).start()
```

- [ ] **Step 5: Handle __UPDATE_AVAILABLE__ in _on_response**

Add one more special message handler in `_on_response` (before the progress handler):

```python
        if text.startswith("__UPDATE_AVAILABLE__"):
            payload = text.replace("__UPDATE_AVAILABLE__", "")
            version, url = payload.split("||", 1)
            self.show_update_available(version, url)
            return
```

- [ ] **Step 6: Verify module compiles**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python3 -c "import sys; sys.path.insert(0, 'src'); from assistant.updater import check_for_update, APP_VERSION; print('updater OK, version:', APP_VERSION)"`

- [ ] **Step 7: Run all tests**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python3 -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/ui/tray.py
git commit -m "feat: add update banner and one-click update to main window"
```

---

## Task 3: Version Bump Discipline

**Files:**
- Modify: `src/assistant/updater.py` (document version sync)

- [ ] **Step 1: Add a comment in updater.py explaining version sync**

At the `APP_VERSION` constant, add a comment:

```python
# IMPORTANT: Update this value when bumping version in pyproject.toml.
# This must match the version in pyproject.toml for update checking to work.
APP_VERSION = "0.2.1"
```

- [ ] **Step 2: Commit**

```bash
git add src/assistant/updater.py
git commit -m "docs: add version sync reminder to updater module"
```

---

## Summary

| Task | Component | Key Files |
|------|-----------|-----------|
| 1 | Updater module — version check, download, apply | `src/assistant/updater.py` |
| 2 | Update banner in main window | `src/ui/tray.py` |
| 3 | Version sync documentation | `src/assistant/updater.py` |
