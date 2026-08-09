# @agent: session-260809-grand-sunset | module: tests/test_demo | ts: 2026-08-09T13:06+08:00
"""
tests/test_demo.py — demo 冒烟测试

覆盖：
    - demo 模块可 import
    - main() 在 stub 模式下可执行（不加载真实模型）
    - 各内部函数可独立调用

注意：demo.py 在 import 时会修改 sys.stdout/sys.stderr（Windows UTF-8 兼容），
因此不在模块级别 import demo，而是在测试函数内部延迟导入。
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


def _import_demo():
    """延迟导入 demo 模块（避免模块级 import 触发 sys.stdout 修改）。"""
    # 确保 src/ 在 sys.path 中
    from pathlib import Path
    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    import demo
    return demo


# ---------------------------------------------------------------------------
# Import 测试
# ---------------------------------------------------------------------------


class TestDemoImport:
    """demo 模块导入测试"""

    def test_demo_importable(self):
        """demo 模块应可导入"""
        demo = _import_demo()
        assert hasattr(demo, "main")
        assert hasattr(demo, "_try_create_engine")
        assert hasattr(demo, "_run_workers")
        assert hasattr(demo, "_run_skills")
        assert hasattr(demo, "_run_validator")
        assert hasattr(demo, "_generate_report")

    def test_main_function_exists(self):
        demo = _import_demo()
        assert callable(demo.main)


# ---------------------------------------------------------------------------
# _generate_report 测试
# ---------------------------------------------------------------------------


class TestGenerateReport:
    """_generate_report 测试"""

    def test_report_contains_header(self):
        demo = _import_demo()
        report = demo._generate_report(
            query="test",
            guardian_result={"status": "ok"},
            completeness=0.8,
            blackboard={},
            skills_result={},
            validator_result=MagicMock(passed=True, errors=[], warnings=[]),
            elapsed_ms=100.0,
            mode="stub",
        )
        assert "SelfBrain-GOAI" in report
        assert "test" in report

    def test_report_contains_skills_section(self):
        demo = _import_demo()
        skills_result = {
            "privacy_shield": {"risk_level": "low", "detected": []},
            "memory_probe": {"expanded": [], "decomposed": []},
            "data_fusion": {"fused": [], "deduped": 0},
            "access_control": {"allowed": True, "rule": "MATCH"},
            "audit_trail": {"entries": [], "summary": {"total": 0}},
            "result_verify": {"passed": True, "score": 1.0},
        }
        report = demo._generate_report(
            query="q",
            guardian_result={},
            completeness=0.5,
            blackboard={},
            skills_result=skills_result,
            validator_result=MagicMock(passed=True, errors=[], warnings=[]),
            elapsed_ms=50.0,
            mode="stub",
        )
        assert "PrivacyShield" in report
        assert "MemoryProbe" in report
        assert "DataFusion" in report
        assert "AccessControl" in report
        assert "AuditTrail" in report
        assert "ResultVerify" in report

    def test_report_contains_validator_section(self):
        demo = _import_demo()
        report = demo._generate_report(
            query="q",
            guardian_result={},
            completeness=0.5,
            blackboard={},
            skills_result={},
            validator_result=MagicMock(passed=False, errors=["err1"], warnings=["warn1"]),
            elapsed_ms=50.0,
            mode="stub",
        )
        assert "Validator" in report or "核查" in report
        assert "err1" in report


# ---------------------------------------------------------------------------
# _run_skills 测试
# ---------------------------------------------------------------------------


class TestRunSkills:
    """_run_skills 测试"""

    def test_run_skills_returns_results(self):
        demo = _import_demo()
        blackboard = {
            "navigator_result": {"status": "ok"},
            "cipher_result": {"status": "pending"},
        }
        result = demo._run_skills("test query", blackboard)

        assert "privacy_shield" in result
        assert "memory_probe" in result
        assert "data_fusion" in result
        assert "access_control" in result
        assert "audit_trail" in result
        assert "result_verify" in result


# ---------------------------------------------------------------------------
# _run_validator 测试
# ---------------------------------------------------------------------------


class TestRunValidator:
    """_run_validator 测试"""

    def test_run_validator_returns_result(self):
        demo = _import_demo()
        blackboard = {
            "guardian_result": {"status": "ok"},
            "navigator_result": {"status": "ok"},
            "cipher_result": {"status": "ok"},
            "coordinator_result": {"status": "ok"},
            "policy_result": {"status": "ok"},
            "audit_result": {"session_id": "1", "trace_id": "t", "span_id": "s"},
        }
        result = demo._run_validator(blackboard)

        assert hasattr(result, "passed")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")


# ---------------------------------------------------------------------------
# main() stub 模式测试（需要 patch sys.stdout 干扰）
# ---------------------------------------------------------------------------


class TestDemoMain:
    """main() 函数测试"""

    @pytest.fixture(autouse=True)
    def restore_stdout(self):
        """每个测试后恢复 sys.stdout"""
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        yield
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr

    def test_main_stub_mode_returns_zero(self):
        demo = _import_demo()
        with patch.object(demo, "_try_create_engine") as mock_try:
            mock_engine = MagicMock()
            mock_engine.unload_all.return_value = {"status": "ok", "data": {}}
            mock_try.return_value = (mock_engine, False)

            with patch.object(demo, "_board_update"):
                ret = demo.main(["我的隐私数据在哪里"])

        assert ret == 0

    def test_main_default_query(self):
        demo = _import_demo()
        with patch.object(demo, "_try_create_engine") as mock_try:
            mock_engine = MagicMock()
            mock_engine.unload_all.return_value = {"status": "ok", "data": {}}
            mock_try.return_value = (mock_engine, False)

            with patch.object(demo, "_board_update"):
                ret = demo.main([])

        assert ret == 0

    def test_main_calls_try_create_engine(self):
        demo = _import_demo()
        with patch.object(demo, "_try_create_engine") as mock_try:
            mock_engine = MagicMock()
            mock_engine.unload_all.return_value = {"status": "ok", "data": {}}
            mock_try.return_value = (mock_engine, False)

            with patch.object(demo, "_board_update"):
                demo.main(["test"])

            mock_try.assert_called_once()


# ---------------------------------------------------------------------------
# _try_create_engine 测试
# ---------------------------------------------------------------------------


class TestTryCreateEngine:
    """_try_create_engine 测试"""

    def test_stub_mode_returns_engine(self):
        demo = _import_demo()
        with patch("demo.create_engine") as mock_ce:
            mock_engine = MagicMock()
            mock_ce.return_value = mock_engine
            engine, is_real = demo._try_create_engine(False)

        assert is_real is False
        assert engine is mock_engine

    def test_real_mode_success(self):
        demo = _import_demo()
        with patch("demo.create_engine") as mock_ce:
            mock_engine = MagicMock()
            mock_engine.decompose.return_value = {"status": "ok"}
            mock_ce.return_value = mock_engine
            engine, is_real = demo._try_create_engine(True)

        assert is_real is True

    def test_real_mode_falls_back_to_stub(self):
        demo = _import_demo()
        with patch("demo.create_engine") as mock_ce:
            mock_stub = MagicMock()
            mock_ce.side_effect = [RuntimeError("fail"), mock_stub]
            engine, is_real = demo._try_create_engine(True)

        assert is_real is False
        assert engine is mock_stub
