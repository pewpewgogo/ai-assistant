# Auto-Updater Design Spec

**Date:** 2026-03-24
**Status:** Draft
**Goal:** Add automatic update checking and one-click self-replacement so the user never needs to manually download a new `.exe`.

---

## Context

The app is distributed as a single `AI.Assistant.exe` via GitHub Releases. Currently the user must manually visit the releases page and re-download each time. The target user is a basic PC user who should not need to do this.

## Design

### Update Check (on startup)

1. On app startup, call GitHub API: `GET https://api.github.com/repos/pewpewgogo/ai-assistant/releases/latest`
2. Parse the `tag_name` field (e.g. `v0.3.0`) and compare to the current app version
3. The current version is stored as a constant in the updater module, matching `pyproject.toml`
4. If the remote version is newer, show an update banner in the main window
5. If no internet, API fails, or rate limited — silently skip, no error shown to user

### Update Banner (UI)

A yellow/gold banner at the top of the main window:
- Text: "Доступно обновление vX.Y.Z! [Обновить]"
- "Обновить" is a clickable button
- Banner is hidden by default, shown only when an update is available
- Non-intrusive — does not block usage of the app

### Update Process (on click)

When the user clicks "Обновить":

1. Banner text changes to "Скачивание обновления..." (download in progress)
2. Download the `.exe` asset from the release to a temp file next to the current exe
3. Write a small batch script (`_update.bat`) next to the current exe that:
   - Waits 2 seconds for the current process to exit
   - Copies the new exe over the current exe
   - Starts the new exe
   - Deletes itself and the temp file
4. Launch the batch script
5. Exit the current app

### Batch Script Template

```bat
@echo off
timeout /t 2 /nobreak >nul
copy /y "{temp_exe_path}" "{current_exe_path}"
del "{temp_exe_path}"
start "" "{current_exe_path}"
del "%~f0"
```

### Skip Conditions

The updater should not run when:
- The app is not running as a bundled `.exe` (i.e. `sys.frozen` is not set) — this means running from source during development
- No internet connection
- GitHub API returns an error or rate limit

### Error Handling

- Network errors during check → silently skip
- Network errors during download → show "Ошибка загрузки обновления" in banner, keep current version running
- File write errors → show error in banner, keep current version running
- All errors are logged but never crash the app

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/assistant/updater.py` | New | Update checker and downloader |
| `src/ui/tray.py` | Modify | Add update banner to MainWindow, trigger check on startup |
| `build.spec` | No change | No new dependencies or data files needed |

## Not In Scope

- Automatic background checking (only on startup)
- Delta updates or patching (full exe replacement)
- Rollback to previous version
- Update channel selection (always uses latest release)
- Linux/macOS update mechanism (Windows-only via batch script)
