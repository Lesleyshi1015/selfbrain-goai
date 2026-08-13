# @agent: session-260809-tidy-tide | module: agents/memory_backend | ts: 2026-08-13T20:41+08:00
"""
agents/memory_backend — 记忆检索后端抽象接口（热插拔）

GOAI 合并版 PPT 需求：Memory Navigator 可换检索引擎（如 TimeWeave）。
本模块定义抽象检索后端接口 MemoryBackend，并提供默认实现 SBAPIBackend
（封装 sb_api.SBEngine.search，返回结构与现状完全一致）。

热插拔用法：
    from agents.memory_backend import SBAPIBackend
    from agents.navigator import MemoryNavigator

    # 默认：SBAPI 后端（stub 或真实模型）
    nav = MemoryNavigator("G4-navigator", room)

    # 热插拔：注入自定义后端（如 TimeWeave 实现 MemoryBackend 后）
    nav = MemoryNavigator("G4-navigator", room, backend=timeweave_backend)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sb_api import create_engine


class MemoryBackend(ABC):
    """记忆检索后端抽象接口（热插拔）。

    所有检索引擎（sb_api、TimeWeave 等）实现本接口后，
    即可注入 MemoryNavigator 替换默认检索实现，蜂群编排无需改动。

    约定返回结构（data 层最小契约）：
        {"query": str, "results": list[dict], "memory_paths": list[str]}
    """

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> dict:
        """执行记忆检索。

        Args:
            query: 用户查询文本。
            top_k: 返回结果条数上限（默认 5）。

        Returns:
            检索结果 dict，data 层至少包含：
                "query": 原查询文本。
                "results": 检索命中的记忆条目列表。
                "memory_paths": 定位到的数据位置路径列表。
        """
        raise NotImplementedError


class SBAPIBackend(MemoryBackend):
    """默认记忆检索后端：封装 SBEngine.search()。

    返回 SBEngine.search() 的完整 envelope（status/data/component），
    data 含 "query"/"results"/"memory_paths"/"provider"，与现状完全一致，
    保证现有 195 tests 行为不受影响。
    """

    def __init__(self, engine: Any | None = None) -> None:
        """初始化 SBAPIBackend。

        Args:
            engine: 可选的 SBEngine 实例；为 None 时内部 create_engine()（默认，
                惰性 stub，不加载真实模型）。
        """
        self._engine = engine if engine is not None else create_engine()

    def search(self, query: str, top_k: int = 5) -> dict:
        """调用 SBEngine.search(query) 并透传结果。

        Args:
            query: 用户查询文本。
            top_k: 预留参数（当前 stub 未使用，真实模型接入后生效）。

        Returns:
            SBEngine.search() 的 envelope（含 status/data/component；
            data 含 "query"/"results"/"memory_paths"/"provider"）。
        """
        return self._engine.search(query)


__all__ = ["MemoryBackend", "SBAPIBackend"]
