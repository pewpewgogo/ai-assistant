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
