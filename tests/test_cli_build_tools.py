import json
from pathlib import Path

from flux_agent.cli import (
    SPECIALIST_TOOL_DEFINITIONS,
    TOOL_DEFINITIONS,
    _execute_tool,
)
from flux_agent.tools.workspace import Workspace


class FakeProvider:
    def __init__(self, first_tool: str = "read_file") -> None:
        self.calls = 0
        self.first_tool = first_tool
        self.last_messages = []

    def chat(self, messages, tools=None):
        self.calls += 1
        self.last_messages = list(messages)
        if self.calls == 1:
            return {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "specialist-call",
                        "function": {
                            "name": self.first_tool,
                            "arguments": json.dumps({"path": "facts.txt"}),
                        },
                    }
                ],
            }
        return {"role": "assistant", "content": "Inspected the shared workspace file."}


def test_specialists_receive_shared_read_only_workspace_tools(tmp_path: Path):
    workspace = Workspace(tmp_path)
    workspace.write_file("facts.txt", "The release target is Python 3.11.")
    provider = FakeProvider()

    result = json.loads(
        _execute_tool(
            workspace,
            "delegate_tasks",
            {"tasks": [{"name": "inspect", "instruction": "Inspect the release target."}]},
            provider,
        )
    )

    assert [item["function"]["name"] for item in SPECIALIST_TOOL_DEFINITIONS] == [
        "list_files",
        "read_file",
    ]
    assert result[0]["output"] == "Inspected the shared workspace file."
    assert provider.calls == 2


def test_specialist_cannot_execute_write_tools(tmp_path: Path):
    workspace = Workspace(tmp_path)
    provider = FakeProvider(first_tool="write_file")

    json.loads(
        _execute_tool(
            workspace,
            "delegate_tasks",
            {"tasks": [{"name": "inspect", "instruction": "Try to write."}]},
            provider,
        )
    )

    assert any(
        "write and execution tools are unavailable" in str(message.get("content", ""))
        for message in provider.last_messages
    )
    assert not (tmp_path / "facts.txt").exists()


def test_browser_tools_are_registered_for_build_mode():
    names = {item["function"]["name"] for item in TOOL_DEFINITIONS}
    assert {"browser_navigate", "browser_read", "browser_click"} <= names


class FakeBrowser:
    _page = object()

    def __init__(self):
        self.navigated = []
        self.clicked = []

    def navigate(self, url, approved=False):
        self.navigated.append((url, approved))
        return "200 · Example · https://example.com"

    def text(self, max_chars=20_000):
        return "Example page text"[:max_chars]

    def click(self, selector, approved=False):
        self.clicked.append((selector, approved))


def test_browser_navigation_requires_confirmation(tmp_path: Path, monkeypatch):
    from flux_agent import cli

    browser = FakeBrowser()
    monkeypatch.setattr(cli.Confirm, "ask", lambda *_args, **_kwargs: False)
    result = _execute_tool(
        Workspace(tmp_path),
        "browser_navigate",
        {"url": "https://example.com"},
        browser=browser,
    )
    assert result == "User declined browser navigation."
    assert browser.navigated == []


def test_browser_navigation_and_click_use_approved_actions(tmp_path: Path, monkeypatch):
    from flux_agent import cli

    browser = FakeBrowser()
    monkeypatch.setattr(cli.Confirm, "ask", lambda *_args, **_kwargs: True)
    workspace = Workspace(tmp_path)
    assert _execute_tool(
        workspace, "browser_navigate", {"url": "https://example.com"}, browser=browser
    ).startswith("200")
    assert _execute_tool(
        workspace, "browser_click", {"selector": "button.submit"}, browser=browser
    ) == "Clicked selector: button.submit"
    assert browser.navigated == [("https://example.com", True)]
    assert browser.clicked == [("button.submit", True)]


def test_external_integration_action_requires_confirmation(tmp_path: Path, monkeypatch):
    from flux_agent import cli

    calls = []

    class FakeHub:
        def send_message(self, service, target, content):
            calls.append((service, target, content))
            return {"service": service, "message_id": "test-id"}

    monkeypatch.setattr("flux_agent.integrations.hub.IntegrationHub", FakeHub)
    monkeypatch.setattr(cli.Confirm, "ask", lambda *_args, **_kwargs: False)
    result = _execute_tool(
        Workspace(tmp_path),
        "integration_action",
        {
            "action": "send_message", "service": "slack",
            "target": "C123", "content": "Hello",
        },
    )
    assert result == "User declined the external integration action."
    assert calls == []


def test_external_integration_action_dispatches_after_approval(tmp_path: Path, monkeypatch):
    from flux_agent import cli

    calls = []

    class FakeHub:
        def create_github_issue(self, repository, title, body):
            calls.append((repository, title, body))
            return {"service": "github", "number": 5}

    monkeypatch.setattr("flux_agent.integrations.hub.IntegrationHub", FakeHub)
    monkeypatch.setattr(cli.Confirm, "ask", lambda *_args, **_kwargs: True)
    result = _execute_tool(
        Workspace(tmp_path),
        "integration_action",
        {
            "action": "create_github_issue", "service": "github",
            "target": "org/repo", "title": "Bug", "content": "Details",
        },
    )
    assert '"number": 5' in result
    assert calls == [("org/repo", "Bug", "Details")]
