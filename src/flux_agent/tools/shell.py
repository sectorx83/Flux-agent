"""Approval-gated shell execution inside the workspace."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from flux_agent.tools.workspace import Workspace


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str


def run_command(workspace: Workspace, command: str, timeout: int = 60) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=workspace.root,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return CommandResult(command, completed.returncode, completed.stdout[-20_000:], completed.stderr[-20_000:])
