"""Workspace-confined file operations."""

from __future__ import annotations

from pathlib import Path


class WorkspaceError(ValueError):
    """Raised when a requested path is outside the configured workspace."""


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError("Path is outside the configured workspace.") from exc
        return candidate

    def list_files(self, relative_path: str = ".") -> list[str]:
        directory = self.resolve(relative_path)
        if not directory.is_dir():
            raise WorkspaceError(f"Not a directory: {relative_path}")
        return sorted(
            str(path.relative_to(self.root)) + ("/" if path.is_dir() else "")
            for path in directory.iterdir()
            if path.name != ".git"
        )

    def read_file(self, relative_path: str, max_chars: int = 20_000) -> str:
        path = self.resolve(relative_path)
        if not path.is_file():
            raise WorkspaceError(f"File does not exist: {relative_path}")
        return path.read_text(encoding="utf-8")[:max_chars]

    def write_file(self, relative_path: str, content: str) -> str:
        path = self.resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path.relative_to(self.root))
