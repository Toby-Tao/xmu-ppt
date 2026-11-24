#!/usr/bin/env python3
"""Resolve a Python interpreter that has the xmu-ppt core dependencies.

Installed skills do not ship a virtual environment. This script keeps the skill
usable outside the source checkout:

- If the current interpreter already imports the core modules, use it.
- Otherwise reuse ``~/.xmu-ppt/venv`` when it is healthy.
- Otherwise create that venv and install ``requirements-core.txt`` once.

Usage:
    python bootstrap_env.py            # ensure a usable interpreter, print a report
    python bootstrap_env.py --check    # check only, never create or install
    python bootstrap_env.py --python   # ensure, then print only the interpreter path

The JSON report on ``--check`` has ``ok`` and ``python`` keys. Exit code is 0
when the interpreter is usable.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
REQUIREMENTS = SKILL_DIR / "requirements-core.txt"
CORE_IMPORT = "import pptx, PIL, yaml, requests, flask"
DEFAULT_VENV = Path(os.environ.get("XMU_PPT_VENV", str(Path.home() / ".xmu-ppt" / "venv")))


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def modules_ok(python: Path) -> bool:
    try:
        completed = subprocess.run(
            [str(python), "-c", CORE_IMPORT],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def check_python(python: Path) -> None:
    if sys.version_info < (3, 10):
        raise SystemExit(
            f"需要 Python 3.10 或更高版本，当前为 {sys.version.split()[0]}。"
            "请先安装新版 Python，再运行本脚本。"
        )


def ensure_venv(venv: Path) -> Path:
    python = venv_python(venv)
    if python.is_file() and modules_ok(python):
        return python
    if not REQUIREMENTS.is_file():
        raise SystemExit(f"缺少依赖清单：{REQUIREMENTS}")
    venv.parent.mkdir(parents=True, exist_ok=True)
    if not python.is_file():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    subprocess.run(
        [str(python), "-m", "pip", "install", "--disable-pip-version-check", "-q",
         "-r", str(REQUIREMENTS)],
        check=True,
    )
    if not modules_ok(python):
        raise SystemExit(
            f"依赖安装后仍无法导入核心模块。请手动运行：\n  {python} -m pip install -r {REQUIREMENTS}"
        )
    return python


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只检查，不创建环境和安装依赖")
    parser.add_argument("--python", action="store_true", help="只输出可用的解释器路径")
    args = parser.parse_args(argv)

    check_python(Path(sys.executable))
    current = Path(sys.executable)
    if modules_ok(current):
        python, created = current, False
    elif args.check:
        python, created = (venv_python(DEFAULT_VENV) if venv_python(DEFAULT_VENV).is_file() else current), False
    else:
        venv_existed = venv_python(DEFAULT_VENV).is_file()
        python = ensure_venv(DEFAULT_VENV)
        created = not venv_existed
        if not args.python:
            action = "已创建并安装依赖" if created else "已复用现有环境"
            print(f"{action}：{python}", file=sys.stderr)

    ok = modules_ok(python)
    if args.check:
        print(json.dumps({"ok": ok, "python": str(python)}, ensure_ascii=False))
        return 0 if ok else 1
    if not ok:
        print(
            "核心依赖不可用。请在可联网环境运行：\n"
            f"  {current} -m pip install -r {REQUIREMENTS}",
            file=sys.stderr,
        )
        return 1
    if args.python:
        print(str(python))
        return 0
    print(f"Python: {python}")
    print(f"依赖: OK ({REQUIREMENTS})")
    print("后续命令请使用上面的解释器，并把脚本路径写成 ${SKILL_DIR}/scripts/...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
