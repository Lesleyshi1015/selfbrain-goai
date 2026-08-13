# @agent: session-260809-grand-sunset | module: tests/test_agents | ts: 2026-08-09T13:06+08:00
"""
tests/test_agents.py — 6 个 Worker Agent 测试

覆盖：
    navigator  — do_work 读黑板→调用 engine.search→写回 navigator_result
    cipher     — do_work 读黑板→调用 engine.cipher_analyze→写回 cipher_result
    coordinator— do_work 读 navigator/cipher 结果→协调→写回 coordinator_result
    policy     — do_work 读 output_to_check→调用 engine.policy_check→写回 policy_result
    audit      — do_work 读黑板→生成审计条目→写回 audit_result
    validator  — validate 6维核查判定
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agent_teams_sdk import TeamRoom  # noqa: E402
from agent_teams_sdk.roles.validator import ValidationResult  # noqa: E402

# 导入各 Agent
from agents.navigator import MemoryNavigator  # noqa: E402
from agents.cipher import CipherGenerator  # noqa: E402
from agents.coordinator import DataCoordinator  # noqa: E402
from agents.policy import PolicyEnforcer  # noqa: E402
from agents.audit import AuditLogger  # noqa: E402
from agents.validator import Validator  # noqa: E402

# ---------------------------------------------------------------------------
# MemoryNavigator 测试
# ---------------------------------------------------------------------------


class TestMemoryNavigator:
    """Navigator Agent 测试"""

    @pytest.fixture
    def nav(self, team_room, engine_stub):
        # [G2-sbapi] @agent: session-260809-tidy-tide | module: tests | ts: 2026-08-13T20:41+08:00
        # 构造注入 engine（替代属性替换）：backend 缺省复用 engine，检索经 backend 透传
        n = MemoryNavigator("G4-navigator", team_room, engine=engine_stub)
        return n

    def test_do_work_reads_query_and_writes_result(self, nav, team_room, engine_stub):
        team_room.write("user_query", "我的密码在哪")
        result = nav.do_work({"action": "work"})

        assert result["status"] == "ok"
        assert result["component"] == "navigator"
        assert team_room.read("navigator_result") == result
        engine_stub.search.assert_called_once_with("我的密码在哪")

    def test_do_work_empty_query_returns_error_envelope(self, nav, team_room):
        # [转派修复·G2-sbapi] @agent: session-260809-tidy-tide | module: tests | ts: 2026-08-09T13:58+08:00
        # R2 P0-3：空查询不再抛异常，返回 error envelope 并写黑板（与 cipher.py 一致）
        team_room.write("user_query", "")
        result = nav.do_work({"action": "work"})
        assert result["status"] == "error"
        assert result["data"]["error"] == "user_query 为空"
        assert team_room.read("navigator_result")["status"] == "error"

    def test_do_work_no_query_key_returns_error_envelope(self, nav, team_room):
        # 未写入 user_query（R2 P0-3 修复后返回 error envelope，不抛异常）
        result = nav.do_work({"action": "work"})
        assert result["status"] == "error"
        assert result["data"]["error"] == "user_query 为空"
        assert team_room.read("navigator_result")["status"] == "error"

    def test_do_work_engine_exception_returns_error_envelope(self, nav, team_room, engine_stub):
        team_room.write("user_query", "test")
        engine_stub.search.side_effect = RuntimeError("search failed")

        result = nav.do_work({"action": "work"})

        assert result["status"] == "error"
        assert "search failed" in result["data"]["error"]
        assert team_room.read("navigator_result")["status"] == "error"


# ---------------------------------------------------------------------------
# CipherGenerator 测试
# ---------------------------------------------------------------------------


class TestCipherGenerator:
    """Cipher Agent 测试"""

    @pytest.fixture
    def cipher(self, team_room, engine_stub):
        c = CipherGenerator(team_room)
        c._engine = engine_stub
        return c

    def test_do_work_reads_query_and_writes_result(self, cipher, team_room, engine_stub):
        team_room.write("user_query", "加密这段文本")
        result = cipher.do_work({"action": "work"})

        assert result["component"] == "cipher"
        assert team_room.read("cipher_result") == result
        engine_stub.cipher_analyze.assert_called_once_with("加密这段文本")

    def test_do_work_custom_text_key(self, cipher, team_room, engine_stub):
        team_room.write("custom_key", "custom text")
        result = cipher.do_work({"action": "work", "text_key": "custom_key"})

        engine_stub.cipher_analyze.assert_called_once_with("custom text")

    def test_do_work_missing_text_returns_error(self, cipher, team_room, engine_stub):
        result = cipher.do_work({"action": "work", "text_key": "missing"})

        assert result["status"] == "error"
        assert "input_missing" in result["data"]["type"]

    def test_execute_writes_both_keys(self, cipher, team_room, engine_stub):
        team_room.write("user_query", "test")
        result = cipher.execute({"action": "work"})

        assert team_room.read("cipher_result") == result
        assert team_room.read("G5-cipher_result") == result


# ---------------------------------------------------------------------------
# DataCoordinator 测试
# ---------------------------------------------------------------------------


class TestDataCoordinator:
    """Coordinator Agent 测试"""

    @pytest.fixture
    def coord(self, team_room):
        return DataCoordinator(team_room)

    def test_do_work_reads_sources_and_writes_result(self, coord, team_room):
        team_room.write("navigator_result", {"nav": "data"})
        team_room.write("cipher_result", {"cipher": "data"})

        result = coord.do_work({"action": "work"})

        assert result["status"] == "coordinated"
        assert result["sources"]["navigator"] == {"nav": "data"}
        assert result["sources"]["cipher"] == {"cipher": "data"}
        assert team_room.read("coordinator_result") == result

    def test_do_work_merge_strategy_append(self, coord, team_room):
        team_room.write("navigator_result", [1, 2])
        team_room.write("cipher_result", [3, 4])

        result = coord.do_work({"action": "work", "merge_strategy": "append"})

        assert result["merged_data"] == [1, 2, 3, 4]

    def test_do_work_merge_strategy_dedup(self, coord, team_room):
        team_room.write("navigator_result", [1, 2, 2])
        team_room.write("cipher_result", [2, 3])

        result = coord.do_work({"action": "work", "merge_strategy": "dedup"})

        # 去重基于 str 表示
        assert len(result["merged_data"]) <= 4

    def test_do_work_no_sources(self, coord, team_room):
        result = coord.do_work({"action": "work"})

        assert result["merged_data"] == []
        assert result["conflicts"] == []

    def test_do_work_type_mismatch_conflict(self, coord, team_room):
        team_room.write("navigator_result", {"a": 1})
        team_room.write("cipher_result", [1, 2])

        result = coord.do_work({"action": "work"})

        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["type"] == "type_mismatch"

    def test_on_message_triggers_execute(self, team_room):
        coord = DataCoordinator(team_room)
        with patch.object(coord, "execute") as mock_exec:
            coord.on_message("@G6-coordinator hello")
            mock_exec.assert_called_once_with({"action": "coordinate"})

    def test_on_message_ignored_without_prefix(self, team_room):
        coord = DataCoordinator(team_room)
        with patch.object(coord, "execute") as mock_exec:
            coord.on_message("hello @G6-coordinator")
            mock_exec.assert_not_called()


# ---------------------------------------------------------------------------
# PolicyEnforcer 测试
# ---------------------------------------------------------------------------


class TestPolicyEnforcer:
    """Policy Agent 测试"""

    @pytest.fixture
    def policy(self, team_room, engine_stub):
        return PolicyEnforcer(team_room, engine_stub)

    def test_do_work_reads_from_blackboard(self, policy, team_room, engine_stub):
        team_room.write("output_to_check", "待发布文本")
        result = policy.do_work({"action": "work"})

        engine_stub.policy_check.assert_called_once_with("待发布文本")
        assert "allowed" in result
        assert team_room.read("policy_result") == result

    def test_do_work_text_in_task_overrides_blackboard(self, policy, team_room, engine_stub):
        team_room.write("output_to_check", "bb text")
        result = policy.do_work({"action": "work", "text": "task text"})

        engine_stub.policy_check.assert_called_once_with("task text")

    def test_do_work_missing_text_raises(self, policy, team_room, engine_stub):
        with pytest.raises(ValueError, match="未找到待校验文本"):
            policy.do_work({"action": "work"})

    def test_do_work_engine_error_returns_not_allowed(self, policy, team_room, engine_stub):
        team_room.write("output_to_check", "test")
        engine_stub.policy_check.return_value = {
            "status": "error",
            "data": {"error": "policy engine down"},
            "component": "broker",
        }

        result = policy.do_work({"action": "work"})

        assert result["allowed"] is False
        assert "策略引擎错误" in result["reason"]

    def test_do_work_pending_treated_as_allowed(self, policy, team_room, engine_stub):
        team_room.write("output_to_check", "test")
        # engine_stub 默认返回 pending
        result = policy.do_work({"action": "work"})

        assert result["allowed"] is True
        assert "Wave 2 补全" in result["reason"]


# ---------------------------------------------------------------------------
# AuditLogger 测试
# ---------------------------------------------------------------------------


class TestAuditLogger:
    """Audit Agent 测试"""

    @pytest.fixture
    def audit(self, team_room):
        return AuditLogger("G8-audit", team_room, write_file=False)

    def test_do_work_reads_blackboard_and_writes_audit(self, audit, team_room):
        team_room.write("navigator_result", {"status": "ok"})
        team_room.write("cipher_result", {"status": "pending"})

        result = audit.do_work({"action": "audit"})

        assert result["status"] == "completed"
        assert result["entries_count"] == 2
        assert team_room.read("audit_result") == result

    def test_do_work_empty_blackboard(self, audit, team_room):
        result = audit.do_work({"action": "audit"})

        assert result["status"] == "completed"
        assert result["entries_count"] == 1  # heartbeat
        assert result["entries"][0]["agent"] == "system"

    def test_build_audit_entries(self, audit):
        bb = {
            "navigator_result": {"status": "ok"},
            "cipher_result": None,  # 跳过
            "some_other": "value",  # 不在 AUDITED_KEYS
        }
        entries = audit._build_audit_entries(bb)

        assert len(entries) == 1
        assert entries[0]["agent"] == "navigator"
        assert entries[0]["operation"] == "blackboard_write"

    def test_summarize_value_truncation(self, audit):
        long_val = {"data": "x" * 500}
        summary = audit._summarize_value(long_val, max_len=50)
        # 实际长度约 64（JSON 前缀 + 截断标记）
        assert len(summary) <= 70
        assert "truncated" in summary

    def test_now_iso_format(self, audit):
        ts = audit._now_iso()
        assert "+08:00" in ts or "+0800" in ts.replace(":", "")

    def test_on_message_triggers_audit(self, team_room):
        audit = AuditLogger("G8-audit", team_room, write_file=False)
        with patch.object(audit, "execute") as mock_exec:
            audit.on_message("@G8-audit run audit")
            mock_exec.assert_called_once_with({"action": "audit"})

    def test_do_work_exception_returns_error_result(self, team_room):
        # 模拟 read_all 抛出异常
        bad_room = MagicMock()
        bad_room.read_all.side_effect = RuntimeError("read failed")
        audit = AuditLogger("G-audit", bad_room, write_file=False)

        result = audit.do_work({"action": "audit"})

        assert result["status"] == "error"
        assert "read failed" in result["error_message"]


# ---------------------------------------------------------------------------
# Validator 测试
# ---------------------------------------------------------------------------


class TestValidator:
    """Validator Agent 6维核查测试"""

    @pytest.fixture
    def validator(self, team_room):
        return Validator("G9-validator", team_room)

    # ---- completeness ----

    def test_check_completeness_all_present(self, validator):
        bb = {k: {} for k in [
            "guardian_result", "navigator_result", "cipher_result",
            "coordinator_result", "policy_result", "audit_result",
        ]}
        ok, errors, warnings = validator._check_completeness(bb)
        assert ok is True
        assert errors == []

    def test_check_completeness_missing_keys(self, validator):
        ok, errors, _ = validator._check_completeness({})
        assert ok is False
        assert len(errors) == 6  # 6 个期望键全缺失

    def test_check_completeness_none_value_warning(self, validator):
        bb = {"guardian_result": None}
        ok, _, warnings = validator._check_completeness(bb)
        # None 值产生 warning 而非 error
        assert any("None" in w for w in warnings)

    # ---- correctness ----

    def test_check_correctness_empty_dict(self, validator):
        bb = {"nav_result": {}}
        ok, errors, _ = validator._check_correctness(bb)
        assert ok is False
        assert any("空值" in e for e in errors)

    def test_check_correctness_error_status(self, validator):
        bb = {"nav_result": {"status": "error"}}
        ok, errors, _ = validator._check_correctness(bb)
        assert ok is False
        assert any("状态异常" in e for e in errors)

    def test_check_correctness_valid_result(self, validator):
        bb = {"nav_result": {"status": "ok", "data": {}}}
        ok, errors, _ = validator._check_correctness(bb)
        assert ok is True

    # ---- privacy ----

    def test_check_privacy_sensitive_keywords(self, validator):
        bb = {"query": "my password is 123456"}
        ok, errors, _ = validator._check_privacy(bb)
        assert ok is False
        assert any("password" in e for e in errors)

    def test_check_privacy_clean_text(self, validator):
        bb = {"query": "今天天气不错"}
        ok, errors, _ = validator._check_privacy(bb)
        assert ok is True

    # ---- consistency ----

    def test_check_consistency_timestamps_unordered(self, validator):
        bb = {
            "a_result": {"timestamp": "300"},
            "b_result": {"timestamp": "100"},
        }
        ok, _, warnings = validator._check_consistency(bb)
        assert ok is True  # 仅 warning
        assert any("乱序" in w for w in warnings)

    # ---- traceability ----

    def test_check_traceability_no_audit(self, validator):
        bb = {"some_result": {}}
        ok, errors, _ = validator._check_traceability(bb)
        assert ok is False
        assert any("audit" in e for e in errors)

    def test_check_traceability_with_audit(self, validator):
        bb = {"audit_result": {"session_id": "123", "trace_id": "abc", "span_id": "xyz"}}
        ok, errors, warnings = validator._check_traceability(bb)
        assert ok is True

    # ---- performance ----

    def test_check_performance_no_results(self, validator):
        # 使用空黑板来触发无结果 warning
        ok, _, warnings = validator._check_performance({})
        assert ok is True
        assert any("worker" in w for w in warnings)

    def test_check_performance_latency_exceeded(self, validator):
        bb = {"nav_result": {"latency_ms": 10000}}
        ok, errors, _ = validator._check_performance(bb)
        assert ok is False
        assert any("延迟超标" in e for e in errors)

    # ---- validate (integration) ----

    def test_validate_all_pass(self, validator):
        bb = {
            "guardian_result": {"status": "ok"},
            "navigator_result": {"status": "ok"},
            "cipher_result": {"status": "ok"},
            "coordinator_result": {"status": "ok"},
            "policy_result": {"status": "ok", "allowed": True},
            "audit_result": {
                "session_id": "1", "trace_id": "t", "span_id": "s",
                "entries": [],
            },
        }
        result = validator.validate(bb)
        assert result.passed is True
        assert result.errors == []

    def test_validate_non_dict_raises(self, validator):
        with pytest.raises(ValueError, match="必须为 dict"):
            validator.validate("not a dict")

    def test_validate_returns_warnings_not_errors(self, validator):
        bb = {
            "guardian_result": None,  # 既产生 warning 也产生 error
            "navigator_result": {"status": "ok"},
            "cipher_result": {"status": "ok"},
            "coordinator_result": {"status": "ok"},
            "policy_result": {"status": "ok"},
            "audit_result": {"session_id": "1", "trace_id": "t", "span_id": "s"},
        }
        result = validator.validate(bb)
        # None 值既产生 warning 也产生 error
        assert result.passed is False  # 因为有 error
        assert any("None" in w for w in result.warnings)
        assert any("None" in e for e in result.errors)
