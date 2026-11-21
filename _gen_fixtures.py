# -*- coding: utf-8 -*-
"""一次性生成合法样例、七个首批 SOP 配置、七类错误样例。生成后可留作可复现脚本。"""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXAMPLES = ROOT / "examples"
ERRORS = ROOT / "errors"
EXAMPLES.mkdir(exist_ok=True)
ERRORS.mkdir(exist_ok=True)

BASE = {
    "schema_version": "1.0",
    "code": "SOP_MEMBER_ONBOARD",
    "name": "新会员入驻办理",
    "description": "虚构示例：从商机分派到会员正式入驻的标准流程。",
    "trigger": {
        "event_code": "EVT_MEMBER_ONBOARD",
        "conditions": [{"field": "ctx.member_level", "op": "in", "value": ["GOLD"]}],
    },
    "steps": [
        {"seq": 1, "code": "STEP_VERIFY", "title": "资质核验", "role_code": "ROLE_SERVICE",
         "due_rule": {"kind": "after_trigger", "value": 2, "unit": "hour"},
         "depends_on": [], "doc_codes": ["DOC_ONBOARD_GUIDE"]},
        {"seq": 2, "code": "STEP_CONTRACT", "title": "合同签署", "role_code": "ROLE_LEGAL",
         "due_rule": {"kind": "after_prev_step", "value": 1, "unit": "day"},
         "depends_on": [1], "condition": {"field": "form.sign_type", "op": "eq", "value": "ELECTRONIC"},
         "doc_codes": ["DOC_CONTRACT_TPL"]},
        {"seq": 3, "code": "STEP_ARCHIVE", "title": "资料归档", "role_code": "ROLE_ADMIN",
         "due_rule": {"kind": "after_prev_step", "value": 1, "unit": "day"},
         "depends_on": [2]},
    ],
    "output_form": [
        {"key": "member_code", "label": "会员编号", "type": "string", "required": True},
        {"key": "sign_type", "label": "签署方式", "type": "enum",
         "options": ["ELECTRONIC", "PAPER"], "required": True},
    ],
    "checks": [
        {"code": "CHK_CONTRACT", "description": "合同已签署", "check_type": "attachment",
         "expr": "form.sign_type"},
    ],
    "assets": [
        {"code": "ASSET_GUIDE", "name": "入驻指引", "media_type": "application/pdf",
         "doc_code": "DOC_ONBOARD_GUIDE"},
    ],
}


def dump(obj, fp: Path) -> None:
    fp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    # 合法样例
    dump(BASE, EXAMPLES / "valid_template.json")

    # 七个首批 SOP 配置文件（合法；仅改 code/name/trigger，同一结构骨架）
    seven = [
        ("SOP_MEMBER_ONBOARD", "新会员入驻办理", "EVT_MEMBER_ONBOARD"),
        ("SOP_CONTRACT_SIGN", "服务合同签署", "EVT_CONTRACT_SIGNED"),
        ("SOP_LEAD_ASSIGN", "商机分派与跟进", "EVT_LEAD_ASSIGNED"),
        ("SOP_CONTENT_PUBLISH", "内容发布审核", "EVT_CONTENT_PUBLISH"),
        ("SOP_TICKET_ESCALATE", "工单升级处置", "EVT_TICKET_ESCALATE"),
        ("SOP_RENEW_REMIND", "会籍续费提醒", "EVT_MEMBER_ONBOARD"),
        ("SOP_FEEDBACK_CLOSE", "客户反馈闭环", "EVT_TICKET_ESCALATE"),
    ]
    for code, name, evt in seven:
        d = copy.deepcopy(BASE)
        d["code"] = code
        d["name"] = name
        d["trigger"]["event_code"] = evt
        dump(d, EXAMPLES / f"{code}.json")

    # 七类错误样例：每个只破坏一处
    # E001 schema_invalid —— 缺必填字段 description_of_error（additionalProperties 也会报，但主要是缺 required）
    d = copy.deepcopy(BASE)
    d.pop("output_form")  # 缺必填字段
    dump(d, ERRORS / "E001_schema_invalid.json")

    # E002 unknown_role
    d = copy.deepcopy(BASE)
    d["steps"][0]["role_code"] = "ROLE_NOT_IN_CATALOG"
    dump(d, ERRORS / "E002_unknown_role.json")

    # E003 invalid_due_rule —— value=0（schema minimum=1 + lint 检查）
    d = copy.deepcopy(BASE)
    d["steps"][0]["due_rule"]["value"] = 0
    dump(d, ERRORS / "E003_invalid_due_rule.json")

    # E004 duplicate_seq
    d = copy.deepcopy(BASE)
    d["steps"][1]["seq"] = 1  # 与步骤 0 重复
    dump(d, ERRORS / "E004_duplicate_seq.json")

    # E005 unknown_event
    d = copy.deepcopy(BASE)
    d["trigger"]["event_code"] = "EVT_DOES_NOT_EXIST"
    dump(d, ERRORS / "E005_unknown_event.json")

    # E006 cyclic_dependency —— 1->2->3->1（同时 schema 仍合法）
    d = copy.deepcopy(BASE)
    d["steps"][0]["depends_on"] = [3]  # 步骤1依赖步骤3，步骤3依赖步骤2，步骤2依赖步骤1 => 环
    dump(d, ERRORS / "E006_cyclic_dependency.json")

    # E007 invalid_field_path
    d = copy.deepcopy(BASE)
    d["trigger"]["conditions"][0]["field"] = "ctx.not_allowed_field"
    dump(d, ERRORS / "E007_invalid_field_path.json")

    print("generated:", len(list(EXAMPLES.glob('*.json'))), "examples,",
          len(list(ERRORS.glob('*.json'))), "error samples")


if __name__ == "__main__":
    main()
