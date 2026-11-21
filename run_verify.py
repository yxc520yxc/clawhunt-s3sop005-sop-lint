# -*- coding: utf-8 -*-
"""一键复跑：生成夹具 → sop-lint 全量校验 → pytest 全部验收。写 RUN_LOG.txt。"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
out: list[str] = []


def run(label: str, args: list[str]) -> tuple[int, str]:
    p = subprocess.run([PY] + args, cwd=str(ROOT), capture_output=True, text=True)
    body = f"$ {label}\n[exit={p.returncode}]\n{p.stdout}{p.stderr}\n"
    out.append(body)
    print(body)
    return p.returncode, body


def main() -> None:
    out.append(f"RUN at {datetime.now(timezone.utc).isoformat()}\nPY={PY}\n")
    run("生成夹具", ["_gen_fixtures.py"])
    run("sop-lint 合法样例（应 0）", ["sop_lint.py", "examples/"])
    run("sop-lint 错误样例（应非 0）", ["sop_lint.py", "errors/"])
    rc, _ = run("pytest 全部验收", ["-m", "pytest", "-v", "-s", "tests/"])
    out.append(f"\n=== SUMMARY ===\nPYTEST_EXIT={rc}\n")
    (ROOT / "RUN_LOG.txt").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
