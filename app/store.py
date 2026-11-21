# -*- coding: utf-8 -*-
"""内存模板仓储（依赖无；真实接入时替换为数据库实现，接口契约不变）。

预置一个合法模板作为导出样例。所有编码均为虚构测试数据。
"""
from __future__ import annotations

import copy
import hashlib
import json

SAMPLE_TEMPLATE: dict = {
    "schema_version": "1.0",
    "code": "SOP_MEMBER_ONBOARD",
    "name": "新会员入驻办理",
    "description": "虚构示例：从商机分派到会员正式入驻的标准流程。",
    "trigger": {
        "event_code": "EVT_MEMBER_ONBOARD",
        "conditions": [
            {"field": "ctx.member_level", "op": "in", "value": ["GOLD", "PLATINUM"]}
        ],
    },
    "steps": [
        {
            "seq": 1,
            "code": "STEP_VERIFY",
            "title": "资质核验",
            "role_code": "ROLE_SERVICE",
            "due_rule": {"kind": "after_trigger", "value": 2, "unit": "hour"},
            "depends_on": [],
            "doc_codes": ["DOC_ONBOARD_GUIDE"],
        },
        {
            "seq": 2,
            "code": "STEP_CONTRACT",
            "title": "合同签署",
            "role_code": "ROLE_LEGAL",
            "due_rule": {"kind": "after_prev_step", "value": 1, "unit": "day"},
            "depends_on": [1],
            "condition": {"field": "form.sign_type", "op": "eq", "value": "ELECTRONIC"},
            "doc_codes": ["DOC_CONTRACT_TPL"],
        },
        {
            "seq": 3,
            "code": "STEP_ARCHIVE",
            "title": "资料归档",
            "role_code": "ROLE_ADMIN",
            "due_rule": {"kind": "after_prev_step", "value": 1, "unit": "day"},
            "depends_on": [2],
        },
    ],
    "output_form": [
        {"key": "member_code", "label": "会员编号", "type": "string", "required": True},
        {"key": "sign_type", "label": "签署方式", "type": "enum",
         "options": ["ELECTRONIC", "PAPER"], "required": True},
        {"key": "amount", "label": "合同金额（分）", "type": "integer"},
    ],
    "checks": [
        {"code": "CHK_CONTRACT", "description": "合同已签署", "check_type": "attachment",
         "expr": "form.sign_type"},
        {"code": "CHK_AMOUNT", "description": "金额为正", "check_type": "value_range",
         "expr": "form.amount"},
    ],
    "assets": [
        {"code": "ASSET_GUIDE", "name": "入驻指引", "media_type": "application/pdf",
         "doc_code": "DOC_ONBOARD_GUIDE"},
    ],
}


class TemplateStore:
    """模板仓储：已发布模板与导入草稿使用互不重叠的 id 空间。

    - 已发布模板以业务 code 为 key（如 SOP_MEMBER_ONBOARD）。
    - 导入草稿以 draft_id 为 key，形如 ``draft-<12位十六进制>``，由模板内容
      确定性派生（同一内容重复导入得到同一 id，幂等），因此绝不会与业务
      code 碰撞。
    - get() 按 id 精确查找，不再用 ``published.get(id) or drafts.get(id)``
      的回退写法——该写法会让与已发布同 code 的草稿被 published 遮蔽，
      导致"导出→导入→再导出"读写的是同一份预置数据（往返假阳性）。
    """

    def __init__(self) -> None:
        self._published: dict[str, dict] = {
            SAMPLE_TEMPLATE["code"]: copy.deepcopy(SAMPLE_TEMPLATE),
        }
        self._drafts: dict[str, dict] = {}

    @staticmethod
    def make_draft_id(doc: dict) -> str:
        canonical = json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return "draft-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]

    def get(self, template_id: str) -> dict | None:
        # 精确查找：草稿 id 与已发布 code 分属不同命名空间，互不遮蔽。
        doc = self._drafts.get(template_id)
        if doc is None:
            doc = self._published.get(template_id)
        return copy.deepcopy(doc) if doc is not None else None

    def save_draft(self, doc: dict) -> str:
        draft_id = self.make_draft_id(doc)
        self._drafts[draft_id] = copy.deepcopy(doc)
        return draft_id

    def reset(self) -> None:
        self._drafts.clear()


STORE = TemplateStore()
