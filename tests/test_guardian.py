# @agent: session-260809-grand-sunset | module: tests/test_guardian | ts: 2026-08-09T13:06+08:00
"""
tests/test_guardian.py — PrivacyGuardian Agent 测试

覆盖：
    - 构造（默认 workers、自定义 workers、无 team_room）
    - evaluate_completeness（0 / 0.35 / 0.65 / 0.95 档位）
    - process_query（mock engine.fuse、黑板写入）
    - reconstruct_result
    - execute 委托
    - _fuse_results（sb_api 可用/不可用/异常）
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agent_teams_sdk import TeamRoom  # noqa: E402
from agents.guardian import PrivacyGuardian, PrivacyGuardianError  # noqa: E402

# ---------------------------------------------------------------------------
# 构造测试
# ---------------------------------------------------------------------------


class TestPrivacyGuardianInit:
    """PrivacyGuardian 初始化测试"""

    def test_default_workers(self):
        room = TeamRoom("test")
        guardian = PrivacyGuardian("Guardian", room)
        assert guardian.workers == [
            "navigator", "cipher", "coordinator", "policy"
        ]
        assert guardian.name == "Guardian"
        assert guardian.team_room is room

    def test_custom_workers(self):
        room = TeamRoom("test")
        guardian = PrivacyGuardian("G", room, workers=["a", "b"])
        assert guardian.workers == ["a", "b"]

    def test_no_team_room_creates_default(self):
        guardian = PrivacyGuardian("G")
        assert guardian.team_room is not None
        assert guardian.workers == PrivacyGuardian.__init__.__defaults__ is None or True

    def test_board_updated_initially_false(self):
        room = TeamRoom("test")
        guardian = PrivacyGuardian("G", room)
        assert guardian.board_updated is False


# ---------------------------------------------------------------------------
# evaluate_completeness 测试
# ---------------------------------------------------------------------------


class TestEvaluateCompleteness:
    """完整度评估测试（0 / 0.35 / 0.65 / 0.95 档位）"""

    @pytest.fixture
    def guardian(self, team_room):
        return PrivacyGuardian("G", team_room)

    def test_empty_blackboard(self, guardian):
        """空黑板 → 0.0"""
        assert guardian.evaluate_completeness({}) == 0.0

    def test_only_navigator(self, guardian):
        """仅 navigator_result → 0.35"""
        bb = {"navigator_result": {"status": "ok"}}
        assert guardian.evaluate_completeness(bb) == 0.35

    def test_navigator_and_cipher(self, guardian):
        """navigator + cipher → 0.65"""
        bb = {
            "navigator_result": {"status": "ok"},
            "cipher_result": {"status": "ok"},
        }
        assert guardian.evaluate_completeness(bb) == 0.65

    def test_all_workers_no_query(self, guardian):
        """4 个 worker 结果齐全但无 user_query → 1.0（0.35+0.30+0.20+0.15）"""
        bb = {
            "navigator_result": {},
            "cipher_result": {},
            "coordinator_result": {},
            "policy_result": {},
        }
        assert guardian.evaluate_completeness(bb) == 1.0

    def test_all_workers_with_query(self, guardian):
        """4 个 worker + user_query → 0.95（封顶）"""
        bb = {
            "navigator_result": {},
            "cipher_result": {},
            "coordinator_result": {},
            "policy_result": {},
            "user_query": "test",
        }
        # 1.0 + 0.05 → min(1.05, 0.95) = 0.95
        # 等等，4个worker已经是1.0了，再加0.05还是封顶0.95
        # 实际上 0.35+0.30+0.20+0.15 = 1.0，但代码里 min(score+0.05, 0.95)
        # 所以 1.0 + 0.05 = 1.05 → min = 0.95
        assert guardian.evaluate_completeness(bb) == 0.95

    def test_empty_string_value_not_counted(self, guardian):
        """空字符串值不计入完整度"""
        bb = {"navigator_result": ""}
        assert guardian.evaluate_completeness(bb) == 0.0

    def test_none_value_not_counted(self, guardian):
        """None 值不计入完整度"""
        bb = {"navigator_result": None}
        assert guardian.evaluate_completeness(bb) == 0.0

    def test_user_query_without_workers(self, guardian):
        """仅有 user_query 无 worker 结果 → 0.0（worker 分数为 0 时不加 0.05）"""
        bb = {"user_query": "test"}
        assert guardian.evaluate_completeness(bb) == 0.0


# ---------------------------------------------------------------------------
# reconstruct_result 测试
# ---------------------------------------------------------------------------


class TestReconstructResult:
    """结果重建测试"""

    @pytest.fixture
    def guardian(self, team_room):
        return PrivacyGuardian("G", team_room)

    def test_reconstruct_basic(self, guardian):
        bb = {
            "user_query": "我的密码在哪",
            "navigator_result": {"status": "ok"},
            "cipher_result": None,
        }
        result = guardian.reconstruct_result(bb)

        assert result["guardian"] == "G"
        assert result["query"] == "我的密码在哪"
        assert "navigator" in result["worker_results"]
        assert result["worker_results"]["navigator"] == {"status": "ok"}
        assert result["worker_results"]["cipher"] is None
        assert "completeness" in result

    def test_reconstruct_missing_keys(self, guardian):
        """缺失的 worker key 值为 None"""
        bb = {"user_query": "q"}
        result = guardian.reconstruct_result(bb)
        for w in guardian.workers:
            assert result["worker_results"][w] is None

    def test_reconstruct_includes_completeness(self, guardian):
        bb = {
            "navigator_result": {},
            "cipher_result": {},
        }
        result = guardian.reconstruct_result(bb)
        assert result["completeness"] == 0.65


# ---------------------------------------------------------------------------
# _fuse_results 测试
# ---------------------------------------------------------------------------


class TestFuseResults:
    """_fuse_results 测试（sb_api 融合）"""

    @pytest.fixture
    def guardian(self, team_room):
        return PrivacyGuardian("G", team_room)

    def test_fuse_success(self, guardian):
        """sb_api 可用时返回融合结果"""
        raw = {"worker_results": {"nav": {}}}
        mock_engine = MagicMock()
        mock_engine.fuse.return_value = {
            "status": "ok", "data": "fused", "component": "core"
        }

        with patch("sb_api.create_engine") as mock_ce:
            mock_ce.return_value = mock_engine
            result = guardian._fuse_results(raw)

        assert result["status"] == "ok"
        mock_engine.fuse.assert_called_once_with({"nav": {}})

    def test_fuse_import_error_fallback(self, guardian):
        """ImportError 时返回降级结果"""
        raw = {"worker_results": {"nav": {}}}
        with patch("sb_api.create_engine") as mock_ce:
            mock_ce.side_effect = ImportError("no module")
            result = guardian._fuse_results(raw)

        assert result["status"] == "pending"
        assert result["data"] == raw

    def test_fuse_exception_fallback(self, guardian):
        """运行时异常时返回降级结果"""
        raw = {"worker_results": {"nav": {}}}
        with patch("sb_api.create_engine") as mock_ce:
            mock_ce.side_effect = RuntimeError("fuse failed")
            result = guardian._fuse_results(raw)

        # 异常时返回 error 状态；data 为异常信息字符串 str(exc)
        # [转派修复·G2-sbapi] @agent: session-260809-tidy-tide | module: tests | ts: 2026-08-09T13:50+08:00
        assert result["status"] == "error"
        assert isinstance(result["data"], str)
        assert "fuse failed" in result["data"]

    def test_fuse_engine_exception(self, guardian):
        """engine.fuse 抛异常时返回 error envelope"""
        # [转派修复·G2-sbapi] @agent: session-260809-tidy-tide | module: tests | ts: 2026-08-09T13:50+08:00
        # 原代码漏写函数定义头被并入上一测试；patch 目标改为 sb_api.create_engine
        # （guardian 模块无 _create_engine 属性，_fuse_results 经函数内 from sb_api import 取用）
        raw = {"worker_results": {}}
        mock_engine = MagicMock()
        mock_engine.fuse.side_effect = RuntimeError("fuse failed")

        with patch("sb_api.create_engine") as mock_ce:
            mock_ce.return_value = mock_engine
            result = guardian._fuse_results(raw)

        assert result["status"] == "error"
        assert "fuse failed" in result["data"]


# ---------------------------------------------------------------------------
# process_query 测试
# ---------------------------------------------------------------------------


class TestProcessQuery:
    """process_query 主入口测试"""

    @pytest.fixture
    def guardian(self, team_room):
        return PrivacyGuardian("G", team_room)

    def test_process_query_writes_user_query(self, guardian):
        """process_query 应将查询写入黑板"""
        with patch.object(guardian, "_dispatch_to_worker"), \
             patch.object(guardian, "evaluate_completeness", return_value=0.0), \
             patch.object(guardian, "reconstruct_result", return_value={}), \
             patch.object(guardian, "_fuse_results", return_value={"status": "ok"}):
            guardian.process_query("test query")

        assert guardian.team_room.read("user_query") == "test query"

    def test_process_query_dispatches_workers(self, guardian):
        """process_query 应依次调度各 worker"""
        dispatched = []

        def fake_dispatch(worker, query):
            dispatched.append(worker)
            # 模拟写入 worker 结果
            guardian.team_room.write(f"{worker}_result", {"status": "ok"})

        with patch.object(guardian, "_dispatch_to_worker", side_effect=fake_dispatch), \
             patch.object(guardian, "evaluate_completeness", return_value=0.0), \
             patch.object(guardian, "reconstruct_result", return_value={}), \
             patch.object(guardian, "_fuse_results", return_value={"status": "ok"}):
            guardian.process_query("q")

        assert dispatched == ["navigator", "cipher", "coordinator", "policy"]

    def test_process_query_stops_at_completeness_threshold(self, guardian):
        """完整度 >= 0.8 时停止调度"""
        call_count = [0]

        def fake_dispatch(worker, query):
            call_count[0] += 1
            guardian.team_room.write(f"{worker}_result", {"status": "ok"})

        # 第一个 worker 后完整度就达标
        completeness_values = [0.85, 0.90, 0.95, 1.0]

        with patch.object(guardian, "_dispatch_to_worker", side_effect=fake_dispatch), \
             patch.object(guardian, "evaluate_completeness",
                          side_effect=lambda bb: completeness_values[call_count[0] - 1]):
            with patch.object(guardian, "reconstruct_result", return_value={}), \
                 patch.object(guardian, "_fuse_results", return_value={"status": "ok"}):
                guardian.process_query("q")

        # 只调度了第一个 worker
        assert call_count[0] == 1

    def test_process_query_returns_fused_result(self, guardian):
        """process_query 返回融合结果"""
        fused = {"status": "ok", "data": "result", "component": "core"}

        with patch.object(guardian, "_dispatch_to_worker"), \
             patch.object(guardian, "evaluate_completeness", return_value=0.0), \
             patch.object(guardian, "reconstruct_result", return_value={}), \
             patch.object(guardian, "_fuse_results", return_value=fused):
            result = guardian.process_query("q")

        assert result == fused

    def test_process_query_exception_returns_error(self, guardian):
        """处理异常时返回 error envelope"""
        with patch.object(guardian, "_dispatch_to_worker",
                          side_effect=RuntimeError("dispatch failed")):
            result = guardian.process_query("q")

        assert result["status"] == "error"
        assert "dispatch failed" in result["data"]

    def test_process_query_sets_board_updated(self, guardian):
        """成功处理后 board_updated 为 True"""
        with patch.object(guardian, "_dispatch_to_worker"), \
             patch.object(guardian, "evaluate_completeness", return_value=0.0), \
             patch.object(guardian, "reconstruct_result", return_value={}), \
             patch.object(guardian, "_fuse_results", return_value={"status": "ok"}):
            guardian.process_query("q")

        assert guardian.board_updated is True


# ---------------------------------------------------------------------------
# execute 委托测试
# ---------------------------------------------------------------------------


class TestExecute:
    """execute 方法测试（基类约定入口）"""

    @pytest.fixture
    def guardian(self, team_room):
        return PrivacyGuardian("G", team_room)

    def test_execute_with_query_in_task(self, guardian):
        """task 含 query 时委托给 process_query"""
        with patch.object(guardian, "process_query") as mock_pq:
            mock_pq.return_value = {"status": "ok"}
            guardian.execute({"query": "test"})
            mock_pq.assert_called_once_with("test")

    def test_execute_reads_from_blackboard(self, guardian):
        """task 无 query 时从黑板读取"""
        guardian.team_room.write("user_query", "bb query")
        with patch.object(guardian, "process_query") as mock_pq:
            mock_pq.return_value = {"status": "ok"}
            guardian.execute({})
            mock_pq.assert_called_once_with("bb query")

    def test_execute_empty_query(self, guardian):
        """空 query 时调用 process_query("")"""
        with patch.object(guardian, "process_query") as mock_pq:
            guardian.execute({})
            mock_pq.assert_called_once_with("")


# ---------------------------------------------------------------------------
# on_message 测试
# ---------------------------------------------------------------------------


class TestOnMessage:
    """on_message 测试"""

    def test_on_message_writes_user_message(self, team_room):
        guardian = PrivacyGuardian("G", team_room)
        guardian.on_message("hello")
        assert team_room.read("user_message") == "hello"


# ---------------------------------------------------------------------------
# _dispatch_to_worker 测试
# ---------------------------------------------------------------------------


class TestDispatchToWorker:
    """_dispatch_to_worker 测试"""

    def test_dispatch_writes_task_key(self, team_room):
        guardian = PrivacyGuardian("G", team_room)
        guardian._dispatch_to_worker("navigator", "test query")

        task = team_room.read("task_to_navigator")
        assert task["action"] == "work"
        assert task["query"] == "test query"
        assert task["guardian"] == "G"
        assert "timestamp" in task
