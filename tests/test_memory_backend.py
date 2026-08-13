# @agent: session-260809-tidy-tide | module: tests/memory_backend | ts: 2026-08-13T20:41+08:00
"""
tests/test_memory_backend.py — 记忆检索后端抽象接口（热插拔）测试

覆盖：
    - MemoryBackend 为抽象基类（含抽象方法 search）
    - SBAPIBackend 默认 engine 可创建，search 返回契约结构
    - 自定义 FakeBackend 注入 MemoryNavigator 生效（热插拔验证）
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# 确保 src/ 在 sys.path 中
src_dir = str(Path(__file__).resolve().parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from agent_teams_sdk import TeamRoom  # noqa: E402
from agents.memory_backend import MemoryBackend, SBAPIBackend  # noqa: E402
from agents.navigator import MemoryNavigator  # noqa: E402


class FakeBackend(MemoryBackend):
    """测试用假后端：返回固定结构，验证热插拔注入生效。"""

    def __init__(self, marker: str = "fake") -> None:
        self.marker = marker
        self.calls: list[str] = []

    def search(self, query: str, top_k: int = 5) -> dict:
        self.calls.append(query)
        return {
            "status": "ok",
            "data": {
                "query": query,
                "results": [{"source": self.marker, "text": f"{query}-hit"}],
                "memory_paths": ["fake/path"],
                "provider": self.marker,
            },
            "component": "navigator",
        }


class TestMemoryBackend:
    """记忆后端抽象接口契约测试"""

    def test_backend_contract(self):
        """MemoryBackend 是抽象基类，SBAPIBackend 可实例化"""
        assert MemoryBackend.__abstractmethods__  # 含未实现的抽象方法（search）
        assert issubclass(SBAPIBackend, MemoryBackend)
        backend = SBAPIBackend(engine=MagicMock())
        assert isinstance(backend, MemoryBackend)
        assert not SBAPIBackend.__abstractmethods__  # 已实现全部抽象方法

    def test_default_sbapi_backend(self):
        """SBAPIBackend 默认 engine 可创建，search 返回契约 dict"""
        backend = SBAPIBackend()  # 内部 create_engine()（stub，不加载模型）
        result = backend.search("测试查询")

        assert result["status"] == "ok"
        data = result["data"]
        assert data["query"] == "测试查询"
        assert isinstance(data["results"], list)
        assert isinstance(data["memory_paths"], list)
        assert "provider" in data

    def test_custom_backend_injection(self):
        """自定义 FakeBackend 注入 MemoryNavigator，do_work 走自定义 backend"""
        room = TeamRoom("backend-inject-test")
        room.write("user_query", "我的密码存在哪？")
        fake = FakeBackend(marker="fake-backend")
        nav = MemoryNavigator("G4-navigator", room, backend=fake)

        result = nav.do_work({"action": "work"})

        # 热插拔生效：结果来自自定义 backend
        assert result["status"] == "ok"
        assert result["data"]["provider"] == "fake-backend"
        assert result["data"]["results"][0]["source"] == "fake-backend"
        assert fake.calls == ["我的密码存在哪？"]
        # 黑板写入的是自定义 backend 的结果
        assert room.read("navigator_result")["data"]["provider"] == "fake-backend"
