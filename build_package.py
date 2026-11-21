# -*- coding: utf-8 -*-
"""从 U 盘源打确定性 zip（条目排序 + 固定时间戳），SHA256 稳定。"""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SRC = Path("F:/ClawHunt交付-20261119/2506-SOP模板JSON规范与sop-lint")
OUT = Path(__file__).resolve().parent
PKG = "S3-SOP-005-delivery-v1.zip"
BUNDLE = "S3-SOP-005-source.bundle"


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def main() -> None:
    mf = json.loads((SRC / "MANIFEST.json").read_text(encoding="utf-8"))
    expected = mf["files"]

    files = sorted(
        f for f in SRC.rglob("*")
        if f.is_file() and "__pycache__" not in f.parts and ".pytest_cache" not in f.parts
    )
    rels = [f.relative_to(SRC).as_posix() for f in files]
    listed = set(expected) | {"MANIFEST.json"}
    if set(rels) != listed:
        raise RuntimeError(
            f"USB file set drift: extra={sorted(set(rels)-listed)} missing={sorted(listed-set(rels))}"
        )
    for rel, meta in expected.items():
        blob = (SRC / rel).read_bytes()
        if len(blob) != meta["size"] or sha(blob) != meta["sha256"]:
            raise RuntimeError(f"USB hash drift: {rel}")
    print(f"USB source verified: {len(expected)} hashed files + MANIFEST.json")

    zpath = OUT / PKG
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f, rel in zip(files, rels):
            zi = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zf.writestr(zi, f.read_bytes())

    blob = zpath.read_bytes()
    (OUT / BUNDLE).write_bytes(blob)
    with zipfile.ZipFile(zpath) as zf:
        bad = zf.testzip()
        entries = zf.namelist()
    if bad is not None:
        raise RuntimeError(f"zip corrupt at {bad}")
    if entries != rels:
        raise RuntimeError("zip entry order/content mismatch")

    info = {
        "package": PKG,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(SRC),
        "bytes": len(blob),
        "sha256": sha(blob),
        "zip_entries": len(entries),
        "hashed_files": len(expected),
        "entries": entries,
        "note": "MANIFEST.json self-entry excluded from hash list; archive includes it for offline verification.",
    }
    (OUT / "package-info.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"PACKAGE {PKG}: {len(blob):,} B / {len(entries)} entries / sha256 {sha(blob)}")
    print(f"BUNDLE  {BUNDLE}: byte-identical")


if __name__ == "__main__":
    main()
