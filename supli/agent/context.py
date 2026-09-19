"""Context gathering (SKILL §6, roadmap §28).

Only the context needed for the current request is assembled. The whole
project is never sent to the model. Retrieval here is lexical; semantic
retrieval/RAG is a later, optional optimisation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..tools.workspace import Workspace

TEXT_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt", ".json", ".toml", ".yaml", ".yml",
    ".html", ".css", ".sh", ".rs", ".go", ".java", ".c", ".h", ".cpp", ".sql", ".cfg", ".ini",
}

DEFAULT_MAX_FILES = 8
DEFAULT_MAX_CHARS = 40_000


@dataclass
class ContextBundle:
    files: list[dict[str, object]]
    total_chars: int
    documents: list[str]

    def to_prompt(self) -> str:
        if not self.files:
            return "(no project files matched the request)"
        parts = []
        for item in self.files:
            parts.append(f"--- {item['path']} ---\n{item['content']}")
        return "\n\n".join(parts)


class ContextGatherer:
    def __init__(self, workspace: Workspace, max_files: int = DEFAULT_MAX_FILES,
                 max_chars: int = DEFAULT_MAX_CHARS) -> None:
        self.workspace = workspace
        self.max_files = max_files
        self.max_chars = max_chars

    def _candidate_files(self) -> list[Path]:
        skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
        out: list[Path] = []
        for path in self.workspace.root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in skip for part in path.parts):
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            out.append(path)
        return out

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {t for t in re.findall(r"[a-zA-Z0-9_.\-]{3,}", text.lower())}

    def gather(self, request: str, explicit_paths: list[str] | None = None) -> ContextBundle:
        """Select relevant files by explicit path first, then lexical score."""
        selected: list[dict[str, object]] = []
        seen: set[str] = set()
        total = 0

        if explicit_paths:
            for rel in explicit_paths:
                try:
                    target = self.workspace.resolve(rel, must_exist=True)
                except Exception:
                    continue
                if not target.is_file():
                    continue
                content = target.read_text(encoding="utf-8", errors="replace")
                selected.append({"path": rel, "content": content[: self.max_chars]})
                seen.add(rel)
                total += len(content)

        query_tokens = self._tokens(request)
        scored: list[tuple[int, Path]] = []
        for path in self._candidate_files():
            try:
                rel = str(path.relative_to(self.workspace.root))
            except ValueError:
                continue
            if rel in seen:
                continue
            name_tokens = self._tokens(rel)
            score = len(query_tokens & name_tokens) * 3
            if score == 0:
                try:
                    head = path.read_text(encoding="utf-8", errors="replace")[:4000]
                except OSError:
                    continue
                score = len(query_tokens & self._tokens(head))
            if score > 0:
                scored.append((score, path))
        scored.sort(key=lambda pair: (-pair[0], str(pair[1])))

        for _, path in scored:
            if len(selected) >= self.max_files or total >= self.max_chars:
                break
            rel = str(path.relative_to(self.workspace.root))
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            budget = self.max_chars - total
            if budget <= 0:
                break
            selected.append({"path": rel, "content": content[:budget]})
            total += min(len(content), budget)

        documents = [d for d in ("roadmap.md", "SKILL.md", "README.md")
                     if (self.workspace.root / d).exists()]
        return ContextBundle(files=selected, total_chars=total, documents=documents)