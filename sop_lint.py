#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sop-lint —— 校验 SOP 模板 JSON 文件（可在 CI 中运行）。

用法：
    python sop_lint.py <文件或目录> [<文件或目录> ...]
    python sop_lint.py --json <文件或目录>       # 机器可读输出

行为：
  - 文件：直接校验该 JSON 文档。
  - 目录：递归收集其下所有 .json 文件逐一校验。
  - 存在任一 error 级问题 -> 打印明细并以退出码 1 结束；全部通过 -> 退出码 0。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from app.lint import lint_doc, has_errors, load_schema
from app.catalog import DUE_KINDS, DUE_UNITS  # noqa: F401  保证与 catalog 同步导入


def collect_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.json")))
        elif p.is_file():
            files.append(p)
        else:
            print(f"[sop-lint] 路径不存在: {t}", file=sys.stderr)
    return files


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    if not argv:
        print("用法: python sop_lint.py [--json] <文件或目录> [...]", file=sys.stderr)
        return 2

    validator = Draft202012Validator(load_schema())
    files = collect_files(argv)
    if not files:
        print("[sop-lint] 没有找到可校验的 .json 文件", file=sys.stderr)
        return 2

    report: list[dict] = []
    any_error = False
    for fp in files:
        try:
            doc = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as exc:  # JSON 解析失败同样计为 schema 错误
            issues = [{"code": "E001", "severity": "error", "path": "/",
                       "message": f"JSON 解析失败: {exc}"}]
        else:
            issues = [i.as_dict() for i in lint_doc(doc, validator)]
        errs = [i for i in issues if i["severity"] == "error"]
        if errs:
            any_error = True
        report.append({"file": str(fp), "errors": len(errs), "issues": issues})

    if as_json:
        print(json.dumps({"ok": not any_error, "files": report},
                         ensure_ascii=False, indent=2))
    else:
        for entry in report:
            if entry["errors"]:
                print(f"FAIL {entry['file']}  ({entry['errors']} errors)")
                for i in entry["issues"]:
                    if i["severity"] == "error":
                        print(f"   [{i['code']}] {i['path']}: {i['message']}")
            else:
                print(f"OK   {entry['file']}")
        print(f"\n总计 {len(report)} 文件，"
              f"{'存在错误' if any_error else '全部通过'}。")
    return 1 if any_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
