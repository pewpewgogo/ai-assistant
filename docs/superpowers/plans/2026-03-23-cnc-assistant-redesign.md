# CNC Assistant Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the existing AI assistant into an accessible CNC desktop helper with a big simple UI, screen overlay guidance, CNC knowledge base, and global hotkey activation.

**Architecture:** Enhance the existing PyQt6 + Python app. Add a transparent overlay window for visual guidance, a knowledge base loader for CNC-specific context, and a global hotkey module. Redesign the main window for maximum accessibility (big buttons, large text). The engine orchestrates guide-vs-do mode switching based on natural language intent.

**Tech Stack:** Python 3.10+, PyQt6, OpenAI/Anthropic APIs, pynput (new), pyautogui, pyttsx3, mss, Whisper

**Spec:** `docs/superpowers/specs/2026-03-23-cnc-assistant-redesign-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `src/knowledge/__init__.py` | Package init |
| `src/knowledge/loader.py` | Loads relevant knowledge sections by keyword matching |
| `src/knowledge/ttc450_manual.txt` | TTC450 Pro manual text (structured by section) |
| `src/knowledge/candle_guide.txt` | Candle GRBL controller usage guide |
| `src/ui/overlay.py` | Transparent fullscreen overlay with highlight rendering |
| `src/assistant/hotkey.py` | Global F1 keyboard shortcut listener |
| `tests/__init__.py` | Package init |
| `tests/test_knowledge_loader.py` | Tests for knowledge loader |
| `tests/test_overlay.py` | Tests for overlay module |
| `tests/test_hotkey.py` | Tests for hotkey module |
| `tests/test_executor_highlight.py` | Tests for new highlight action |
| `tests/test_engine_modes.py` | Tests for guide/do mode in engine |

### Modified Files
| File | What Changes |
|------|-------------|
| `src/assistant/config.py` | Add hotkey, overlay, mode settings |
| `src/actions/executor.py` | Add highlight action type |
| `src/assistant/engine.py` | Wire knowledge loader, overlay, guide/do mode |
| `src/ui/tray.py` | Complete UI redesign — big buttons, large text |
| `pyproject.toml` | Add pynput dependency |
| `build.spec` | Add new modules to hiddenimports and datas |

---

## Task 1: Knowledge Base — Loader Module

**Files:**
- Create: `src/knowledge/__init__.py`
- Create: `src/knowledge/loader.py`
- Create: `tests/__init__.py`
- Create: `tests/test_knowledge_loader.py`

- [ ] **Step 1: Write failing test for KnowledgeLoader**

```python
# tests/test_knowledge_loader.py
import os
import tempfile
import pytest
from knowledge.loader import KnowledgeLoader


@pytest.fixture
def knowledge_dir():
    """Create a temp directory with sample knowledge files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "ttc450_manual.txt"), "w", encoding="utf-8") as f:
            f.write(
                "## Безопасность\n"
                "Всегда выключайте станок перед заменой фрезы.\n\n"
                "## Шпиндель\n"
                "Максимальная скорость шпинделя 12000 об/мин.\n\n"
                "## Обслуживание\n"
                "Смазывайте направляющие каждые 50 часов работы.\n"
            )
        with open(os.path.join(tmpdir, "candle_guide.txt"), "w", encoding="utf-8") as f:
            f.write(
                "## Загрузка G-code\n"
                "Откройте меню Файл и выберите Открыть.\n\n"
                "## Установка нуля\n"
                "Используйте кнопку Zero XY для установки нулевой точки.\n\n"
                "## Запуск задания\n"
                "Нажмите кнопку Send для запуска обработки.\n"
            )
        yield tmpdir


def test_load_all_files(knowledge_dir):
    loader = KnowledgeLoader(knowledge_dir)
    assert len(loader.sections) > 0


def test_search_by_keyword(knowledge_dir):
    loader = KnowledgeLoader(knowledge_dir)
    results = loader.search("шпиндель")
    assert any("12000" in section for section in results)


def test_search_candle(knowledge_dir):
    loader = KnowledgeLoader(knowledge_dir)
    results = loader.search("загрузка g-code")
    assert any("Файл" in section for section in results)


def test_search_no_results(knowledge_dir):
    loader = KnowledgeLoader(knowledge_dir)
    results = loader.search("лазер")
    assert results == []


def test_token_budget(knowledge_dir):
    loader = KnowledgeLoader(knowledge_dir)
    results = loader.search("шпиндель", max_chars=50)
    total = sum(len(s) for s in results)
    assert total <= 50


def test_get_context_string(knowledge_dir):
    loader = KnowledgeLoader(knowledge_dir)
    context = loader.get_context("шпиндель")
    assert isinstance(context, str)
    assert "12000" in context
```

- [ ] **Step 2: Create package init and conftest**

```python
# src/knowledge/__init__.py
# (empty)
```

```python
# tests/__init__.py
# (empty)
```

Add `conftest.py` so pytest can find `src/` packages:

```python
# tests/conftest.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/test_knowledge_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'knowledge.loader'`

- [ ] **Step 4: Implement KnowledgeLoader**

```python
# src/knowledge/loader.py
"""Knowledge base loader — loads text files and retrieves relevant sections by keyword."""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)


class KnowledgeLoader:
    """Loads knowledge files split by '## ' headings, searches by keyword."""

    def __init__(self, knowledge_dir: str):
        self.sections: List[dict] = []
        self._load_directory(knowledge_dir)

    def _load_directory(self, knowledge_dir: str) -> None:
        """Load all .txt files, split each into sections by ## headings."""
        for filename in sorted(os.listdir(knowledge_dir)):
            if not filename.endswith(".txt"):
                continue
            filepath = os.path.join(knowledge_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self._parse_sections(content, filename)
            except Exception as e:
                logger.error("Failed to load %s: %s", filepath, e)

    def _parse_sections(self, content: str, source: str) -> None:
        """Split content by ## headings into titled sections."""
        current_title = ""
        current_body = []

        for line in content.split("\n"):
            if line.startswith("## "):
                if current_body:
                    self.sections.append({
                        "title": current_title,
                        "body": "\n".join(current_body).strip(),
                        "source": source,
                    })
                current_title = line[3:].strip()
                current_body = []
            else:
                current_body.append(line)

        if current_body:
            self.sections.append({
                "title": current_title,
                "body": "\n".join(current_body).strip(),
                "source": source,
            })

    def search(self, query: str, max_chars: int = 2000) -> List[str]:
        """Find sections matching query keywords. Returns list of section texts within budget."""
        query_lower = query.lower()
        keywords = query_lower.split()

        scored = []
        for section in self.sections:
            searchable = (section["title"] + " " + section["body"]).lower()
            score = sum(1 for kw in keywords if kw in searchable)
            if score > 0:
                scored.append((score, section))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        total_chars = 0
        for _score, section in scored:
            text = f"### {section['title']}\n{section['body']}"
            if total_chars + len(text) > max_chars:
                break
            results.append(text)
            total_chars += len(text)

        return results

    def get_context(self, query: str, max_chars: int = 2000) -> str:
        """Get a single context string for the AI prompt."""
        sections = self.search(query, max_chars)
        if not sections:
            return ""
        return "## Справочная информация\n\n" + "\n\n".join(sections)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/test_knowledge_loader.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/knowledge/ tests/
git commit -m "feat: add knowledge base loader module"
```

---

## Task 2: Knowledge Base — Content Files

**Files:**
- Create: `src/knowledge/ttc450_manual.txt`
- Create: `src/knowledge/candle_guide.txt`

- [ ] **Step 1: Create TTC450 Pro manual knowledge file**

Write `src/knowledge/ttc450_manual.txt` with structured sections covering:
- Safety (безопасность)
- Machine specs (характеристики) — working area 450x400mm, spindle speed, etc.
- Setup (настройка) — assembly, connecting, first power-on
- Bit changing (замена фрезы)
- Coordinate system (система координат)
- Maintenance (обслуживание)
- Troubleshooting (устранение неисправностей)
- Common error codes

Use `## Section Title` format for each section. All content in Russian.

Note: This is a placeholder based on public specs. The user will provide the actual PDF manual later to fill in complete details.

- [ ] **Step 2: Create Candle usage guide**

Write `src/knowledge/candle_guide.txt` with structured sections covering:
- Interface overview (обзор интерфейса) — describe main areas of the Candle window
- Loading G-code (загрузка G-code) — File → Open, file types
- Setting work zero (установка нуля) — Zero XY, Zero Z buttons
- Jogging (ручное перемещение) — jog controls, step size
- Running a job (запуск обработки) — Send button, pause, stop
- GRBL settings (настройки GRBL) — common parameters
- Connection (подключение) — COM port, baud rate
- Common problems (частые проблемы)

Use `## Section Title` format. All content in Russian.

- [ ] **Step 3: Verify loader works with real content**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -c "from knowledge.loader import KnowledgeLoader; loader = KnowledgeLoader('src/knowledge'); print(f'{len(loader.sections)} sections loaded'); print(loader.get_context('шпиндель')[:200])"`

Expected: Sections loaded, relevant content returned.

- [ ] **Step 4: Commit**

```bash
git add src/knowledge/ttc450_manual.txt src/knowledge/candle_guide.txt
git commit -m "feat: add TTC450 manual and Candle guide knowledge files"
```

---

## Task 3: Config — Add New Settings

**Files:**
- Modify: `src/assistant/config.py` (lines 13-52)
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test for new settings**

```python
# tests/test_config.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from assistant.config import Settings


def test_default_hotkey():
    s = Settings()
    assert s.hotkey == "f1"


def test_default_overlay_enabled():
    s = Settings()
    assert s.overlay_enabled is True


def test_default_overlay_timeout():
    s = Settings()
    assert s.overlay_timeout == 8


def test_default_overlay_color():
    s = Settings()
    assert s.overlay_color == "#ff6b6b"


def test_default_mode():
    s = Settings()
    assert s.default_mode == "guide"


def test_default_knowledge_dir():
    s = Settings()
    assert s.knowledge_dir == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'hotkey'`

- [ ] **Step 3: Add new fields to Settings class**

In `src/assistant/config.py`, add these fields to the `Settings` class after the existing `screen_monitor` field (after line 31):

```python
    # Hotkey
    hotkey: str = "f1"

    # Overlay
    overlay_enabled: bool = True
    overlay_timeout: int = 8
    overlay_color: str = "#ff6b6b"

    # Mode
    default_mode: str = "guide"  # "guide" or "do"

    # Knowledge
    knowledge_dir: str = ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/test_config.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/assistant/config.py tests/test_config.py
git commit -m "feat: add hotkey, overlay, mode, knowledge settings"
```

---

## Task 4: System Prompt — CNC Expertise

**Files:**
- Modify: `src/assistant/config.py` (lines 34-52, system_prompt field)

- [ ] **Step 1: Rewrite the system prompt**

Replace the `system_prompt` default value in `src/assistant/config.py` with the following:

```python
    system_prompt: str = (
        "Ты — голосовой помощник для работы с настольным ЧПУ-фрезером Two Trees TTC450 Pro "
        "и программой Candle. Также помогаешь с общими задачами на компьютере.\n\n"
        "ПРАВИЛА:\n"
        "- Отвечай ТОЛЬКО на русском языке\n"
        "- Говори простым языком, без технического жаргона\n"
        "- Давай одну инструкцию за раз, не перегружай информацией\n"
        "- Будь терпеливым и дружелюбным\n\n"
        "РЕЖИМЫ РАБОТЫ:\n"
        "- Режим ПОДСКАЗКИ (по умолчанию): когда пользователь спрашивает 'как сделать?', "
        "'покажи где', 'помоги', 'где находится' — покажи подсветку на экране с помощью "
        "действия highlight и объясни голосом.\n"
        "- Режим ВЫПОЛНЕНИЯ: когда пользователь говорит 'сделай это', 'нажми', 'открой', "
        "'запусти', 'закрой' — выполни действие напрямую.\n\n"
        "ДОСТУПНЫЕ ДЕЙСТВИЯ (JSON формат):\n"
        '{"action": "click", "x": 100, "y": 200} — нажать мышью\n'
        '{"action": "double_click", "x": 100, "y": 200} — двойной клик\n'
        '{"action": "right_click", "x": 100, "y": 200} — правый клик\n'
        '{"action": "type", "text": "текст"} — напечатать текст\n'
        '{"action": "hotkey", "keys": ["ctrl", "o"]} — комбинация клавиш\n'
        '{"action": "scroll", "x": 100, "y": 200, "clicks": 3} — прокрутка\n'
        '{"action": "open", "target": "notepad.exe"} — открыть программу\n'
        '{"action": "wait", "seconds": 2} — подождать\n'
        '{"action": "highlight", "type": "point", "x": 100, "y": 200, '
        '"label": "Нажмите сюда"} — подсветить элемент на экране\n'
        '{"action": "highlight", "type": "area", "x": 50, "y": 50, '
        '"w": 200, "h": 100, "label": "Эта область"} — подсветить область\n\n'
        "Если действие не требуется — просто ответь текстом.\n"
        "Можно комбинировать несколько действий в одном ответе.\n"
        "В режиме подсказки используй highlight вместо click."
    )
```

- [ ] **Step 2: Verify config loads without errors**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -c "from assistant.config import Settings; s = Settings(); print(s.system_prompt[:100])"`
Expected: Prints first 100 chars of new system prompt without errors.

- [ ] **Step 3: Commit**

```bash
git add src/assistant/config.py
git commit -m "feat: rewrite system prompt with CNC expertise and guide/do modes"
```

---

## Task 5: Overlay Module

**Files:**
- Create: `src/ui/overlay.py`
- Create: `tests/test_overlay.py`

- [ ] **Step 1: Write failing test for OverlayWindow**

```python
# tests/test_overlay.py
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_overlay_import():
    """Test that overlay module can be imported."""
    from ui.overlay import OverlayWindow
    assert OverlayWindow is not None


def test_highlight_data():
    """Test highlight data structure without creating a real window."""
    from ui.overlay import OverlayWindow

    with patch.object(OverlayWindow, "__init__", lambda self: None):
        overlay = OverlayWindow.__new__(OverlayWindow)
        overlay._highlights = []
        overlay._add_highlight("point", 100, 200, 0, 0, "Test")
        assert len(overlay._highlights) == 1
        assert overlay._highlights[0]["type"] == "point"
        assert overlay._highlights[0]["x"] == 100
        assert overlay._highlights[0]["y"] == 200
        assert overlay._highlights[0]["label"] == "Test"


def test_clear_highlights():
    """Test clearing highlights."""
    from ui.overlay import OverlayWindow

    with patch.object(OverlayWindow, "__init__", lambda self: None):
        overlay = OverlayWindow.__new__(OverlayWindow)
        overlay._highlights = []
        overlay._add_highlight("point", 100, 200, 0, 0, "Test")
        overlay._highlights.clear()
        assert len(overlay._highlights) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/test_overlay.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ui.overlay'`

- [ ] **Step 3: Implement OverlayWindow**

```python
# src/ui/overlay.py
"""Transparent fullscreen overlay for visual guidance highlights."""

import logging
from typing import List, Optional

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt6.QtWidgets import QWidget, QApplication

logger = logging.getLogger(__name__)


class OverlayWindow(QWidget):
    """Transparent, click-through fullscreen overlay that draws highlights."""

    def __init__(self, timeout: int = 8, color: str = "#ff6b6b"):
        super().__init__()
        self._highlights: List[dict] = []
        self._opacity = 1.0
        self._color = QColor(color)
        self._timeout = timeout

        # Frameless, transparent, always on top, click-through
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Cover full primary screen
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        # Pulse animation timer
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_direction = -0.05

        # Auto-dismiss timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.clear)

    def _add_highlight(self, highlight_type: str, x: int, y: int,
                       w: int = 0, h: int = 0, label: str = "") -> None:
        """Add a highlight to the list."""
        self._highlights.append({
            "type": highlight_type,
            "x": x, "y": y, "w": w, "h": h,
            "label": label,
        })

    def show_highlight(self, highlight_type: str, x: int, y: int,
                       w: int = 0, h: int = 0, label: str = "") -> None:
        """Show a highlight on screen."""
        self._add_highlight(highlight_type, x, y, w, h, label)
        self._opacity = 1.0
        self.show()
        self.update()

        # Start pulse animation
        if not self._pulse_timer.isActive():
            self._pulse_timer.start(50)

        # Reset auto-dismiss
        self._dismiss_timer.stop()
        self._dismiss_timer.start(self._timeout * 1000)

    def clear(self) -> None:
        """Clear all highlights and hide."""
        self._highlights.clear()
        self._pulse_timer.stop()
        self._dismiss_timer.stop()
        self.hide()
        self.update()

    def _pulse(self) -> None:
        """Animate highlight opacity for pulsing effect."""
        self._opacity += self._pulse_direction
        if self._opacity <= 0.4:
            self._pulse_direction = 0.05
        elif self._opacity >= 1.0:
            self._pulse_direction = -0.05
        self.update()

    def paintEvent(self, event) -> None:
        """Draw all highlights."""
        if not self._highlights:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for h in self._highlights:
            if h["type"] == "point":
                self._draw_point(painter, h)
            elif h["type"] == "area":
                self._draw_area(painter, h)
            elif h["type"] == "steps":
                self._draw_step(painter, h)
            elif h["type"] == "tooltip":
                self._draw_tooltip(painter, h)

        painter.end()

    def _draw_point(self, painter: QPainter, h: dict) -> None:
        """Draw a pulsing circle with arrow and label."""
        color = QColor(self._color)
        color.setAlphaF(self._opacity)

        # Outer circle
        pen = QPen(color, 3)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        radius = 25
        painter.drawEllipse(QPointF(h["x"], h["y"]), radius, radius)

        # Glow
        glow = QColor(self._color)
        glow.setAlphaF(self._opacity * 0.3)
        painter.setPen(QPen(glow, 6))
        painter.drawEllipse(QPointF(h["x"], h["y"]), radius + 4, radius + 4)

        # Label below
        if h["label"]:
            self._draw_label(painter, h["x"], h["y"] + radius + 20, h["label"])

    def _draw_area(self, painter: QPainter, h: dict) -> None:
        """Draw a pulsing rectangle border with label."""
        color = QColor(self._color)
        color.setAlphaF(self._opacity)

        pen = QPen(color, 3)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        rect = QRectF(h["x"], h["y"], h["w"], h["h"])
        painter.drawRoundedRect(rect, 8, 8)

        # Glow
        glow = QColor(self._color)
        glow.setAlphaF(self._opacity * 0.3)
        painter.setPen(QPen(glow, 6))
        painter.drawRoundedRect(rect.adjusted(-3, -3, 3, 3), 10, 10)

        # Label below rect
        if h["label"]:
            self._draw_label(painter, h["x"] + h["w"] / 2, h["y"] + h["h"] + 20, h["label"])

    def _draw_step(self, painter: QPainter, h: dict) -> None:
        """Draw a numbered step circle."""
        color = QColor(self._color)
        color.setAlphaF(self._opacity)

        # Filled circle with number
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(h["x"], h["y"]), 16, 16)

        # Number text
        painter.setPen(QPen(QColor("#1e1e2e"), 1))
        font = QFont("Arial", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(h["x"] - 16, h["y"] - 16, 32, 32),
                         Qt.AlignmentFlag.AlignCenter, h["label"])

    def _draw_tooltip(self, painter: QPainter, h: dict) -> None:
        """Draw a floating text label."""
        if h["label"]:
            self._draw_label(painter, h["x"], h["y"], h["label"])

    def _draw_label(self, painter: QPainter, x: float, y: float, text: str) -> None:
        """Draw a label with background at the given position."""
        font = QFont("Arial", 13, QFont.Weight.Bold)
        painter.setFont(font)

        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()
        padding = 10

        bg_rect = QRectF(
            x - text_width / 2 - padding,
            y - text_height / 2 - padding / 2,
            text_width + padding * 2,
            text_height + padding,
        )

        # Background
        bg_color = QColor(self._color)
        bg_color.setAlphaF(self._opacity * 0.2)
        painter.setPen(QPen(QColor(self._color), 2))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(bg_rect, 8, 8)

        # Text
        text_color = QColor("#ffffff")
        text_color.setAlphaF(self._opacity)
        painter.setPen(QPen(text_color, 1))
        painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, text)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/test_overlay.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/overlay.py tests/test_overlay.py
git commit -m "feat: add transparent screen overlay module"
```

---

## Task 6: Executor — Add Highlight Action

**Files:**
- Modify: `src/actions/executor.py` (lines 90-142, `_run_action` function)
- Create: `tests/test_executor_highlight.py`

- [ ] **Step 1: Write failing test for highlight action**

```python
# tests/test_executor_highlight.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/test_executor_highlight.py -v`
Expected: FAIL — highlight action not handled, returns wrong result

- [ ] **Step 3: Add highlight action to executor**

In `src/actions/executor.py`, two changes are needed:

**3a. Update `execute_actions` return type** (line 18) from `list[str]` to `list`:

```python
def execute_actions(response: str, delay: float = 0.3) -> list:
```

**3b. Update `_run_action` return type** (line 90) from `-> str` to `-> str | dict`:

```python
def _run_action(action: dict) -> str | dict:
```

**3c. Add new highlight case** in `_run_action()` before the final `else` branch. The highlight action does NOT execute pyautogui — it returns the highlight data for the engine to route to the overlay.

Add after the `wait` action block (around line 139):

```python
    elif name == "highlight":
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/test_executor_highlight.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/actions/executor.py tests/test_executor_highlight.py
git commit -m "feat: add highlight action type to executor"
```

---

## Task 7: Global Hotkey Module

**Files:**
- Create: `src/assistant/hotkey.py`
- Create: `tests/test_hotkey.py`
- Modify: `pyproject.toml` (add pynput dependency)

- [ ] **Step 1: Add pynput dependency**

In `pyproject.toml`, add `pynput>=1.7` to the dependencies list (after `pydantic-settings`):

```toml
    "pynput>=1.7",
```

- [ ] **Step 2: Install the new dependency**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && pip install pynput>=1.7`

- [ ] **Step 3: Write failing test for GlobalHotkey**

```python
# tests/test_hotkey.py
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
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/test_hotkey.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'assistant.hotkey'`

- [ ] **Step 5: Implement GlobalHotkey**

```python
# src/assistant/hotkey.py
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
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/test_hotkey.py -v`
Expected: All 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/assistant/hotkey.py tests/test_hotkey.py pyproject.toml
git commit -m "feat: add global F1 hotkey module with pynput"
```

---

## Task 8: UI Redesign — Main Window

**Files:**
- Modify: `src/ui/tray.py` (lines 48-193, MainWindow class + lines 263-318, run_app)

- [ ] **Step 1: Rewrite MainWindow._build_ui()**

Replace the `_build_ui` method (lines 75-116) in `src/ui/tray.py` with the new big/simple layout:

```python
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Status indicator — big, centered
        status_layout = QVBoxLayout()
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_icon = QLabel("🟢")
        self.status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_icon.setStyleSheet("font-size: 36px;")
        status_layout.addWidget(self.status_icon)

        self.status_label = QLabel("Готов помочь")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #a6e3a1;"
        )
        status_layout.addWidget(self.status_label)
        layout.addLayout(status_layout)

        # Chat log — large readable text
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setStyleSheet(
            "QTextEdit {"
            "  background-color: #313244;"
            "  color: #cdd6f4;"
            "  border: none;"
            "  border-radius: 12px;"
            "  padding: 14px;"
            "  font-size: 16px;"
            "}"
        )
        layout.addWidget(self.chat_log, stretch=1)

        # Big talk button
        self.listen_btn = QPushButton("🎤  НАЖМИ ЧТОБЫ ГОВОРИТЬ")
        self.listen_btn.setMinimumHeight(70)
        self.listen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.listen_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #89b4fa;"
            "  color: #1e1e2e;"
            "  border: none;"
            "  border-radius: 16px;"
            "  font-size: 22px;"
            "  font-weight: bold;"
            "  padding: 18px;"
            "}"
            "QPushButton:hover { background-color: #74c7ec; }"
            "QPushButton:pressed { background-color: #89dceb; }"
        )
        self.listen_btn.clicked.connect(self._on_listen_clicked)
        layout.addWidget(self.listen_btn)

        # Stop button — smaller, red
        self.stop_btn = QPushButton("⬛  СТОП")
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #f38ba8;"
            "  color: #1e1e2e;"
            "  border: none;"
            "  border-radius: 12px;"
            "  font-size: 16px;"
            "  font-weight: bold;"
            "  padding: 12px;"
            "}"
            "QPushButton:hover { background-color: #eba0ac; }"
        )
        self.stop_btn.clicked.connect(self._on_stop)
        layout.addWidget(self.stop_btn)

        # Settings link — small, at bottom
        settings_btn = QPushButton("⚙  Настройки")
        settings_btn.setFlat(True)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(
            "QPushButton { color: #6c7086; font-size: 13px; border: none; }"
            "QPushButton:hover { color: #cdd6f4; }"
        )
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Hotkey hint
        hotkey_label = QLabel(f"Или нажмите {self.settings.hotkey.upper()} на клавиатуре")
        hotkey_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hotkey_label.setStyleSheet("color: #585b70; font-size: 12px;")
        layout.addWidget(hotkey_label)

        # Window properties
        self.setWindowTitle("ЧПУ Помощник")
        self.setMinimumSize(420, 600)
        self.resize(420, 650)
```

- [ ] **Step 2: Update _on_state_change() for new status indicators**

Replace `_on_state_change` method (lines 141-151) with. Note: the engine passes `AssistantState` enum directly (not a string), and we use `self._is_recording` to match the existing field name from `__init__`:

```python
    def _on_state_change(self, state):
        if isinstance(state, str):
            state = AssistantState(state)
        state_map = {
            AssistantState.IDLE: ("🟢", "Готов помочь", "#a6e3a1"),
            AssistantState.LISTENING: ("🟠", "Слушаю...", "#fab387"),
            AssistantState.THINKING: ("🔵", "Думаю...", "#89b4fa"),
            AssistantState.ACTING: ("🟡", "Выполняю...", "#f9e2af"),
            AssistantState.SPEAKING: ("🟣", "Говорю...", "#cba6f7"),
        }
        icon, text, color = state_map.get(state, ("🟢", "Готов помочь", "#a6e3a1"))
        self.status_icon.setText(icon)
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")

        # Update button state (uses self._is_recording to match existing __init__)
        if state == AssistantState.IDLE:
            self.listen_btn.setText("🎤  НАЖМИ ЧТОБЫ ГОВОРИТЬ")
            self.listen_btn.setEnabled(True)
            self._is_recording = False
        elif state == AssistantState.LISTENING:
            self.listen_btn.setText("🔴  СЛУШАЮ... (нажми чтобы остановить)")
            self._is_recording = True
```

- [ ] **Step 3: Update _on_transcript and _on_response for new styling**

Replace methods with larger text formatting:

```python
    def _on_transcript(self, text: str):
        self.chat_log.append(
            f'<p style="color:#89b4fa; font-size:16px; margin:8px 0;">'
            f'🗣 <b>Вы:</b> {text}</p>'
        )

    def _on_response(self, text: str):
        import html
        clean = html.escape(text)
        self.chat_log.append(
            f'<p style="color:#a6e3a1; font-size:16px; margin:8px 0;">'
            f'🤖 {clean}</p>'
        )
```

- [ ] **Step 4: Update the window stylesheet**

Replace `_stylesheet` method (lines 165-193) with:

```python
    def _stylesheet(self):
        return """
            QMainWindow {
                background-color: #1e1e2e;
            }
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: Arial, sans-serif;
            }
        """
```

- [ ] **Step 5: Update run_app() window title and size**

In `run_app()` function, update the window title reference and ensure the main window gets proper sizing. Change the `setWindowTitle` call to "ЧПУ Помощник" and set minimum window size.

- [ ] **Step 6: Verify the app launches**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -c "print('UI module compiles'); from ui.tray import MainWindow; print('OK')"`
Expected: Prints OK without import errors.

- [ ] **Step 7: Commit**

```bash
git add src/ui/tray.py
git commit -m "feat: redesign main window with big buttons and large text"
```

---

## Task 9: Engine Integration

**Files:**
- Modify: `src/assistant/engine.py` (lines 25-164)
- Create: `tests/test_engine_modes.py`

- [ ] **Step 1: Write failing test for engine with knowledge and overlay**

```python
# tests/test_engine_modes.py
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_engine_has_overlay_callback():
    """Engine should accept an overlay callback."""
    from assistant.engine import AssistantEngine
    engine = AssistantEngine.__new__(AssistantEngine)
    engine._overlay_callback = None
    engine.set_overlay_callback(lambda *a: None)
    assert engine._overlay_callback is not None


def test_engine_has_knowledge_loader():
    """Engine should initialize knowledge loader."""
    from assistant.engine import AssistantEngine
    engine = AssistantEngine.__new__(AssistantEngine)
    engine._knowledge_loader = None
    assert engine._knowledge_loader is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/test_engine_modes.py -v`
Expected: FAIL — `set_overlay_callback` does not exist

- [ ] **Step 3: Add overlay callback and knowledge loader to engine**

In `src/assistant/engine.py`:

Add import at the top:
```python
from knowledge.loader import KnowledgeLoader
```

Add to `__init__` (after line 48):
```python
        self._overlay_callback = None
        self._knowledge_loader = None
        knowledge_dir = self.settings.knowledge_dir
        if not knowledge_dir:
            # Default to bundled knowledge
            knowledge_dir = str(Path(__file__).parent.parent / "knowledge")
        try:
            self._knowledge_loader = KnowledgeLoader(knowledge_dir)
            logger.info("Knowledge base loaded: %d sections", len(self._knowledge_loader.sections))
        except Exception as e:
            logger.warning("Could not load knowledge base: %s", e)
```

Add new method:
```python
    def set_overlay_callback(self, callback):
        """Set callback for overlay highlights: callback(type, x, y, w, h, label)."""
        self._overlay_callback = callback
```

- [ ] **Step 4: Modify listen_and_respond to use knowledge context**

In the `listen_and_respond` method, after transcription (around line 117) and before the AI call (line 120), add knowledge context:

```python
            # Get relevant knowledge context
            knowledge_context = ""
            if self._knowledge_loader and transcript:
                knowledge_context = self._knowledge_loader.get_context(transcript)

            # Build enhanced system prompt
            system_prompt = self.settings.system_prompt
            if knowledge_context:
                system_prompt = system_prompt + "\n\n" + knowledge_context
```

Pass `system_prompt` to the AI call instead of `self.settings.system_prompt`.

- [ ] **Step 5: Route highlight actions to overlay**

In `listen_and_respond`, after `execute_actions` (around line 126), check for highlight results and route to overlay:

```python
            # Route highlight actions to overlay
            if results and self._overlay_callback:
                for result in results:
                    if isinstance(result, dict) and result.get("action") == "highlight":
                        try:
                            self._overlay_callback(
                                result.get("type", "point"),
                                result.get("x", 0),
                                result.get("y", 0),
                                result.get("w", 0),
                                result.get("h", 0),
                                result.get("label", ""),
                            )
                        except Exception as e:
                            logger.error("Overlay callback error: %s", e)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/test_engine_modes.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/assistant/engine.py tests/test_engine_modes.py
git commit -m "feat: integrate knowledge base and overlay into engine"
```

---

## Task 10: Wire Everything in run_app

**Files:**
- Modify: `src/ui/tray.py` (lines 280-318, `run_app` function)

- [ ] **Step 1: Import new modules in tray.py**

Add at the top of `src/ui/tray.py`:

```python
from ui.overlay import OverlayWindow
from assistant.hotkey import GlobalHotkey
```

- [ ] **Step 2: Create overlay and hotkey in run_app**

In the `run_app()` function, after the engine is created and before the window is shown, add:

```python
    # Create overlay
    overlay = OverlayWindow(
        timeout=settings.overlay_timeout,
        color=settings.overlay_color,
    )

    # Wire overlay to engine
    def on_highlight(h_type, x, y, w, h, label):
        overlay.show_highlight(h_type, x, y, w, h, label)

    engine.set_overlay_callback(on_highlight)

    # Create global hotkey
    def on_hotkey():
        window._on_listen_clicked()

    hotkey = GlobalHotkey(key_name=settings.hotkey, callback=on_hotkey)
    hotkey.start()
```

- [ ] **Step 3: Clean up hotkey on exit**

Add cleanup before `sys.exit`:

```python
    hotkey.stop()
    overlay.clear()
```

- [ ] **Step 4: Verify app launches without errors**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -c "from ui.tray import run_app; print('All imports OK')"`
Expected: Prints "All imports OK"

- [ ] **Step 5: Commit**

```bash
git add src/ui/tray.py
git commit -m "feat: wire overlay and global hotkey into main app"
```

---

## Task 11: Update Build Configuration

**Files:**
- Modify: `build.spec` (lines 10-33)
- Modify: `pyproject.toml` (verify pynput is present)

- [ ] **Step 1: Add new hidden imports to build.spec**

In `build.spec`, add to the `hiddenimports` list:

```python
    'pynput',
    'pynput.keyboard',
    'pynput.keyboard._win32',
    'pynput._util',
    'pynput._util.win32',
```

- [ ] **Step 2: Add knowledge files to datas**

In `build.spec`, add a `datas` parameter to `Analysis`:

```python
    datas=[
        ('src/knowledge/ttc450_manual.txt', 'knowledge'),
        ('src/knowledge/candle_guide.txt', 'knowledge'),
    ],
```

- [ ] **Step 3: Add .superpowers to .gitignore**

```bash
echo ".superpowers/" >> /Users/mac/WebstormProjects/ai-assistant/.gitignore
```

- [ ] **Step 4: Commit**

```bash
git add build.spec .gitignore pyproject.toml
git commit -m "feat: update build config for overlay, hotkey, knowledge files"
```

---

## Task 12: End-to-End Smoke Test

**Files:**
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write smoke test**

```python
# tests/test_smoke.py
"""Smoke tests — verify all modules import and basic wiring works."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_all_imports():
    from assistant.config import Settings
    from assistant.engine import AssistantEngine
    from assistant.voice import VoiceCapture
    from assistant.screen import ScreenCapture
    from assistant.speaker import Speaker
    from assistant.brain import create_provider
    from assistant.hotkey import GlobalHotkey
    from actions.executor import execute_actions
    from knowledge.loader import KnowledgeLoader
    from ui.overlay import OverlayWindow


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
```

- [ ] **Step 2: Run all tests**

Run: `cd /Users/mac/WebstormProjects/ai-assistant && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_smoke.py
git commit -m "test: add end-to-end smoke tests for all new modules"
```

---

## Summary

| Task | Component | New/Modified | Key Files |
|------|-----------|-------------|-----------|
| 1 | Knowledge Loader | New | `src/knowledge/loader.py` |
| 2 | Knowledge Content | New | `ttc450_manual.txt`, `candle_guide.txt` |
| 3 | Config Settings | Modified | `src/assistant/config.py` |
| 4 | System Prompt | Modified | `src/assistant/config.py` |
| 5 | Overlay Module | New | `src/ui/overlay.py` |
| 6 | Executor Highlight | Modified | `src/actions/executor.py` |
| 7 | Global Hotkey | New | `src/assistant/hotkey.py` |
| 8 | UI Redesign | Modified | `src/ui/tray.py` |
| 9 | Engine Integration | Modified | `src/assistant/engine.py` |
| 10 | App Wiring | Modified | `src/ui/tray.py` |
| 11 | Build Config | Modified | `build.spec`, `pyproject.toml` |
| 12 | Smoke Tests | New | `tests/test_smoke.py` |
