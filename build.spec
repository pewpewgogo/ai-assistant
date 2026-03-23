# PyInstaller spec file for AI Assistant
# Run: pyinstaller build.spec

import sys
from pathlib import Path

block_cipher = None
src_path = str(Path("src"))

a = Analysis(
    [str(Path("src") / "assistant" / "main.py")],
    pathex=[src_path],
    binaries=[],
    datas=[
        ("assets", "assets"),
    ],
    hiddenimports=[
        "pyttsx3.drivers",
        "pyttsx3.drivers.sapi5",
        "sounddevice",
        "numpy",
        "mss",
        "mss.windows",
        "pyautogui",
        "pyautogui._pyautogui_win",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AI Assistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add .ico path here for custom icon
)
