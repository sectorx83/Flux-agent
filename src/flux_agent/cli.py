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
]


def _execute_tool(workspace: Workspace, name: str, arguments: dict[str, Any]) -> str:
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
) -> str:
    history.append({"role": "user", "content": text})
    for _ in range(max_rounds):
        message = provider.chat(history, TOOL_DEFINITIONS if mode == "build" else None)
        history.append(message)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return message.get("content") or "(No text response.)"
        for call in tool_calls:
            name = call["function"]["name"]
            arguments = json.loads(call["function"].get("arguments") or "{}")
            try:
                result = _execute_tool(workspace, name, arguments)
            except (WorkspaceError, OSError, ValueError, KeyError) as exc:
                result = f"Tool error: {exc}"
            history.append({"role": "tool", "tool_call_id": call["id"], "content": result})
    raise ProviderError("Maximum tool-call rounds reached. The task was stopped to prevent runaway execution.")


def _interactive() -> None:
    _load_dotenv()
    config = load_config()
    workspace = Workspace(config.workspace)
    provider = ProviderRouter(config.provider, config.fallback_providers, config.model, config.request_timeout)
    mode = "chat"
    history: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPTS[mode]}]
    console.print(
        Panel.fit(
            f"[bold cyan]FLUX AGENT[/bold cyan] [dim]v{__version__}[/dim]\n[white]Local-first AI workspace[/white]",
            border_style="cyan",
        )
    )
    console.print(f"Workspace: [cyan]{workspace.root}[/cyan]")
    console.print(f"Provider: [green]{config.provider}[/green] · Model: [cyan]{config.model}[/cyan]")
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
            console.print("Build mode tools: list_files, read_file, write_file, run_command")
            continue
        if command == "/model":
            console.print(f"Provider: {provider.active_provider} · Model: {config.model}")
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
                answer = _run_turn(provider, workspace, mode, history, text, config.max_tool_rounds)
            console.print(Panel(answer, title="Flux", border_style="green"))
        except ProviderError as exc:
            console.print(f"[red]Provider error:[/red] {exc}")
        except (WorkspaceError, OSError, ValueError, json.JSONDecodeError) as exc:
            console.print(f"[red]Execution error:[/red] {exc}")


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

    try:
        result = RemoteClient().submit(prompt, mode)
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print_json(data=result)


@app.command("remote-tasks")
def remote_tasks() -> None:
    """List tasks queued on the paired Flux host."""
    from flux_agent.remote.client import RemoteClient

    try:
        result = RemoteClient().tasks()
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print_json(data=result)


@app.command("memory-add")
def memory_add(
    content: str = typer.Argument(..., help="Memory content to save."),
    category: str = typer.Option("note", help="Memory category."),
) -> None:
    """Save a note to local project memory."""
    from platformdirs import user_data_dir

    from flux_agent.memory.store import MemoryStore

    path = Path(user_data_dir("flux-agent")) / "memory.sqlite3"
    memory = MemoryStore(path)
    memory_id = memory.add(str(load_config().workspace), content, category)
    console.print(f"Saved memory [green]#{memory_id}[/green]")


@app.command("memory-search")
def memory_search(query: str = typer.Argument(..., help="Search local project memory.")) -> None:
    """Search notes saved for the current workspace."""
    from platformdirs import user_data_dir
    from flux_agent.memory.store import MemoryStore

    path = Path(user_data_dir("flux-agent")) / "memory.sqlite3"
    memory = MemoryStore(path)
    results = memory.search(str(load_config().workspace), query)
    if not results:
        console.print("No matching memories.")
        return
    for item in results:
        console.print(Panel(str(item["content"]), title=f"#{item['id']} · {item['category']}"))


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
    table = Table("ID", "Name", "Next run (UTC)", "Enabled", "Interval")
    for item in engine.list():
        table.add_row(
            str(item["id"]), item["name"], item["run_at"],
            "yes" if item["enabled"] else "no",
            str(item["interval_seconds"] or "one-shot"),
        )
    console.print(table)


@app.command("workflow-add")
def workflow_add(
    name: str = typer.Argument(..., help="Workflow name."),
    payload: str = typer.Argument(..., help="JSON payload stored for the workflow handler."),
    run_at: str = typer.Argument(..., help="ISO-8601 run time, including timezone."),
    interval: int | None = typer.Option(None, help="Optional repeat interval in seconds (minimum 60)."),
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
        ).add(name, parsed_payload, parsed_time, interval)
    except (ValueError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"Scheduled workflow [green]#{workflow_id}[/green]")


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
