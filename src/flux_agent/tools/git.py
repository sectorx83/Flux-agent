"""Git inspection helpers that avoid shell interpolation."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def git_status(workspace: Path) -> str:
    if shutil.which("git") is None:
        raise FileNotFoundError("Git is not installed.")
    result = subprocess.run(
        ["git", "status", "--short", "--branch"], cwd=workspace,
        capture_output=True, text=True, timeout=15, check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git status failed.")
    return result.stdout
