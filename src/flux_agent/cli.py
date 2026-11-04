"""Interactive Flux Agent command line."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from flux_agent import __version__
from flux_agent.config import load_config
from flux_agent.modes.prompts import SYSTEM_PROMPTS
from flux_agent.providers.groq import ProviderError
from flux_agent.providers.router import ChatProvider, ProviderRouter
from flux_agent.tools.shell import run_command
from flux_agent.tools.workspace import Workspace, WorkspaceError

app = typer.Typer(add_completion=True, no_args_is_help=False, help="Flux Agent: local-first AI agent CLI.")
console = Console()
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List entries in a directory inside the configured workspace.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 file inside the configured workspace.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or replace a UTF-8 file inside the configured workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command in the configured workspace. The user must approve it.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_tasks",
            "description": "Delegate independent subtasks to specialist agents and collect their results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 4,
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "instruction": {"type": "string"}
                            },
                            "required": ["name", "instruction"]
                        }
                    }
                },
                "required": ["tasks"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "integration_action",
            "description": "Perform an approved action through a configured official service API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["send_message", "create_github_issue", "create_google_task", "create_notion_task"]
                    },
                    "service": {
                        "type": "string",
                        "enum": ["slack", "discord", "telegram", "github", "google", "notion"]
                    },
                    "target": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["action", "service", "target", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_navigate",
            "description": "Open an HTTP or HTTPS page in the approved browser session.",
            "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_read",
            "description": "Read visible text from the current browser page.",
            "parameters": {"type": "object", "properties": {"max_chars": {"type": "integer"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Click the first element matching a CSS selector in the current page.",
            "parameters": {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]},
        },
    },
]

SPECIALIST_TOOL_DEFINITIONS = TOOL_DEFINITIONS[:2]


def _execute_tool(
    workspace: Workspace, name: str, arguments: dict[str, Any], provider: ChatProvider | None = None,
    browser: Any | None = None,
) -> str:
    if name == "list_files":
        return json.dumps(workspace.list_files(arguments.get("path", ".")))
    if name == "read_file":
        return workspace.read_file(arguments["path"])
    if name == "write_file":
        relative = arguments["path"]
        if not Confirm.ask(f"Create or replace [bold]{relative}[/bold]?"):
            return "User declined the file write."
        return f"Wrote {workspace.write_file(relative, arguments['content'])}"
    if name == "run_command":
        command = arguments["command"]
        console.print(Panel(command, title="Command approval", border_style="yellow"))
        if not Confirm.ask("Run this command in the workspace?"):
            return "User declined command execution."
        try:
            result = run_command(workspace, command)
        except subprocess.TimeoutExpired:
            return "Command timed out after 60 seconds."
        return json.dumps({"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    if name == "delegate_tasks":
        if provider is None:
            raise ValueError("Multi-agent delegation requires an active provider.")
        import asyncio

        from flux_agent.agents.orchestrator import AgentTask, MultiAgentOrchestrator

        raw_tasks = arguments.get("tasks")
        if not isinstance(raw_tasks, list) or not 1 <= len(raw_tasks) <= 4:
            raise ValueError("Provide between one and four delegated tasks.")
        tasks = []
        for item in raw_tasks:
            if not isinstance(item, dict):
                raise ValueError("Each delegated task must be an object.")
            name_value = item.get("name")
            instruction = item.get("instruction")
            if not isinstance(name_value, str) or not name_value.strip():
                raise ValueError("Each delegated task needs a non-empty name.")
            if not isinstance(instruction, str) or not instruction.strip():
                raise ValueError("Each delegated task needs a non-empty instruction.")
            tasks.append(AgentTask(name_value.strip(), instruction.strip()))

        async def run_agent(task: AgentTask) -> str:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a specialist agent. Complete only the assigned subtask. "
                        "Be concise and report evidence and limitations."
                    ),
                },
                {"role": "user", "content": task.instruction},
            ]
            for _ in range(4):
                response = await asyncio.to_thread(provider.chat, messages, SPECIALIST_TOOL_DEFINITIONS)
                messages.append(response)
                calls = response.get("tool_calls") or []
                if not calls:
                    return str(response.get("content") or "(No text response.)")
                for call in calls:
                    tool_name = call["function"]["name"]
                    if tool_name not in {"list_files", "read_file"}:
                        result = "Specialists may only inspect workspace files; write and execution tools are unavailable."
                    else:
                        try:
                            tool_args = json.loads(call["function"].get("arguments") or "{}")
                            result = await asyncio.to_thread(_execute_tool, workspace, tool_name, tool_args)
                        except (WorkspaceError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                            result = f"Tool error: {exc}"
                    messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
            return "Specialist stopped after reaching its tool-call limit."

        results = asyncio.run(MultiAgentOrchestrator(run_agent, max_parallel=min(4, len(tasks))).run(tasks))
        return json.dumps([
            {"name": item.name, "output": item.output, "error": item.error}
            for item in results
        ])
    if name == "integration_action":
        from flux_agent.integrations.hub import IntegrationHub

        action = arguments.get("action", "")
        service = arguments.get("service", "")
        target = arguments.get("target", "")
        title = arguments.get("title", "")
        content = arguments.get("content", "")
        summary = {
            "action": action, "service": service, "target": target,
            "title": title, "content": content,
        }
        console.print(Panel(json.dumps(summary, indent=2), title="External integration approval", border_style="yellow"))
        if not Confirm.ask("Allow this external service action?"):
            return "User declined the external integration action."
        hub = IntegrationHub()
        if action == "send_message":
            if service not in {"slack", "discord", "telegram"}:
                raise ValueError("send_message supports Slack, Discord, and Telegram.")
            result = hub.send_message(service, target, content)
        elif action == "create_github_issue" and service == "github":
            result = hub.create_github_issue(target, title, content)
        elif action == "create_google_task" and service == "google":
            result = hub.create_google_task(target, title, content)
        elif action == "create_notion_task" and service == "notion":
            result = hub.create_notion_task(target, title, content)
        else:
            raise ValueError("The selected action and service combination is not supported.")
        return json.dumps(result)
    if name in {"browser_navigate", "browser_read", "browser_click"}:
        from flux_agent.browser.automation import BrowserAutomation

        active_browser = browser or BrowserAutomation()
        if name == "browser_navigate":
            url = arguments.get("url", "")
            console.print(Panel(url, title="Browser navigation approval", border_style="yellow"))
            if not Confirm.ask("Allow the browser to open this URL?"):
                return "User declined browser navigation."
            return active_browser.navigate(url, approved=True)
        if active_browser._page is None:
            raise RuntimeError("Open a page with browser_navigate before reading or clicking.")
        if name == "browser_read":
            return active_browser.text(int(arguments.get("max_chars", 20_000)))
        selector = arguments.get("selector", "")
        console.print(Panel(selector, title="Browser interaction approval", border_style="yellow"))
        if not Confirm.ask("Allow this browser click?"):
            return "User declined browser interaction."
        active_browser.click(selector, approved=True)
        return f"Clicked selector: {selector}"
    raise ValueError(f"Unknown tool: {name}")


def _load_dotenv() -> None:
    """Load a simple local .env file without overriding existing environment values."""
    path = Path.cwd() / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _run_turn(
    provider: ChatProvider,
    workspace: Workspace,
    mode: str,
    history: list[dict[str, Any]],
    text: str,
    max_rounds: int,
    browser: Any | None = None,
) -> str:
    owns_browser = browser is None
    if browser is None:
        from flux_agent.browser.automation import BrowserAutomation

        browser = BrowserAutomation()
    history.append({"role": "user", "content": text})
    try:
        for _ in range(max_rounds):
            message = provider.chat(history, TOOL_DEFINITIONS if mode == "build" else None)
            history.append(message)
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return message.get("content") or "(No text response.)"
            for call in tool_calls:
                name = call["function"]["name"]
                try:
                    arguments = json.loads(call["function"].get("arguments") or "{}")
                    result = _execute_tool(workspace, name, arguments, provider, browser)
                except (WorkspaceError, OSError, ValueError, KeyError, RuntimeError) as exc:
                    result = f"Tool error: {exc}"
                history.append({"role": "tool", "tool_call_id": call["id"], "content": result})
        raise ProviderError("Maximum tool-call rounds reached. The task was stopped to prevent runaway execution.")
    finally:
        if owns_browser:
            browser.close()


def _interactive() -> None:
    _load_dotenv()
    config = load_config()
    workspace = Workspace(config.workspace)
    provider = ProviderRouter(
        config.provider, config.fallback_providers, config.model,
        config.request_timeout, config.model_capabilities,
    )
    mode = "chat"
    history: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPTS[mode]}]
    from flux_agent.browser.automation import BrowserAutomation

    browser = BrowserAutomation()
    console.print(
        Panel.fit(
            f"[bold cyan]FLUX AGENT[/bold cyan] [dim]v{__version__}[/dim]\n[white]Local-first AI workspace[/white]",
            border_style="cyan",
        )
    )
    console.print(f"Workspace: [cyan]{workspace.root}[/cyan]")
    console.print(f"Provider: [green]{provider.active_provider}[/green] · Model: [cyan]{provider.active_model}[/cyan]")
    console.print("Commands: /chat /plan /build /mode /tools /model /settings /help /exit")
    while True:
        try:
            text = Prompt.ask(f"[bold magenta]{mode.upper()}[/bold magenta]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\nGoodbye.")
            break
        if not text:
            continue
        command = text.lower()
        if command in {"/exit", "/quit"}:
            break
        if command in {"/chat", "/plan", "/build"}:
            mode = command[1:]
            history = [{"role": "system", "content": SYSTEM_PROMPTS[mode]}]
            console.print(f"Mode changed to [bold]{mode.upper()}[/bold].")
            continue
        if command == "/mode":
            table = Table("Mode", "Description")
            table.add_row("chat", "Conversation and assistance")
            table.add_row("plan", "Produce plans without changing files")
            table.add_row("build", "Use workspace tools; writes and commands require approval")
            console.print(table)
            continue
        if command == "/tools":
            console.print(
                "Build mode tools: list_files, read_file, write_file, run_command, delegate_tasks, "
                "browser_navigate, browser_read, browser_click, integration_action"
            )
            continue
        if command == "/model":
            console.print(f"Provider: {provider.active_provider} · Model: {provider.active_model}")
            continue
        if command == "/settings":
            console.print(
                f"Workspace: {workspace.root}\nConfig file: {config.workspace}\n"
                f"Provider: {config.provider}\nFallbacks: {config.fallback_providers}"
            )
            continue
        if command == "/help":
            console.print("Use natural language for tasks. Switch modes with /chat, /plan or /build. Use /exit to quit.")
            continue
        try:
            with console.status("Flux is thinking...", spinner="dots"):
                answer = _run_turn(provider, workspace, mode, history, text, config.max_tool_rounds, browser)
            console.print(Panel(answer, title="Flux", border_style="green"))
        except ProviderError as exc:
            console.print(f"[red]Provider error:[/red] {exc}")
        except (WorkspaceError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            console.print(f"[red]Execution error:[/red] {exc}")
    browser.close()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Start the interactive Flux Agent terminal."""
    if ctx.invoked_subcommand is None:
        _interactive()


@app.command()
def doctor() -> None:
    """Check the local Flux setup."""
    _load_dotenv()
    config = load_config()
    table = Table("Check", "Status")
    table.add_row("Python", "[green]OK[/green]")
    table.add_row("Groq API key", "[green]configured[/green]" if os.getenv("GROQ_API_KEY") else "[yellow]missing[/yellow]")
    table.add_row("Workspace", str(config.workspace))
    table.add_row("Model", config.model)
    console.print(table)


@app.command()
def init(path: Path = typer.Argument(Path("."), help="Workspace directory to initialize.")) -> None:
    """Initialize a workspace with a FLUX.md instruction file."""
    root = path.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    flux_file = root / "FLUX.md"
    if flux_file.exists():
        raise typer.BadParameter(f"{flux_file} already exists; refusing to overwrite it.")
    flux_file.write_text(
        "# Flux project instructions\n\nDescribe project conventions, commands, and constraints here.\n",
        encoding="utf-8",
    )
    console.print(f"Created [green]{flux_file}[/green]")


@app.command("remote-submit")
def remote_submit(
    prompt: str = typer.Argument(..., help="Task to send to the Flux host."),
    mode: str = typer.Option("chat", help="Remote mode: chat, plan, or build."),
) -> None:
    """Submit a task to a paired Flux host (Termux-friendly)."""
    from flux_agent.remote.client import RemoteClient

    _load_dotenv()
    try:
        result = RemoteClient().submit(prompt, mode)
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print_json(data=result)


@app.command("remote-tasks")
def remote_tasks() -> None:
    """List tasks queued on the paired Flux host."""
    from flux_agent.remote.client import RemoteClient

    _load_dotenv()
    try:
        result = RemoteClient().tasks()
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print_json(data=result)


@app.command("remote-pair")
def remote_pair(
    device_name: str = typer.Argument(..., help="Friendly name for the new device."),
) -> None:
    """Pair a new remote device. The returned token is shown only once."""
    from flux_agent.remote.client import RemoteClient

    _load_dotenv()
    try:
        result = RemoteClient().pair_device(device_name)
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print_json(data=result)
    console.print("[yellow]Copy the token now. It cannot be retrieved again.[/yellow]")


@app.command("remote-devices")
def remote_devices() -> None:
    """List paired devices and their revocation status."""
    from flux_agent.remote.client import RemoteClient

    _load_dotenv()
    try:
        result = RemoteClient().devices()
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    table = Table("Device ID", "Name", "Created", "Last used", "Revoked")
    for device in result["devices"]:
        table.add_row(
            device["id"], device["name"], device["created_at"],
            device.get("last_used_at") or "never", device.get("revoked_at") or "no",
        )
    console.print(table)


@app.command("remote-revoke")
def remote_revoke(
    device_id: str = typer.Argument(..., help="Paired device ID to revoke."),
) -> None:
    """Immediately revoke a paired device credential."""
    from flux_agent.remote.client import RemoteClient

    _load_dotenv()
    try:
        result = RemoteClient().revoke_device(device_id)
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"Revoked device [green]{result['device_id']}[/green]")


@app.command("remote-watch")
def remote_watch(task_id: int = typer.Argument(..., min=1, help="Remote task ID to stream.")) -> None:
    """Stream task status changes and the final result from the remote host."""
    from flux_agent.remote.client import RemoteClient

    _load_dotenv()
    try:
        for update in RemoteClient().stream_task(task_id):
            console.print_json(data=update)
            if update.get("status") in {"completed", "failed"}:
                break
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("memory-add")
def memory_add(
    content: str = typer.Argument(..., help="Memory content to save."),
    category: str = typer.Option("note", help="Memory category."),
    semantic: bool = typer.Option(False, help="Also create a local embedding for semantic search."),
) -> None:
    """Save a note to local project memory."""
    from platformdirs import user_data_dir

    from flux_agent.memory.store import MemoryStore

    path = Path(user_data_dir("flux-agent")) / "memory.sqlite3"
    memory = MemoryStore(path)
    project = str(load_config().workspace)
    memory_id = memory.add(project, content, category)
    if semantic:
        from flux_agent.memory.embeddings import LocalEmbedder

        embedder = LocalEmbedder()
        memory.set_embedding(memory_id, project, embedder.model_name, embedder.embed_one(content))
    console.print(f"Saved memory [green]#{memory_id}[/green]")


@app.command("memory-search")
def memory_search(
    query: str = typer.Argument(..., help="Search local project memory."),
    semantic: bool = typer.Option(False, help="Use local vector similarity instead of keyword search."),
) -> None:
    """Search notes saved for the current workspace."""
    from platformdirs import user_data_dir

    from flux_agent.memory.store import MemoryStore

    path = Path(user_data_dir("flux-agent")) / "memory.sqlite3"
    memory = MemoryStore(path)
    project = str(load_config().workspace)
    if semantic:
        from flux_agent.memory.embeddings import LocalEmbedder

        embedder = LocalEmbedder()
        results = memory.search_semantic(project, embedder.embed_one(query), embedder.model_name)
    else:
        results = memory.search(project, query)
    if not results:
        console.print("No matching memories. Use --semantic when saving notes to index them locally.")
        return
    for item in results:
        score = f" · similarity {float(item['score']):.3f}" if "score" in item else ""
        console.print(
            Panel(str(item["content"]), title=f"#{item['id']} · {item['category']}{score}")
        )


@app.command("memory-reindex")
def memory_reindex(
    batch_size: int = typer.Option(32, min=1, max=128, help="Number of notes to embed per batch."),
) -> None:
    """Create or refresh local embeddings for existing workspace memories."""
    from platformdirs import user_data_dir

    from flux_agent.memory.embeddings import LocalEmbedder
    from flux_agent.memory.store import MemoryStore

    project = str(load_config().workspace)
    memory = MemoryStore(Path(user_data_dir("flux-agent")) / "memory.sqlite3")
    embedder = LocalEmbedder()
    indexed = 0
    while True:
        pending = memory.list_unembedded(project, embedder.model_name, 500)
        if not pending:
            break
        batch = pending[:batch_size]
        vectors = embedder.embed([str(item["content"]) for item in batch])
        for item, vector in zip(batch, vectors, strict=True):
            memory.set_embedding(int(item["id"]), project, embedder.model_name, vector)
            indexed += 1
    console.print(f"Indexed [green]{indexed}[/green] memories with {embedder.model_name}.")


@app.command("usage")
def usage() -> None:
    """Show locally recorded token usage and configured cost estimates."""
    from platformdirs import user_data_dir

    from flux_agent.usage.store import UsageStore

    store = UsageStore(Path(user_data_dir("flux-agent")) / "usage.sqlite3")
    totals = store.totals()
    table = Table("Provider", "Model", "Requests", "Input tokens", "Output tokens", "Total tokens", "Estimated cost")
    for item in store.summary():
        cost = "not configured" if item["estimated_cost"] is None else f'{item["estimated_cost"]:.6f}'
        table.add_row(
            item["provider"], item["model"], str(item["requests"]),
            str(item["prompt_tokens"]), str(item["completion_tokens"]),
            str(item["total_tokens"]), cost,
        )
    console.print(table)
    console.print(
        f"All-time: {totals['requests']} requests · {totals['total_tokens']} tokens"
    )
    if totals["estimated_cost"] is None:
        console.print("Cost estimates are unavailable until model prices are configured.")
    else:
        console.print(f"Estimated configured spend: {totals['estimated_cost']:.6f}")


@app.command("usage-price")
def usage_price(
    model: str = typer.Argument(..., help="Exact model identifier returned by the provider."),
    input_price: float = typer.Argument(..., min=0, help="Price per one million input tokens."),
    output_price: float = typer.Argument(..., min=0, help="Price per one million output tokens."),
) -> None:
    """Configure token prices for transparent local cost estimates."""
    from platformdirs import user_data_dir

    from flux_agent.usage.store import UsageStore

    store = UsageStore(Path(user_data_dir("flux-agent")) / "usage.sqlite3")
    store.set_price(model, input_price, output_price)
    console.print(f"Saved token pricing for [green]{model}[/green].")


@app.command("connector-status")
def connector_status() -> None:
    """Show which official service credentials are configured."""
    from flux_agent.integrations.hub import IntegrationHub

    table = Table("Service", "Credential variable", "Status")
    for item in IntegrationHub().status():
        table.add_row(
            item["name"], item["credential"],
            "[green]configured[/green]" if item["configured"] else "[dim]not configured[/dim]",
        )
    console.print(table)


@app.command("connector-test")
def connector_test(
    service: str = typer.Argument(..., help="github, slack, discord, telegram, google, or notion."),
) -> None:
    """Verify a configured official service credential against its API."""
    from flux_agent.integrations.hub import IntegrationError, IntegrationHub

    _load_dotenv()
    try:
        result = IntegrationHub().test(service)
    except (IntegrationError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print_json(data=result)


@app.command("integrations")
def integrations() -> None:
    """Show discovered local CLI integrations."""
    from flux_agent.integrations.cli_discovery import discover_clis

    table = Table("CLI", "Path", "Status")
    for name, path in discover_clis().items():
        table.add_row(name, path or "not found", "[green]available[/green]" if path else "[dim]missing[/dim]")
    console.print(table)


@app.command("plugins")
def plugins() -> None:
    """List discovered plugin manifests. Discovery never executes plugin code."""
    from platformdirs import user_data_dir

    from flux_agent.integrations.plugins import PluginRegistry

    registry = PluginRegistry(Path(user_data_dir("flux-agent")) / "plugins")
    table = Table("ID", "Name", "Version", "Permissions")
    for plugin in registry.discover():
        table.add_row(
            plugin.plugin_id, plugin.name, plugin.version,
            ", ".join(plugin.permissions) or "none",
        )
    console.print(table)


@app.command("workflow-list")
def workflow_list() -> None:
    """List locally scheduled workflow records."""
    from platformdirs import user_data_dir

    from flux_agent.workflows.engine import WorkflowEngine

    engine = WorkflowEngine(Path(user_data_dir("flux-agent")) / "workflows.sqlite3")
    table = Table(
        "ID", "Name", "Next run (UTC)", "Enabled", "Interval", "Retries",
        "Event", "Pending events", "Last error",
    )
    for item in engine.list():
        table.add_row(
            str(item["id"]), item["name"], item["run_at"],
            "yes" if item["enabled"] else "no",
            str(item["interval_seconds"] or "one-shot"),
            f'{item["attempts"]}/{item["max_retries"]}',
            item.get("event_name") or "-",
            str(item.get("pending_count", 0)),
            (item.get("last_error") or "-")[:60],
        )
    console.print(table)


@app.command("workflow-add")
def workflow_add(
    name: str = typer.Argument(..., help="Workflow name."),
    payload: str = typer.Argument(..., help="JSON payload stored for the workflow handler."),
    run_at: str = typer.Argument(..., help="ISO-8601 run time, including timezone."),
    interval: int | None = typer.Option(None, help="Optional repeat interval in seconds (minimum 60)."),
    max_retries: int = typer.Option(0, min=0, max=20, help="Maximum retry attempts after failure."),
    retry_delay: int = typer.Option(60, min=1, max=86400, help="Seconds to wait between retries."),
    event_name: str | None = typer.Option(None, help="Optional named event; workflow waits for a matching trigger."),
) -> None:
    """Schedule a workflow record. A worker must be running to execute due workflows."""
    from datetime import datetime

    from platformdirs import user_data_dir

    from flux_agent.workflows.engine import WorkflowEngine

    try:
        parsed_payload = json.loads(payload)
        parsed_time = datetime.fromisoformat(run_at)
        if parsed_time.tzinfo is None:
            raise ValueError("run_at must include a timezone, for example +00:00.")
        workflow_id = WorkflowEngine(
            Path(user_data_dir("flux-agent")) / "workflows.sqlite3"
        ).add(name, parsed_payload, parsed_time, interval, max_retries, retry_delay, event_name)
    except (ValueError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"Scheduled workflow [green]#{workflow_id}[/green]")


@app.command("workflow-trigger")
def workflow_trigger(event_name: str = typer.Argument(..., help="Named event to trigger.")) -> None:
    """Trigger all enabled workflows waiting for a matching event."""
    from platformdirs import user_data_dir

    from flux_agent.workflows.engine import WorkflowEngine

    engine = WorkflowEngine(Path(user_data_dir("flux-agent")) / "workflows.sqlite3")
    count = engine.trigger_event(event_name)
    console.print(f"Triggered [green]{count}[/green] workflow(s) for event '{event_name}'.")


@app.command("workflow-cancel")
def workflow_cancel(workflow_id: int = typer.Argument(..., help="Workflow ID to disable.")) -> None:
    """Disable a scheduled workflow."""
    from platformdirs import user_data_dir

    from flux_agent.workflows.engine import WorkflowEngine

    engine = WorkflowEngine(Path(user_data_dir("flux-agent")) / "workflows.sqlite3")
    if not engine.cancel(workflow_id):
        raise typer.BadParameter(f"Workflow {workflow_id} was not found.")
    console.print(f"Disabled workflow [green]#{workflow_id}[/green]")


@app.command("plugin-add-manifest")
def plugin_add_manifest(path: Path = typer.Argument(..., exists=True, dir_okay=False)) -> None:
    """Install a local plugin manifest only; plugin code is not executed."""
    from platformdirs import user_data_dir

    from flux_agent.integrations.plugins import PluginRegistry

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        destination = PluginRegistry(
            Path(user_data_dir("flux-agent")) / "plugins"
        ).install_manifest(manifest)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"Installed manifest [green]{destination}[/green]")


@app.command("remote-worker")
def remote_worker(
    poll_interval: float = typer.Option(2.0, min=0.2, max=60.0, help="Seconds between queue checks."),
) -> None:
    """Execute tasks submitted to this host's authenticated remote API."""
    import time

    from platformdirs import user_data_dir

    from flux_agent.remote.tasks import RemoteTaskStore

    _load_dotenv()
    config = load_config()
    workspace = Workspace(config.workspace)
    provider = ProviderRouter(
        config.provider, config.fallback_providers, config.model,
        config.request_timeout, config.model_capabilities,
    )
    db_path = Path(os.getenv("FLUX_REMOTE_DB", str(Path(user_data_dir("flux-agent")) / "remote-tasks.sqlite3")))
    store = RemoteTaskStore(db_path)
    console.print("Remote worker online. Build tasks request approval in this terminal. Press Ctrl+C to stop.")
    try:
        while True:
            task = store.claim_next()
            if task is None:
                time.sleep(poll_interval)
                continue
            try:
                history = [{"role": "system", "content": SYSTEM_PROMPTS[task["mode"]]}]
                answer = _run_turn(provider, workspace, task["mode"], history, task["prompt"], config.max_tool_rounds)
                store.complete(task["id"], answer)
                console.print(Panel(answer, title=f"Remote task #{task['id']} completed", border_style="green"))
            except Exception as exc:
                store.fail(task["id"], str(exc))
                console.print(f"[red]Remote task #{task['id']} failed:[/red] {exc}")
    except KeyboardInterrupt:
        console.print("\nRemote worker stopped.")


@app.command("workflow-worker")
def workflow_worker(
    poll_interval: float = typer.Option(5.0, min=0.2, max=300.0, help="Seconds between schedule checks."),
) -> None:
    """Run due local workflows; each payload needs a task and optional mode."""
    import time

    from platformdirs import user_data_dir

    from flux_agent.workflows.engine import WorkflowEngine

    _load_dotenv()
    config = load_config()
    workspace = Workspace(config.workspace)
    provider = ProviderRouter(
        config.provider, config.fallback_providers, config.model,
        config.request_timeout, config.model_capabilities,
    )
    engine = WorkflowEngine(Path(user_data_dir("flux-agent")) / "workflows.sqlite3")

    def execute(name: str, payload: dict) -> None:
        task_text = payload.get("task")
        mode = payload.get("mode", "plan")
        if not isinstance(task_text, str) or not task_text.strip():
            raise ValueError(f"Workflow '{name}' requires a non-empty 'task' field.")
        if mode not in {"chat", "plan", "build"}:
            raise ValueError("Workflow mode must be chat, plan, or build.")
        history = [{"role": "system", "content": SYSTEM_PROMPTS[mode]}]
        answer = _run_turn(provider, workspace, mode, history, task_text, config.max_tool_rounds)
        console.print(Panel(answer, title=f"Workflow: {name}", border_style="green"))

    console.print("Workflow worker online. Build actions ask for approval in this terminal. Press Ctrl+C to stop.")
    try:
        while True:
            try:
                engine.run_due(
                    execute,
                    on_error=lambda name, error, retrying: console.print(
                        f"[yellow]Workflow '{name}' failed: {error}. "
                        f"{'Retry scheduled.' if retrying else 'Retries exhausted.'}[/yellow]"
                    ),
                )
            except Exception as exc:
                console.print(f"[red]Workflow error:[/red] {exc}")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        console.print("\nWorkflow worker stopped.")
