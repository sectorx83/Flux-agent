import asyncio

import pytest

from flux_agent.agents.orchestrator import AgentTask, MultiAgentOrchestrator


def test_orchestrator_returns_results_and_isolates_failures():
    async def runner(task):
        if task.name == "bad":
            raise RuntimeError("failed")
        return task.instruction.upper()

    results = asyncio.run(
        MultiAgentOrchestrator(runner, max_parallel=2).run(
            [AgentTask("good", "one"), AgentTask("bad", "two")]
        )
    )
    assert results[0].output == "ONE"
    assert results[0].error is None
    assert results[1].output is None
    assert results[1].error == "failed"


def test_orchestrator_rejects_duplicate_task_names():
    async def runner(task):
        return task.instruction

    orchestrator = MultiAgentOrchestrator(runner)
    with pytest.raises(ValueError, match="unique"):
        asyncio.run(orchestrator.run([AgentTask("same", "one"), AgentTask("same", "two")]))


def test_orchestrator_rejects_excessive_parallelism():
    async def runner(task):
        return task.instruction

    with pytest.raises(ValueError, match="max_parallel"):
        MultiAgentOrchestrator(runner, max_parallel=17)
