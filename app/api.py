# -*- coding: utf-8 -*-
"""FastAPI 接口：SOP 模板导出 / 导入。

- GET  /api/sop/templates/{id}/export       按编码导出模板（逐字段一致）
- POST /api/sop/templates/import            导入为草稿；岗位/文档/事件编码按目录解析，
                                            解析不到的引用进 warnings，不静默丢弃。
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from .catalog import role_exists, doc_exists, event_exists
from .store import STORE

app = FastAPI(title="SOP 模板交换接口", version="1.0")


class ImportRequest(BaseModel):
    template: dict[str, Any] = Field(..., description="符合 sop-template.schema.json 的模板对象")


class ImportResponse(BaseModel):
    status: str
    draft_id: str
    template: dict[str, Any]
    warnings: list[str]


@app.get("/api/sop/templates/{template_id}/export")
def export_template(template_id: str) -> dict[str, Any]:
    doc = STORE.get(template_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"模板不存在: {template_id}")
    return doc


@app.post("/api/sop/templates/import", response_model=ImportResponse)
def import_template(req: ImportRequest) -> ImportResponse:
    doc = req.template
    warnings: list[str] = []

    # 岗位编码解析
    for i, step in enumerate(doc.get("steps") or []):
        role = step.get("role_code")
        if isinstance(role, str) and not role_exists(role):
            warnings.append(f"/steps/{i}/role_code: 未解析到岗位编码 {role!r}")
        for j, dc in enumerate(step.get("doc_codes") or []):
            if isinstance(dc, str) and not doc_exists(dc):
                warnings.append(f"/steps/{i}/doc_codes/{j}: 未解析到知识文档编码 {dc!r}")

    # 触发事件解析
    trigger = doc.get("trigger") or {}
    ec = trigger.get("event_code")
    if isinstance(ec, str) and not event_exists(ec):
        warnings.append(f"/trigger/event_code: 未解析到事件类型编码 {ec!r}")

    # 关联资产来源文档解析
    for i, asset in enumerate(doc.get("assets") or []):
        dc = asset.get("doc_code")
        if isinstance(dc, str) and not doc_exists(dc):
            warnings.append(f"/assets/{i}/doc_code: 未解析到知识文档编码 {dc!r}")

    draft_id = STORE.save_draft(doc)
    return ImportResponse(
        status="imported_as_draft",
        draft_id=draft_id,
        template=doc,
        warnings=warnings,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
