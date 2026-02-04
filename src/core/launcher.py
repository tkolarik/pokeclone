import os
import subprocess
import sys
from typing import Iterable, Optional


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _module_command(module_name: str, args: Optional[Iterable[str]] = None) -> list[str]:
    cmd = [sys.executable]
    if is_frozen():
        cmd += ["--run-module", module_name]
    else:
        cmd += ["-m", module_name]
    if args:
        cmd += list(args)
    return cmd


def spawn_module(module_name: str, args: Optional[Iterable[str]] = None, env: Optional[dict] = None) -> subprocess.Popen:
    return subprocess.Popen(_module_command(module_name, args), env=env)


def run_module(module_name: str, args: Optional[Iterable[str]] = None, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    return subprocess.run(_module_command(module_name, args), env=env)
