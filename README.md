# S3-SOP-005 · SOP 模板 JSON 规范、导入导出与 sop-lint 命令

任务 #2506 的完整交付：**JSON Schema + 导入导出接口 + sop-lint 命令行 + 错误样例集 + 虚构夹具 + 测试 + CI 配置**。代码放在公开仓库，附 CI 实跑记录。所有编码、组织、数据均为虚构测试值，不含真实客户/企业/个人信息。

**公开仓库**：https://github.com/yxc520yxc/clawhunt-s3sop005-sop-lint （无需登录即可 clone）
**CI 实跑（run #2，success）**：https://github.com/yxc520yxc/clawhunt-s3sop005-sop-lint/actions/runs/44854477546
- Job「验收测试」success 13s（pytest 5 passed，逐用例名），Job「sop-lint 自检」success 11s（合法样例 exit 0 / 错误样例 exit 1 且覆盖 E001–E007）。逐用例日志与 lint 报告见 `evidence/ci-run2/`。

## 一、交付内容

| 交付物 | 位置 | 说明 |
|--------|------|------|
| JSON Schema | `schemas/sop-template.schema.json` | Draft 2020-12，定义模板/步骤/触发/输出表单/检查项/关联资产，是七个首批 SOP 配置文件的格式标准 |
| 导入导出接口 | `app/api.py` | `GET /api/sop/templates/{id}/export`、`POST /api/sop/templates/import`（导入为草稿） |
| sop-lint 命令 | `sop_lint.py` + `app/lint.py` | 校验 7 类错误，退出码语义，可 CI 运行 |
| 错误样例集 | `errors/E001..E007_*.json` | 每类错误一个样例文件 |
| 七个首批 SOP 配置 | `examples/SOP_*.json` | 符合 Schema 的合法配置 |
| 虚构目录 | `app/catalog.py` | 岗位/知识文档/事件类型字典（解析依据） |
| 测试 | `tests/test_acceptance.py` | 四条验收 + 健康检查 |
| CI | `.github/workflows/verify.yml` | 两个并行 job，上传 evidence artifact |

## 二、sop-lint 检查的 7 类错误

| 码 | 类别 | 含义 |
|----|------|------|
| E001 | schema_invalid | 不符合 `sop-template.schema.json` |
| E002 | unknown_role | 步骤 `role_code` 不在岗位目录 |
| E003 | invalid_due_rule | `due_rule` kind/unit/value 非法 |
| E004 | duplicate_seq | 步骤 `seq` 重复 |
| E005 | unknown_event | 触发事件不在事件目录 |
| E006 | cyclic_dependency | `depends_on` 成环或引用不存在的步骤 |
| E007 | invalid_field_path | 条件表达式字段路径非法 |

任何 error 级问题 → 退出码 1；全部通过 → 0。支持单文件与目录递归，支持 `--json` 机器可读输出。

## 三、运行与测试

```bash
python -m pip install -r requirements.txt

# 生成虚构夹具与七个首批 SOP 配置 + 错误样例集
python _gen_fixtures.py

# sop-lint：合法样例应 0，错误样例应非 0
python sop_lint.py examples/
python sop_lint.py errors/          # 退出码 1

# 四条验收测试（逐用例名输出）
python -m pytest -v -s tests/

# 一键复跑（写 RUN_LOG.txt）
python run_verify.py
```

导入接口解析不到的岗位/文档/事件编码**不静默丢弃**，而是作为 `warnings` 返回，同时原样回传模板正文。

## 四、验收对照

1. **导出→导入逐字段相等**：`test_1_export_import_roundtrip_field_equal` 导出模板，导入为草稿，再导出，逐顶层字段与整体均相等，且无 warnings。
2. **≥6 类错误、每类一个样例**：`test_2_lint_detects_at_least_six_error_categories`，7 个样例文件命中 E001–E007 全部 7 类。
3. **错误时退出码非 0**：`test_3_lint_exit_code_nonzero_on_errors` 单文件与目录级均非 0，合法样例为 0。
4. **未解析引用进 warnings**：`test_4_unresolved_references_returned_as_warnings`（注入 ROLE_GHOST/DOC_GHOST/EVT_GHOST，断言出现在 warnings 且正文不被改写）。

## 五、依赖与对接点

- **无外部依赖**：内存仓储 `app/store.py` 预置样例，接口桩化即可运行（任务约定允许）。
- **对接点**：真实接入时把 `app/store.py` 换成数据库实现、`app/catalog.py` 换成真实编码目录服务；`sop_lint.py` / `app/lint.py` / 接口契约不变。
- **无向境外发送数据的第三方 SDK**。
- CI 在公开 GitHub 仓库推送时自动运行，run 链接与逐用例日志见交付说明 solution.md。
