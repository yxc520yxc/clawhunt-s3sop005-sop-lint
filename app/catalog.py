# -*- coding: utf-8 -*-
"""虚构的编码目录：岗位、知识文档、事件类型。

全部为测试数据，不含真实客户/企业/个人信息。sop-lint 与导入接口据此
解析引用；解析不到的编码不得静默丢弃，需作为 warnings 返回。
"""
from __future__ import annotations

# 岗位编码目录
ROLES: dict[str, str] = {
    "ROLE_SALES_MGR": "招商客户经理",
    "ROLE_SERVICE": "会员服务专员",
    "ROLE_CONTENT": "内容运营",
    "ROLE_LEGAL": "法务审核",
    "ROLE_FINANCE": "财务复核",
    "ROLE_ADMIN": "平台管理员",
}

# 知识文档编码目录
DOCS: dict[str, str] = {
    "DOC_ONBOARD_GUIDE": "会员入驻指引",
    "DOC_CONTRACT_TPL": "服务合同模板",
    "DOC_SOP_WRITING": "SOP 编写规范",
    "DOC_BRAND_KIT": "品牌素材包",
    "DOC_PRIVACY_POLICY": "数据处理须知",
}

# 事件类型目录
EVENTS: dict[str, str] = {
    "EVT_MEMBER_ONBOARD": "新会员入驻",
    "EVT_CONTRACT_SIGNED": "合同已签署",
    "EVT_LEAD_ASSIGNED": "商机已分派",
    "EVT_CONTENT_PUBLISH": "内容待发布",
    "EVT_TICKET_ESCALATE": "工单升级",
}

# due_rule 合法枚举（与 schema 保持一致）
DUE_KINDS: frozenset[str] = frozenset({"after_trigger", "after_prev_step", "calendar"})
DUE_UNITS: frozenset[str] = frozenset({"minute", "hour", "day", "business_day"})

# 条件表达式允许引用的字段路径（输入上下文 + 输出表单）
ALLOWED_FIELD_PATHS: set[str] = {
    "ctx.member_level",
    "ctx.org_size",
    "ctx.channel",
    "form.amount",
    "form.urgency",
    "form.sign_type",
    "form.content_category",
    "step.prev.status",
}


def role_exists(code: str) -> bool:
    return code in ROLES


def doc_exists(code: str) -> bool:
    return code in DOCS


def event_exists(code: str) -> bool:
    return code in EVENTS


def field_path_allowed(path: str) -> bool:
    return path in ALLOWED_FIELD_PATHS
