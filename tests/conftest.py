# @agent: session-260809-grand-sunset | module: tests/conftest | ts: 2026-08-09T13:06+08:00
"""
tests/conftest.py — 共享 pytest fixture

为所有测试模块提供：
    - TeamRoom 实例（共享黑板）
    - engine stub（SBEngine 的轻量 mock，不加载真实模型）
    - 黑板键结构常量
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# 确保 src/ 在 sys.path 中（pytest 运行时需要）
_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agent_teams_sdk import TeamRoom  # noqa: E402

# ---------------------------------------------------------------------------
# 黑板键常量（Guardian 评估完整度时读取的键）
# ---------------------------------------------------------------------------

BLACKBOARD_KEYS: Dict[str, str] = {
    "user_query": "用户原始查询",
    "navigator_result": "记忆检索结果",
    "cipher_result": "加密分析结果",
    "coordinator_result": "数据协调结果",
    "policy_result": "策略校验结果",
    "audit_result": "审计记录结果",
    "guardian_result": "Guardian 融合结果",
    "validator_result": "Validator 核查结果",
}

# ---------------------------------------------------------------------------
# Engine Stub 工厂
# ---------------------------------------------------------------------------


def make_engine_stub(
    search_result: Dict[str, Any] | None = None,
    cipher_result: Dict[str, Any] | None = None,
    policy_result: Dict[str, Any] | None = None,
    fuse_result: Dict[str, Any] | None = None,
    decompose_result: Dict[str, Any] | None = None,
    dispatch_result: Dict[str, Any] | None = None,
) -> MagicMock:
    """
    创建 SBEngine 的 stub mock。

    所有方法默认返回合理的 stub envelope，可通过参数覆盖特定返回值。
    不触发任何真实模型加载或推理。
    """
    stub = MagicMock()

    # search — 默认返回 ok envelope（最小可跑结构）
    stub.search.return_value = search_result or {
        "status": "ok",
        "data": {"query": "", "results": [], "memory_paths": [], "provider": "sb_api.stub"},
        "component": "navigator",
    }

    # cipher_analyze — 默认 pending
    stub.cipher_analyze.return_value = cipher_result or {
        "status": "pending",
        "data": {"input_length": 0, "cipher_result": None, "action": None},
        "component": "cipher",
        "note": "Wave 2 补全",
    }

    # policy_check — 默认 pending
    stub.policy_check.return_value = policy_result or {
        "status": "pending",
        "data": {"policy": "", "allowed": None, "reason": "Wave 2 补全"},
        "component": "broker",
        "note": "Wave 2 补全",
    }

    # fuse — 默认 pending
    stub.fuse.return_value = fuse_result or {
        "status": "pending",
        "data": "",
        "component": "core",
        "note": "Wave 2 补全",
    }

    # decompose — 默认 pending
    stub.decompose.return_value = decompose_result or {
        "status": "pending",
        "data": [],
        "component": "core",
        "note": "Wave 2 补全",
    }

    # dispatch — 默认 pending
    stub.dispatch.return_value = dispatch_result or {
        "status": "pending",
        "data": {},
        "component": "core",
        "note": "Wave 2 补全",
    }

    # unload_all — ok
    stub.unload_all.return_value = {
        "status": "ok",
        "data": {"released": [], "remaining": []},
        "component": "all",
    }

    return stub


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def team_room() -> TeamRoom:
    """提供一个干净的 TeamRoom 实例（每测试隔离）。"""
    return TeamRoom("test-room")


@pytest.fixture
def engine_stub() -> MagicMock:
    """提供一个 SBEngine stub（所有方法返回合理 envelope，无真实模型调用）。"""
    return make_engine_stub()


@pytest.fixture
def blackboard_keys() -> Dict[str, str]:
    """黑板键常量副本。"""
    return BLACKBOARD_KEYS.copy()


@pytest.fixture(autouse=True)
def restore_stdout_stderr():
    """
    全局 fixture：每个测试后恢复 sys.stdout / sys.stderr。

    原因：demo.py 在 import 时会修改 sys.stdout/sys.stderr（Windows UTF-8 兼容），
    这会破坏 pytest 的 capture 机制，导致后续测试清理失败。
    """
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    yield
    sys.stdout = orig_stdout
    sys.stderr = orig_stderr


@pytest.fixture
def patch_loader() -> Any:
    """
    Patch sb_api.loader 模块级变量，避免真实路径检查。

    用法：
        def test_something(patch_loader):
            from sb_api import loader
            assert loader.SRC_PATH is not None
    """
    with patch("sb_api.loader.SRC_PATH") as mock_path, \
         patch("sb_api.loader._SRC_PATH_READY", False), \
         patch("sb_api.loader._model_loader", None), \
         patch("sb_api.loader._LOADED", {}):
        mock_path.is_dir.return_value = False
        yield mock_path
