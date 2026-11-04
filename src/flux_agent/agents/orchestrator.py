"""Bounded multi-agent task delegation."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentTask:
    name: str
    instruction: str


@dataclass(frozen=True, slots=True)
class AgentResult:
    name: str
    output: str | None
    error: str | None = None


AgentRunner = Callable[[AgentTask], Awaitable[str]]


class MultiAgentOrchestrator:
    def __init__(self, runner: AgentRunner, max_parallel: int = 3) -> None:
        if max_parallel < 1 or max_parallel > 16:
            raise ValueError("max_parallel must be between 1 and 16.")
        self.runner = runner
        self.semaphore = asyncio.Semaphore(max_parallel)

    async def _run_one(self, task: AgentTask) -> AgentResult:
        async with self.semaphore:
            try:
                output = await self.runner(task)
                return AgentResult(task.name, output)
            except Exception as exc:
                return AgentResult(task.name, None, str(exc))

    async def run(self, tasks: list[AgentTask]) -> list[AgentResult]:
        if len(tasks) > 32:
            raise ValueError("A single orchestration batch is limited to 32 tasks.")
        names = [task.name for task in tasks]
        if len(set(names)) != len(names):
            raise ValueError("Agent task names must be unique.")
        return await asyncio.gather(*(self._run_one(task) for task in tasks))
