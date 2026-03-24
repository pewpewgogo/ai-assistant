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
