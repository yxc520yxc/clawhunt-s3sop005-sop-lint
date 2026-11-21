# -*- coding: utf-8 -*-
"""sop-lint 核心校验逻辑。

检查 7 类错误（每类一个错误样例文件）：
  E001 schema_invalid      —— 不符合 sop-template.schema.json
  E002 unknown_role        —— 步骤 role_code 不在岗位目录
  E003 invalid_due_rule    —— due_rule kind/value/unit 不合法
  E004 duplicate_seq       —— 步骤 seq 重复
  E005 unknown_event       —— 触发事件不在事件目录
  E006 cyclic_dependency   —— depends_on 构成环 / 引用不存在
  E007 invalid_field_path  —— 条件表达式字段路径非法

每条 Issue 含 code/severity/path/message。存在任一 error 级 Issue 时，
CLI 退出码非 0。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .catalog import (
    role_exists,
    event_exists,
    field_path_allowed,
    DUE_KINDS,
    DUE_UNITS,
)

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "sop-template.schema.json"


@dataclass
class Issue:
    code: str
    severity: str  # "error" | "warning"
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def load_schema() -> dict[str, Any]:
    import json
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validate_schema(doc: dict[str, Any], validator: Draft202012Validator) -> list[Issue]:
    issues = []
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        p = "/" + "/".join(str(x) for x in err.absolute_path)
        issues.append(Issue("E001", "error", p, err.message))
    return issues


def _validate_roles(doc: dict[str, Any]) -> list[Issue]:
    issues = []
    for i, step in enumerate(_steps(doc)):
        role = step.get("role_code")
        if isinstance(role, str) and not role_exists(role):
            issues.append(Issue("E002", "error", f"/steps/{i}/role_code",
                                f"未知岗位编码: {role}"))
    return issues


def _validate_due_rules(doc: dict[str, Any]) -> list[Issue]:
    issues = []
    for i, step in enumerate(_steps(doc)):
        rule = step.get("due_rule")
        if not isinstance(rule, dict):
            continue
        kind, unit, value = rule.get("kind"), rule.get("unit"), rule.get("value")
        if kind not in DUE_KINDS:
            issues.append(Issue("E003", "error", f"/steps/{i}/due_rule/kind",
                                f"非法 due_rule.kind: {kind}"))
        if unit not in DUE_UNITS:
            issues.append(Issue("E003", "error", f"/steps/{i}/due_rule/unit",
                                f"非法 due_rule.unit: {unit}"))
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            issues.append(Issue("E003", "error", f"/steps/{i}/due_rule/value",
                                f"非法 due_rule.value: {value!r}"))
    return issues


def _validate_seq_unique(doc: dict[str, Any]) -> list[Issue]:
    seen: dict[int, int] = {}
    issues = []
    for i, step in enumerate(_steps(doc)):
        seq = step.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool):
            continue
        if seq in seen:
            issues.append(Issue("E004", "error", f"/steps/{i}/seq",
                                f"seq 重复: {seq}（首次出现在步骤 {seen[seq]}）"))
        else:
            seen[seq] = i
    return issues


def _validate_event(doc: dict[str, Any]) -> list[Issue]:
    trigger = doc.get("trigger")
    if not isinstance(trigger, dict):
        return []
    code = trigger.get("event_code")
    if isinstance(code, str) and not event_exists(code):
        return [Issue("E005", "error", "/trigger/event_code",
                      f"触发事件不在事件目录: {code}")]
    return []


def _validate_dependency_graph(doc: dict[str, Any]) -> list[Issue]:
    """depends_on 环检测 + 悬空引用检测。"""
    steps = _steps(doc)
    seqs = {s.get("seq") for s in steps if isinstance(s.get("seq"), int)}
    graph: dict[int, list[int]] = {}
    for s in steps:
        seq = s.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool):
            continue
        deps = [d for d in (s.get("depends_on") or []) if isinstance(d, int)]
        graph[seq] = deps

    issues: list[Issue] = []
    # 悬空引用
    for seq, deps in graph.items():
        for d in deps:
            if d not in seqs:
                issues.append(Issue("E006", "error", f"/steps/seq={seq}/depends_on",
                                    f"depends_on 引用不存在的步骤 seq: {d}"))
    # 环检测：DFS 三色标记
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    found: set[int] = set()

    def dfs(node: int, stack: list[int]) -> None:
        color[node] = GRAY
        stack.append(node)
        for nxt in graph.get(node, []):
            if nxt not in color:
                continue
            if color[nxt] == GRAY:
                cycle = stack[stack.index(nxt):] + [nxt]
                found.add(node)
                issues.append(Issue("E006", "error", "/steps/depends_on",
                                    "depends_on 存在环: " + " -> ".join(map(str, cycle))))
            elif color[nxt] == WHITE:
                dfs(nxt, stack)
        stack.pop()
        color[node] = BLACK

    for n in graph:
        if color[n] == WHITE:
            dfs(n, [])
    return issues


def _iter_conditions(doc: dict[str, Any]):
    """产出所有 (json_path, condition_dict)：触发条件 + 步骤条件 + 检查项 expr。"""
    trigger = doc.get("trigger")
    if isinstance(trigger, dict):
        for i, cond in enumerate(trigger.get("conditions") or []):
            if isinstance(cond, dict):
                yield f"/trigger/conditions/{i}", cond
    for i, step in enumerate(_steps(doc)):
        cond = step.get("condition")
        if isinstance(cond, dict):
            yield f"/steps/{i}/condition", cond
    for i, chk in enumerate(doc.get("checks") or []):
        if isinstance(chk, dict) and isinstance(chk.get("expr"), str):
            # expr 形如 "field=form.amount" 或直接字段路径
            expr = chk["expr"]
            field = expr.split("=", 1)[-1].strip() if "=" in expr else expr.strip()
            yield f"/checks/{i}/expr", {"field": field, "op": "exists", "value": None}


def _validate_field_paths(doc: dict[str, Any]) -> list[Issue]:
    issues = []
    for path, cond in _iter_conditions(doc):
        field = cond.get("field")
        if isinstance(field, str) and not field_path_allowed(field):
            issues.append(Issue("E007", "error", path + "/field",
                                f"非法字段路径: {field}"))
    return issues


def _steps(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in (doc.get("steps") or []) if isinstance(s, dict)]


def lint_doc(doc: Any, validator: Draft202012Validator | None = None) -> list[Issue]:
    """对单个模板文档执行全部 7 类检查；返回 Issue 列表。"""
    if validator is None:
        validator = Draft202012Validator(load_schema())
    if not isinstance(doc, dict):
        return [Issue("E001", "error", "/", "模板根节点须为 JSON 对象")]
    issues: list[Issue] = []
    issues += _validate_schema(doc, validator)
    issues += _validate_roles(doc)
    issues += _validate_due_rules(doc)
    issues += _validate_seq_unique(doc)
    issues += _validate_event(doc)
    issues += _validate_dependency_graph(doc)
    issues += _validate_field_paths(doc)
    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)
