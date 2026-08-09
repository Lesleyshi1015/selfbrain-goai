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


class MemoryNavigator(WorkerAgent):
    """记忆导航员：语义检索用户记忆并写回黑板。

    通过 sb_api 桥接层访问 SelfBrain 主项目 navigator 模型，
    将检索结果以统一 envelope 结构写入黑板 key ``navigator_result``，
    供下游 Guardian 评估完整度。

    Attributes:
        team_room: 共享黑板实例（由基类注入）。
    """

    def __init__(self, name: str, team_room: TeamRoom) -> None:
        """初始化导航员。

        Args:
            name: Agent 标识名（蜂群中应为 ``"G4-navigator"``）。
            team_room: 共享黑板实例。
        """
        super().__init__(name, team_room)
        self._engine = create_engine()

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
            KeyError: 黑板中不存在 ``user_query`` 键。
            Exception: sb_api 引擎调用异常（记录并返回 error envelope）。
        """
        # 1. 从黑板读取用户查询
        query: str = self.team_room.read("user_query")
        if not query:
            raise ValueError("user_query 为空，无法执行检索")

        # 2. 调用 sb_api 引擎进行语义检索
        # TODO(G2/Wave2): 真实模型调用由 sb_api.engine.search 补全，
        #   当前返回 stub 空结构（status="ok", results=[]）。
        #   不在此处 mock 假数据、不实际加载模型。
        try:
            result = self._engine.search(query)
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
