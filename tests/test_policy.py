import pytest

from flux_agent.security.policy import PermissionDenied, PermissionPolicy


def test_read_permission_does_not_need_approval():
    PermissionPolicy().check("workspace.read")


def test_shell_requires_approval():
    with pytest.raises(PermissionDenied):
        PermissionPolicy().check("shell.execute")
    PermissionPolicy().check("shell.execute", approved=True)


def test_unknown_permission_is_denied():
    with pytest.raises(PermissionDenied):
        PermissionPolicy().check("anything")
