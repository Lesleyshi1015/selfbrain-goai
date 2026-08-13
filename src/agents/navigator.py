# @agent: session-260809-new-elk | module: agents/navigator | ts: 2026-08-09T12:52+08:00
"""
agents/navigator — 记忆导航员（MemoryNavigator）

SelfBrain-GOAI 蜂群模式执行 Agent G4-navigator。
职责：接收用户查询 → 语义检索记忆 → 将结果写入黑板（navigator_result）
→ 供 Guardian 评估完整度。

继承自 agent-teams-sdk 的 WorkerAgent，通过 sb_api 桥接层调用
SelfBrain 主项目 navigator 模型（Wave 2 补全真实推理，当前为 stub 编排）。

用法：
    from agent_teams_sdk import TeamRoom
    from agents.navigator import MemoryNavigator

    room = TeamRoom("privacy-query-001")
    room.write("user_query", "我的账号密码存在哪？")
    nav = MemoryNavigator("G4-navigator", room)
    result = nav.execute({"action": "work"})
"""

from __future__ import annotations

from typing import Any, Dict

from agent_teams_sdk.roles.worker import WorkerAgent
from agent_teams_sdk.core.team_room import TeamRoom

from sb_api import create_engine
from agents.memory_backend import MemoryBackend, SBAPIBackend


class MemoryNavigator(WorkerAgent):
    """记忆导航员：语义检索用户记忆并写回黑板。

    通过 sb_api 桥接层访问 SelfBrain 主项目 navigator 模型，
    将检索结果以统一 envelope 结构写入黑板 key ``navigator_result``，
    供下游 Guardian 评估完整度。

    Attributes:
        team_room: 共享黑板实例（由基类注入）。
    """

    def __init__(
        self,
        name: str,
        team_room: TeamRoom,
        engine: Any | None = None,
        backend: MemoryBackend | None = None,
    ) -> None:
        """初始化导航员。

        Args:
            name: Agent 标识名（蜂群中应为 ``"G4-navigator"``）。
            team_room: 共享黑板实例。
            engine: 可选的 SBEngine 实例；为 None 时内部创建（默认）。
                蜂群编排（如 demo）应传入共享实例，避免真实模式重复加载模型。
            backend: 可选的记忆检索后端（MemoryBackend 子类，热插拔）；
                为 None 时默认使用 SBAPIBackend（复用 engine，缺省内部创建）。
                TimeWeave 等引擎实现 MemoryBackend 后注入即可替换检索实现。
        """
        super().__init__(name, team_room)
        # [G2-sbapi] @agent: session-260809-tidy-tide | module: agents | ts: 2026-08-13T20:41+08:00
        # 热插拔 memory_backend：backend 优先；默认 SBAPIBackend 复用 self._engine
        # （避免 engine=None 时重复创建 engine 实例，违背 R2 P0-2 单实例原则）
        self._engine = engine if engine is not None else create_engine()
        self._backend = (
            backend if backend is not None else SBAPIBackend(engine=self._engine)
        )

    def do_work(self, task: Dict[str, Any]) -> Any:
        """执行记忆检索任务。

        从黑板读取 ``user_query``，调用 sb_api 引擎进行语义检索，
        将结果写回黑板 ``navigator_result`` 并返回。

        Args:
            task: 任务字典（由蜂群调度器传入，当前未使用具体字段）。

        Returns:
            统一 envelope dict：
                {
                    "status": "ok" | "error",
                    "data": {
                        "query": str,
                        "results": list[dict],
                        "memory_paths": list[str],
                        "provider": str
                    },
                    "component": "navigator"
                }

        Raises:
            Exception: 其他未预期异常（引擎调用异常已捕获返回 error envelope；
                空查询返回 error envelope 不抛异常，与 cipher.py 一致）。
        """
        # 1. 从黑板读取用户查询
        query: str = self.team_room.read("user_query")
        if not query:
            # [转派修复·G2-sbapi] @agent: session-260809-tidy-tide | module: agents | ts: 2026-08-09T13:58+08:00
            # R2 P0-3：不抛异常阻断蜂群，返回 error envelope 并写黑板，
            # 保证 Guardian 完整度评估可读到 navigator_result
            result = {
                "status": "error",
                "data": {"error": "user_query 为空"},
                "component": "navigator",
            }
            self.team_room.write(
                "navigator_result",
                result,
                updated_by=self.name,
            )
            return result

        # 2. 通过记忆检索后端进行语义检索（默认 SBAPIBackend → sb_api 引擎；
        #    注入自定义 backend 时走自定义实现，热插拔生效）
        # TODO(G2/Wave2): 真实模型调用由 sb_api.engine.search 补全，
        #   当前返回 stub 空结构（status="ok", results=[]）。
        #   不在此处 mock 假数据、不实际加载模型。
        try:
            result = self._backend.search(query)
        except Exception as exc:
            # 优雅降级：返回 error envelope，不抛出阻断蜂群
            result = {
                "status": "error",
                "data": {"error": str(exc), "query": query},
                "component": "navigator",
            }

        # 3. 将结果写回黑板（Guardian 读取此 key 评估完整度）
        self.team_room.write(
            "navigator_result",
            result,
            updated_by=self.name,
        )

        return result
