# -*- coding: utf-8 -*-
"""逐用例名打印结果，便于 CI 日志与报告中逐条核对。"""
import warnings

import pytest


def pytest_configure(config):
    # Starlette 的 TestClient 仍依赖 httpx，导入时触发弃用告警；功能不受影响，
    # 抑制该日志噪声。pytest_configure 在测试模块收集前执行，可覆盖 pytest 的
    # 默认 warning filter。
    warnings.filterwarnings("ignore", message=".*httpx.*")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        status = "PASS" if report.passed else ("FAIL" if report.failed else "SKIP")
        print(f"\n[CASE] {report.nodeid} -> {status}")
