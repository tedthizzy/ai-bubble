"""Exercise Bash prompt expansion with a harmless, private command marker."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.skipif(sys.platform == "win32", reason="Bash activation is a POSIX path")
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="Root expands a different prompt"
)
def test_virtualenv_prompt_does_not_execute_environment_name(tmp_path: Path) -> None:
    environment = tmp_path / "environment"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "virtualenv",
            "--no-seed",
            "--no-download",
            "--prompt",
            r"audit\$(touch injected-marker)",
            str(environment),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        timeout=30,
    )
    shell_environment = dict(os.environ)
    for key in ["VIRTUAL_ENV_DISABLE_PROMPT", "PROMPT_COMMAND", "BASH_ENV", "ENV"]:
        shell_environment.pop(key, None)
    shell_environment["VIRTUALENV_TEST_ACTIVATE"] = str(environment / "bin/activate")
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-i"],
        input='PS1="base> "\n. "$VIRTUALENV_TEST_ACTIVATE"\nexit\n',
        env=shell_environment,
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    assert "audit" in result.stderr
    assert not (tmp_path / "injected-marker").exists()
