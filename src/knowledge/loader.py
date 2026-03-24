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
