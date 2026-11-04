"""Explicit capability policy used by tools and integrations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Permission:
    name: str
    description: str
    requires_approval: bool = True


DEFAULT_PERMISSIONS = {
    "workspace.read": Permission("workspace.read", "Read files in the configured workspace", False),
    "workspace.write": Permission("workspace.write", "Create or replace workspace files"),
    "shell.execute": Permission("shell.execute", "Execute a local shell command"),
    "network.access": Permission("network.access", "Make an outbound network request"),
    "browser.control": Permission("browser.control", "Control a browser session"),
    "deployment.create": Permission("deployment.create", "Create or update a deployment"),
    "external.submit": Permission("external.submit", "Submit data to an external service"),
}


class PermissionDenied(RuntimeError):
    pass


class PermissionPolicy:
    def __init__(self, granted: set[str] | None = None) -> None:
        self.granted = set(granted or ())

    def check(self, permission: str, approved: bool = False) -> None:
        rule = DEFAULT_PERMISSIONS.get(permission)
        if rule is None:
            raise PermissionDenied(f"Unknown permission: {permission}")
        if rule.requires_approval and permission not in self.granted and not approved:
            raise PermissionDenied(f"Permission '{permission}' requires explicit approval.")

    def grant(self, permission: str) -> None:
        if permission not in DEFAULT_PERMISSIONS:
            raise PermissionDenied(f"Unknown permission: {permission}")
        self.granted.add(permission)

    def revoke(self, permission: str) -> None:
        self.granted.discard(permission)
