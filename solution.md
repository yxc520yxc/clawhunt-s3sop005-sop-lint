# 交付说明 | S3-SOP-005 SOP 模板 JSON 规范、导入导出与 sop-lint 命令

技术栈：Python 3.11+ / JSON Schema (Draft 2020-12) / FastAPI / pytest / jsonschema / GitHub Actions。全部标识与数据均为虚构测试值，不含真实客户/企业/个人信息。

**公开仓库（无需登录可 clone）**：https://github.com/yxc520yxc/clawhunt-s3sop005-sop-lint
**CI 实跑 run（conclusion=success，run #4）**：https://github.com/yxc520yxc/clawhunt-s3sop005-sop-lint/actions/runs/44856104182

## 一、交付物清单

| 交付物 | 位置 | 说明 |
|--------|------|------|
| JSON Schema | `schemas/sop-template.schema.json` | Draft 2020-12，定义模板/步骤/触发/输出表单/检查项/关联资产，为七个首批 SOP 配置文件的格式标准 |
| 导入导出接口 | `app/api.py` | `GET /api/sop/templates/{id}/export` 与 `POST /api/sop/templates/import`（导入为草稿） |
| sop-lint 命令 | `sop_lint.py` + `app/lint.py` | 校验 7 类错误，退出码语义，支持单文件/目录/`--json`，可 CI 运行 |
| 错误样例集 | `errors/E001..E007_*.json` | 每类错误一个样例文件（7 个） |
| 七个首批 SOP 配置 | `examples/SOP_*.json` | 符合 Schema 的合法配置 |
| 虚构目录 | `app/catalog.py` | 岗位/知识文档/事件类型字典（解析依据） |
| 测试 | `tests/test_acceptance.py` | 四条验收 + 健康检查（逐用例名输出） |
| CI | `.github/workflows/verify.yml` | 两 job 并行，上传 evidence artifact |
| CI 实跑证据 | `evidence/ci-run4/` | RUN_META.json + 逐用例日志 + lint 报告 |

## 二、四条验收标准对照（CI run #4 实证）

1. **导出→导入逐字段相等**：`test_1_export_import_roundtrip_field_equal -> PASS`。导出已发布模板→导入为草稿→**按导入返回的 draft_id 再导出草稿本体**，逐顶层字段与整体对象均相等，无 warnings。草稿 id 与业务 code 分属不同命名空间（`draft-<hash>` vs `SOP_*`），真实往返路径被覆盖。另有 `test_6_modified_draft_not_shadowed_by_published -> PASS` 差异探针：导入改过 name/description 的草稿后按 draft_id 导出，断言拿到的正是被修改的草稿本体、且与预置 published 有可见差异——锁定并修复了复核指出的往返假阳性缺陷（详见第六节）。CI 日志见 `evidence/ci-run4/pytest.log`。→ **PASS**。

2. **sop-lint 识别 ≥6 类错误、每类一个样例**：`test_2_lint_detects_at_least_six_error_categories -> PASS`。7 个样例文件命中 E001(schema 非法) / E002(岗位编码不存在) / E003(due_rule 非法) / E004(seq 重复) / E005(触发事件不在目录) / E006(depends_on 有环) / E007(条件字段路径非法) 全部 7 类。CI `evidence/ci-run4/lint-errors.json` 实测 codes=`['E001'…'E007']`。→ **PASS**。

3. **有错误时退出码非 0**：`test_3_lint_exit_code_nonzero_on_errors -> PASS`。单文件 E002 与错误样例目录均返回非 0，合法样例返回 0；CI 的 lint job 用 `test $RC -ne 0` 与合法样例 exit 0 双向断言，两步均 success。→ **PASS**。

4. **未解析引用进 warnings**：`test_4_unresolved_references_returned_as_warnings -> PASS`。注入 ROLE_GHOST / DOC_GHOST / EVT_GHOST，断言三者出现在 `warnings` 中，且导入返回的模板正文与提交内容逐字段相等（不静默丢弃、不改写）。→ **PASS**。

附加 `test_5_health -> PASS`（健康检查）、`test_6_modified_draft_not_shadowed_by_published -> PASS`（复核发现的往返假阳性回归探针，详见第六节）。CI 结果：**6 passed**。

## 三、CI 实跑记录

- 仓库：https://github.com/yxc520yxc/clawhunt-s3sop005-sop-lint （public）
- Run #4：https://github.com/yxc520yxc/clawhunt-s3sop005-sop-lint/actions/runs/44856104182 （conclusion=success，event=push，head=e5e5e6f，workflow=Verify #2506 Stage iii SOP 引擎与工作台）
- Job「验收测试 (pytest, 逐用例名)」：**success，20s**；pytest 1s / exit 0 / 6 passed（含 test_6 回归探针）；上传 artifact `verify-evidence`（pytest.log + timings.txt）。
- Job「sop-lint 自检 (退出码 + 类别覆盖)」：**success，13s**；合法样例 exit 0、错误样例 exit 1 且覆盖 7 类；上传 artifact `lint-evidence`（lint-valid.log + lint-errors.json）。
- 两 job 并行，均远低于任务约定的时间上限。CI 纯 Python、无外部服务依赖。
- 说明：run #1 因 workflow YAML 中 heredoc 顶格代码行导致解析失败（GitHub 未识别 jobs），已改为 `python -c` 单行断言；run #3 因 workflow 名称中 `#` 未加引号被 YAML 当注释（名称显示 `Verify`），已加引号；本 run #4 名称正确且两 job 全绿。

## 四、依赖、对接点与可重复性

- **依赖**：`requirements.txt`（fastapi / uvicorn / httpx / pytest / jsonschema / pydantic），无外部账号、无向境外发送数据的第三方 SDK。
- **可重复**：虚构夹具由 `_gen_fixtures.py` 确定性生成，测试前不依赖外部状态；错误样例集固定 7 个文件。
- **对接点**：真实接入时把内存仓储 `app/store.py` 换成数据库、把 `app/catalog.py` 换成真实编码目录服务；`sop_lint.py` / `app/lint.py` 与接口契约不变。README 已写明运行与测试方法。
- 本机一键复跑：`python run_verify.py`（写 RUN_LOG.txt，6 passed）。

## 五、复核意见闭环（Major 与 Minor 全部处理）

用户复核结论为"有条件放行，1 个 Major（往返测试假阳性）需修"，逐条闭环如下：

**🔴 Major — 验收1 假阳性（已修）**
- 根因：`app/store.py` 的 `get()` 为 `published.get(id) or drafts.get(id)`，草稿以业务 code 为键；导入与预置样例同 code 的草稿时被 published 遮蔽，"导出→导入→再导出"三次读同一份预置数据，断言恒真却与导入无关。用户差异探针坐实"导入改过 name/description 的草稿后按 draft_id 导出，返回的仍是原始 published"。
- 修复：草稿改用独立 `draft_id`（内容确定性派生的 `draft-<hash>`，与业务 code 不同命名空间），`get()` 按 id 精确查找；`test_1` 改为按 draft_id 回读草稿本体并断言导入响应正文相等；新增 `test_6` 差异探针，导入改名草稿后断言导出的是草稿本体且与 published 有可见差异，同时断言业务 code 仍导出原始 published（两条路径互不干扰）。
- 自证：回退 `store.py` 到缺陷版后 `test_6` FAIL（`AssertionError: 按 draft_id 导出未返回导入的草稿本体`），修复版 PASS——探针对该缺陷敏感。

**🟡 Minor（4 项已处理）**
1. 交付方式：本 `solution.md` 已纳入交付包（此前缺失），README 顶部与末尾均给出公开仓库/CI run 链接，引用不再悬空。
2. CI workflow 名称：由 `Verify S3-SOP-005` 改为 `Verify #2506 Stage iii SOP 引擎与工作台`，与工单号/阶段模块一致。
3. 校验规则双轨：README 第七节说明 Schema 层只校验字段路径格式、sop-lint E007 用白名单做语义收紧是有意设计，非规则冲突。
4. TestClient 弃用告警：`tests/conftest.py` 的 `pytest_configure` 抑制 httpx 弃用告警，日志无噪声。

## 六、下载与验证链接

源码包 `S3-SOP-005-delivery-v1.zip`：条目数与逐文件 SHA256 清单见随包 `MANIFEST.json`；包内含 39 个条目（38 个文件列入 SHA256 清单 + MANIFEST.json，含本 `solution.md` 与 CI 实跑证据 `evidence/ci-run4/`）。包字节数与包级 SHA256 在提交时随附的 assets 中给出（提交载荷的一部分，不在源码包内，避免自引用导致哈希漂移）。专属下载链接见随附 assets，均为本单专属命名并带 sharecode，不影响其他工单的公共附件路径。
