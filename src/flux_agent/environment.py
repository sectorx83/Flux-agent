"""Secure local environment-variable storage for Flux Agent."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from collections.abc import MutableMapping

_KEY_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]{0,127}$")
_RESERVED_KEYS = {
    "PATH", "HOME", "USER", "SHELL", "PWD", "OLDPWD", "PYTHONPATH",
    "PYTHONHOME", "VIRTUAL_ENV", "LD_PRELOAD", "LD_LIBRARY_PATH",
}


class EnvironmentStore:
    """Store application credentials in a private JSON file, never print values."""

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser()

    @staticmethod
    def _validate_key(key: str) -> str:
        if not isinstance(key, str) or not _KEY_PATTERN.fullmatch(key):
            raise ValueError("Environment key must use uppercase letters, digits, and underscores.")
        if key in _RESERVED_KEYS:
            raise ValueError(f"Refusing to manage protected operating-system variable: {key}")
        return key

    def _read(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        if self.path.stat().st_size > 1024 * 1024:
            raise ValueError("Environment store exceeds the 1 MiB size limit.")
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Environment store is not valid UTF-8 JSON; refusing to overwrite it.") from exc
        if not isinstance(data, dict):
            raise ValueError("Environment store must contain a JSON object.")
        values: dict[str, str] = {}
        for key, value in data.items():
            self._validate_key(key)
            if not isinstance(value, str) or len(value) > 32768:
                raise ValueError(f"Invalid value stored for environment key: {key}")
            values[key] = value
        return values

    def _write(self, values: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            self.path.parent.chmod(0o700)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".flux-env-", dir=self.path.parent)
        temporary_path = Path(temporary_name)
        try:
            if os.name != "nt":
                os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(values, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            if os.name != "nt":
                self.path.chmod(0o600)
        finally:
            temporary_path.unlink(missing_ok=True)

    def set(self, key: str, value: str) -> None:
        key = self._validate_key(key)
        if not isinstance(value, str) or not value or len(value) > 32768 or "\x00" in value:
            raise ValueError("Environment value must contain 1-32768 non-null characters.")
        values = self._read()
        values[key] = value
        self._write(values)

    def unset(self, key: str) -> bool:
        key = self._validate_key(key)
        values = self._read()
        if key not in values:
            return False
        del values[key]
        self._write(values)
        return True

    def keys(self) -> list[str]:
        return sorted(self._read())

    def load_into(self, target: MutableMapping[str, str] | None = None) -> list[str]:
        environment = os.environ if target is None else target
        loaded = []
        for key, value in self._read().items():
            if key not in environment:
                environment[key] = value
                loaded.append(key)
        return loaded
