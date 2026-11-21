# -*- coding: utf-8 -*-
"""逐用例名打印结果，便于 CI 日志与报告中逐条核对。"""
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        status = "PASS" if report.passed else ("FAIL" if report.failed else "SKIP")
        print(f"\n[CASE] {report.nodeid} -> {status}")
