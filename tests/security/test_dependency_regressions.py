"""Harmless reproductions of the dependency vulnerabilities fixed in this repo."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from git.config import GitConfigParser
from starlette.formparsers import MultiPartException
from starlette.requests import Request
from vcr.serializers import yamlserializer
from yaml.constructor import ConstructorError

if TYPE_CHECKING:
    from pathlib import Path

    from starlette.types import Message


def test_git_config_rewrite_does_not_inject_directives(tmp_path: Path) -> None:
    config = tmp_path / "synthetic.config"
    config.write_text('[core]\n\tzzz = "A\\nauditmarker = injected\\\n"\n')

    def read_option(name: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "config", "--file", str(config), "--get", name],
            capture_output=True,
            text=True,
            check=False,
        )

    assert read_option("core.auditmarker").returncode == 1
    with GitConfigParser(str(config), read_only=False, merge_includes=False) as parser:
        parser.set_value("user", "name", "Security regression")

    assert read_option("core.auditmarker").returncode == 1
    assert read_option("user.name").stdout.strip() == "Security regression"


def test_vcr_rejects_python_yaml_constructors() -> None:
    with pytest.raises(ConstructorError):
        yamlserializer.deserialize(
            '_audit: !!python/object/apply:builtins.str ["synthetic-marker"]\n'
        )

    assert yamlserializer.deserialize("interactions: []\nversion: 1\n") == {
        "interactions": [],
        "version": 1,
    }


def _form_request(body: bytes) -> Request:
    delivered = False

    async def receive() -> Message:
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "scheme": "http",
            "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
            "query_string": b"",
            "server": ("127.0.0.1", 1),
        },
        receive,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "limits"),
    [(b"a=1&b=2", {"max_fields": 1}), (b"a=12345", {"max_part_size": 4})],
)
async def test_urlencoded_form_limits_are_enforced(body: bytes, limits: dict[str, Any]) -> None:
    with pytest.raises(MultiPartException):
        await _form_request(body).form(**limits)


@pytest.mark.asyncio
async def test_urlencoded_form_within_limits_still_parses() -> None:
    form = await _form_request(b"name=Ted").form(max_fields=1, max_part_size=8)
    assert form["name"] == "Ted"
