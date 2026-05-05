"""Unit tests for the OpenUI DSL validator wrapper (HUG-178 Phase B).

Exercises every soft-skip branch by monkey-patching `shutil.which` and
`subprocess.run` — no real Node invocation in these tests, so they run
on CI hosts without Node installed.

A separate end-to-end smoke (the merge gate) covers the happy path
through real Node.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest
from api.services import openui_validator
from api.types.openui import OpenUIDslPayload


def _fake_run(stdout: str, returncode: int = 0, stderr: str = "") -> Any:
    class _Result:
        def __init__(self) -> None:
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    return _Result()


def test_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openui_validator.shutil, "which", lambda _: "/usr/bin/node")
    monkeypatch.setattr(openui_validator, "_validator_script_exists", lambda: True)
    monkeypatch.setattr(
        openui_validator.subprocess,
        "run",
        lambda *a, **kw: _fake_run(json.dumps({"valid": True, "errors": []})),
    )
    result = openui_validator.validate_openui_dsl("root = Stack([], \"column\", \"m\")")
    assert isinstance(result, OpenUIDslPayload)
    assert result.validated is True
    assert result.validation_errors == []
    assert result.is_renderable is True


def test_happy_path_with_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openui_validator.shutil, "which", lambda _: "/usr/bin/node")
    monkeypatch.setattr(openui_validator, "_validator_script_exists", lambda: True)
    monkeypatch.setattr(
        openui_validator.subprocess,
        "run",
        lambda *a, **kw: _fake_run(
            json.dumps(
                {
                    "valid": False,
                    "errors": [
                        {"code": "unknown-component", "message": "Unknown comp Foo"}
                    ],
                }
            )
        ),
    )
    result = openui_validator.validate_openui_dsl("root = Foo()")
    assert result.validated is True
    assert len(result.validation_errors) == 1
    assert result.validation_errors[0].code == "unknown-component"
    assert result.is_renderable is False


def test_synthetic_no_root_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the parser reports valid:false but no errors (e.g. empty
    input), inject a synthetic `no_root` error so `is_renderable` is
    correct."""
    monkeypatch.setattr(openui_validator.shutil, "which", lambda _: "/usr/bin/node")
    monkeypatch.setattr(openui_validator, "_validator_script_exists", lambda: True)
    monkeypatch.setattr(
        openui_validator.subprocess,
        "run",
        lambda *a, **kw: _fake_run(json.dumps({"valid": False, "errors": []})),
    )
    result = openui_validator.validate_openui_dsl("")
    assert result.validated is True
    assert result.is_renderable is False
    assert result.validation_errors[0].code == "no_root"


def test_node_not_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openui_validator.shutil, "which", lambda _: None)
    result = openui_validator.validate_openui_dsl("root = Stack([])")
    assert result.validated is False
    assert result.validated_at is None
    assert result.dsl_text == "root = Stack([])"


def test_validator_script_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openui_validator.shutil, "which", lambda _: "/usr/bin/node")
    monkeypatch.setattr(openui_validator, "_validator_script_exists", lambda: False)
    result = openui_validator.validate_openui_dsl("root = Stack([])")
    assert result.validated is False


def test_validator_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openui_validator.shutil, "which", lambda _: "/usr/bin/node")
    monkeypatch.setattr(openui_validator, "_validator_script_exists", lambda: True)

    def _raise_timeout(*a: Any, **kw: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd=["node"], timeout=5.0)

    monkeypatch.setattr(openui_validator.subprocess, "run", _raise_timeout)
    result = openui_validator.validate_openui_dsl("root = Stack([])")
    assert result.validated is False


def test_validator_bad_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openui_validator.shutil, "which", lambda _: "/usr/bin/node")
    monkeypatch.setattr(openui_validator, "_validator_script_exists", lambda: True)
    monkeypatch.setattr(
        openui_validator.subprocess,
        "run",
        lambda *a, **kw: _fake_run("not json"),
    )
    result = openui_validator.validate_openui_dsl("root = Stack([])")
    assert result.validated is False


def test_validator_no_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openui_validator.shutil, "which", lambda _: "/usr/bin/node")
    monkeypatch.setattr(openui_validator, "_validator_script_exists", lambda: True)
    monkeypatch.setattr(
        openui_validator.subprocess,
        "run",
        lambda *a, **kw: _fake_run("", returncode=2, stderr="boom"),
    )
    result = openui_validator.validate_openui_dsl("root = Stack([])")
    assert result.validated is False


def test_validator_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openui_validator.shutil, "which", lambda _: "/usr/bin/node")
    monkeypatch.setattr(openui_validator, "_validator_script_exists", lambda: True)

    def _raise_oserror(*a: Any, **kw: Any) -> Any:
        raise OSError("eperm")

    monkeypatch.setattr(openui_validator.subprocess, "run", _raise_oserror)
    result = openui_validator.validate_openui_dsl("root = Stack([])")
    assert result.validated is False
