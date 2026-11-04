import asyncio

from flux_agent.agents.orchestrator import AgentTask, MultiAgentOrchestrator


def test_orchestrator_collects_results():
    async def runner(task):
        return f"done:{task.instruction}"

    orchestrator = MultiAgentOrchestrator(runner, max_parallel=2)
    results = asyncio.run(orchestrator.run([
        AgentTask("researcher", "research"),
        AgentTask("reviewer", "review"),
    ]))
    assert [item.output for item in results] == ["done:research", "done:review"]
