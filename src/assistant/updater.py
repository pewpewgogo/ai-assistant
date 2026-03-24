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

# IMPORTANT: Update this value when bumping version in pyproject.toml.
# This must match the version in pyproject.toml for update checking to work.
APP_VERSION = "0.3.1"

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
