# -*- coding: utf-8 -*-
"""把交付文件复制到 U 盘专属目录并生成 MANIFEST.json（自引用剔除）。

U 盘目录是提交包的唯一真源，复制后不再改动；build_package.py 从这里打包。
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

SRC = Path(__file__).resolve().parent
USB = Path("F:/ClawHunt交付-20261119/2506-SOP模板JSON规范与sop-lint")

# 需要纳入交付的文件（相对 SRC）
FILES = [
    ".github/workflows/verify.yml",
    ".gitignore",
    "README.md",
    "RUN_LOG.txt",
    "_gen_fixtures.py",
    "app/__init__.py",
    "app/api.py",
    "app/catalog.py",
    "app/lint.py",
    "app/store.py",
    "errors/E001_schema_invalid.json",
    "errors/E002_unknown_role.json",
    "errors/E003_invalid_due_rule.json",
    "errors/E004_duplicate_seq.json",
    "errors/E005_unknown_event.json",
    "errors/E006_cyclic_dependency.json",
    "errors/E007_invalid_field_path.json",
    "evidence/ci-run2/RUN_META.json",
    "evidence/ci-run2/pytest.log",
    "evidence/ci-run2/timings.txt",
    "evidence/ci-run2/lint-valid.log",
    "evidence/ci-run2/lint-errors.json",
    "examples/SOP_CONTENT_PUBLISH.json",
    "examples/SOP_CONTRACT_SIGN.json",
    "examples/SOP_FEEDBACK_CLOSE.json",
    "examples/SOP_LEAD_ASSIGN.json",
    "examples/SOP_MEMBER_ONBOARD.json",
    "examples/SOP_RENEW_REMIND.json",
    "examples/SOP_TICKET_ESCALATE.json",
    "examples/valid_template.json",
    "requirements.txt",
    "run_verify.py",
    "schemas/sop-template.schema.json",
    "solution.md",
    "sop_lint.py",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/test_acceptance.py",
]


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def main() -> None:
    USB.mkdir(parents=True, exist_ok=True)
    for rel in FILES:
        dst = USB / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SRC / rel, dst)

    # MANIFEST 自引用剔除：只为 FILES 计算哈希，不含 MANIFEST.json 本身
    files_meta: dict[str, dict] = {}
    for rel in FILES:
        blob = (USB / rel).read_bytes()
        files_meta[rel] = {"size": len(blob), "sha256": sha(blob)}
    manifest = {
        "package": "S3-SOP-005",
        "task_id": 2506,
        "description": "SOP 模板 JSON 规范、导入导出与 sop-lint 命令",
        "file_count": len(FILES),
        "note": "MANIFEST.json self-entry excluded from hash list. All identifiers are fictional test data.",
        "files": files_meta,
    }
    (USB / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"USB prepared: {USB}")
    print(f"hashed files: {len(FILES)} + MANIFEST.json")


if __name__ == "__main__":
    main()
