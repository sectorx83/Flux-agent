from pathlib import Path

from flux_agent.cli import _execute_tool
from flux_agent.tools.workspace import Workspace


class FakeProvider:
    def chat(self, messages, tools=None):
        return {"content": f"completed: {messages[-1]['content']}"}


def test_delegate_tasks_runs_parallel_specialists(tmp_path: Path):
    workspace = Workspace(tmp_path)
    result = _execute_tool(
        workspace,
        "delegate_tasks",
        {"tasks": [
            {"name": "research", "instruction": "find likely causes"},
            {"name": "review", "instruction": "review the proposed fix"},
        ]},
        FakeProvider(),
    )
    import json

    parsed = json.loads(result)
    assert [item["name"] for item in parsed] == ["research", "review"]
    assert all(item["output"].startswith("completed:") for item in parsed)


def test_delegate_tasks_rejects_empty_batch(tmp_path: Path):
    import pytest

    with pytest.raises(ValueError, match="between one and four"):
        _execute_tool(Workspace(tmp_path), "delegate_tasks", {"tasks": []}, FakeProvider())
