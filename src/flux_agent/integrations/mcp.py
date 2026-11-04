"""Minimal MCP stdio JSON-RPC client for explicitly configured local servers."""

from __future__ import annotations

import json
import subprocess
from typing import Any


class MCPError(RuntimeError):
    pass


class MCPStdioClient:
    def __init__(self, command: list[str], timeout: float = 20.0) -> None:
        if not command:
            raise ValueError("MCP server command cannot be empty.")
        self.command = command
        self.timeout = timeout
        self.process: subprocess.Popen | None = None
        self.request_id = 0

    def start(self) -> None:
        if self.process is not None:
            return
        self.process = subprocess.Popen(
            self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1,
        )
        self.request("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "flux-agent", "version": "0.1.0"},
        })
        self.notify("notifications/initialized", {})

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            raise MCPError("MCP process is not running.")
        self.request_id += 1
        request_id = self.request_id
        message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise MCPError("MCP server closed its output stream.")
            response = json.loads(line)
            if response.get("id") != request_id:
                continue
            if "error" in response:
                raise MCPError(str(response["error"]))
            return response.get("result", {})

    def notify(self, method: str, params: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise MCPError("MCP process is not running.")
        self.process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "method": method, "params": params
        }) + "\n")
        self.process.stdin.flush()

    def list_tools(self) -> list[dict[str, Any]]:
        return self.request("tools/list", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self) -> None:
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
