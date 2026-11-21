# -*- coding: utf-8 -*-
"""#2506 四条验收标准测试。

1. 导出再导入后模板内容逐字段相等（往返测试）
2. sop-lint 能识别 ≥ 6 类错误，每类有一个错误样例文件
3. 存在错误时 sop-lint 退出码非 0
4. 导入时解析不到的引用出现在 warnings 中
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.lint import lint_doc, load_schema
from app.store import SAMPLE_TEMPLATE, STORE
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
ERRORS = ROOT / "errors"
EXAMPLES = ROOT / "examples"
CLIENT = TestClient(app)


# ---------- 验收 1：往返逐字段相等 ----------
def test_1_export_import_roundtrip_field_equal():
    """真实往返：导出 →（作为草稿）导入 → 按 draft_id 再导出。

    用导入响应返回的 draft_id 回读草稿本体，而不是用业务 code 回读已发布样例——
    后者会被预置 published 遮蔽，使断言与导入内容无关（复核发现的假阳性）。
    """
    STORE.reset()
    code = SAMPLE_TEMPLATE["code"]
    r = CLIENT.get(f"/api/sop/templates/{code}/export")
    assert r.status_code == 200, r.text
    exported = r.json()

    rr = CLIENT.post("/api/sop/templates/import", json={"template": exported})
    assert rr.status_code == 200, rr.text
    imported = rr.json()
    assert imported["status"] == "imported_as_draft"
    assert imported["warnings"] == [], imported["warnings"]
    draft_id = imported["draft_id"]
    assert draft_id != code, "草稿 id 必须与已发布业务 code 分离"
    assert imported["template"] == exported, "导入响应正文须与提交内容逐字段相等"

    # 按 draft_id 回读草稿本体（真实往返路径）
    r2 = CLIENT.get(f"/api/sop/templates/{draft_id}/export")
    assert r2.status_code == 200, r2.text
    reexported = r2.json()
    assert reexported == exported, "导出→导入→按 draft_id 再导出 不是逐字段相等"
    for key in exported:
        assert reexported[key] == exported[key], f"字段漂移: {key}"


# ---------- 回归探针：坐实往返假阳性缺陷已修 ----------
def test_6_modified_draft_not_shadowed_by_published():
    """差异探针：导入一个改过 name/description 的草稿，按 draft_id 导出。

    修复前 get() 以业务 code 优先，草稿被同 code 的 published 遮蔽，导出拿到
    原始样例（改过的草稿无法导出）。此测试锁定该回归：必须返回草稿本体，
    且与预置 published 有可见差异。
    """
    STORE.reset()
    code = SAMPLE_TEMPLATE["code"]
    modified = copy.deepcopy(SAMPLE_TEMPLATE)
    modified["name"] = "【往返探针】改名后的草稿"
    modified["description"] = "【往返探针】此描述仅存在于导入草稿，published 中没有"
    assert modified != SAMPLE_TEMPLATE  # 确保差异真实存在

    rr = CLIENT.post("/api/sop/templates/import", json={"template": modified})
    assert rr.status_code == 200, rr.text
    draft_id = rr.json()["draft_id"]

    # 按草稿 id 导出：必须等于被修改的草稿本体
    got = CLIENT.get(f"/api/sop/templates/{draft_id}/export")
    assert got.status_code == 200, got.text
    assert got.json() == modified, "按 draft_id 导出未返回导入的草稿本体"
    assert got.json()["name"] == modified["name"]
    # 关键：不得等于预置 published（这才是原缺陷——假阳性来源）
    assert got.json() != SAMPLE_TEMPLATE, "导出仍命中 published，往返假阳性未修"
    assert got.json()["name"] != SAMPLE_TEMPLATE["name"]

    # 业务 code 仍导出原始 published，两条路径互不干扰
    pub = CLIENT.get(f"/api/sop/templates/{code}/export")
    assert pub.status_code == 200 and pub.json() == SAMPLE_TEMPLATE


# ---------- 验收 2：≥6 类错误，每类一个样例文件 ----------
def test_2_lint_detects_at_least_six_error_categories():
    validator = Draft202012Validator(load_schema())
    files = sorted(ERRORS.glob("E0*_*.json"))
    assert len(files) >= 6, f"错误样例文件不足 6 个: {len(files)}"

    detected_codes: set[str] = set()
    per_file: dict[str, set[str]] = {}
    for fp in files:
        doc = json.loads(fp.read_text(encoding="utf-8"))
        issues = lint_doc(doc, validator)
        codes = {i.code for i in issues if i.severity == "error"}
        detected_codes |= codes
        per_file[fp.name] = codes

    assert len(detected_codes) >= 6, f"识别到的错误类别不足 6: {sorted(detected_codes)}"
    expected = {"E001", "E002", "E003", "E004", "E005", "E006", "E007"}
    assert expected.issubset(detected_codes), f"缺少类别: {expected - detected_codes}"
    # 每个样例文件至少命中其文件名对应的主错误码
    for fp in files:
        primary = fp.name[:4]  # E001..E007
        assert primary in per_file[fp.name], f"{fp.name} 未命中主错误码 {primary}: {per_file[fp.name]}"


# ---------- 验收 3：存在错误时退出码非 0 ----------
def test_3_lint_exit_code_nonzero_on_errors():
    bad = ERRORS / "E002_unknown_role.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "sop_lint.py"), str(bad)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    assert proc.returncode != 0, f"含错误文件应返回非 0，实际 {proc.returncode}\n{proc.stdout}\n{proc.stderr}"
    assert "E002" in proc.stdout, proc.stdout

    # 目录级（含错误）也非 0
    proc_dir = subprocess.run(
        [sys.executable, str(ROOT / "sop_lint.py"), str(ERRORS)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    assert proc_dir.returncode != 0

    # 合法样例返回 0
    ok = subprocess.run(
        [sys.executable, str(ROOT / "sop_lint.py"), str(ROOT / "examples" / "valid_template.json")],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr


# ---------- 验收 4：解析不到的引用进 warnings ----------
def test_4_unresolved_references_returned_as_warnings():
    doc = json.loads((EXAMPLES / "valid_template.json").read_text(encoding="utf-8"))
    # 注入三类解析不到的引用：岗位 / 知识文档 / 事件
    doc["steps"][0]["role_code"] = "ROLE_GHOST"
    doc["steps"][0]["doc_codes"] = ["DOC_GHOST"]
    doc["trigger"]["event_code"] = "EVT_GHOST"
    doc["assets"][0]["doc_code"] = "DOC_GHOST_2"

    r = CLIENT.post("/api/sop/templates/import", json={"template": doc})
    assert r.status_code == 200, r.text
    body = r.json()
    warnings = body["warnings"]
    assert warnings, "解析不到的引用应产生 warnings"
    joined = " | ".join(warnings)
    assert "ROLE_GHOST" in joined, joined
    assert "DOC_GHOST" in joined, joined
    assert "EVT_GHOST" in joined, joined
    # 不得静默丢弃：模板原文原样返回
    assert body["template"] == doc, "导入返回的模板与提交内容不一致（疑似静默改写）"


def test_5_health():
    r = CLIENT.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
