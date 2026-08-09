# @agent: session-260809-sleek-creek | module: agents/coordinator | ts: 2026-08-09T12:52+08:00
"""数据协调员：协调多来源数据，将协调结果写入黑板。"""

from typing import Any, Dict, List, Optional
from agent_teams_sdk.roles.worker import WorkerAgent
from agent_teams_sdk.core.team_room import TeamRoom


class DataCoordinator(WorkerAgent):
    """
    数据协调员 (WorkerAgent)

    职责：
    - 从黑板读取 navigator_result / cipher_result 等多来源数据
    - 执行本地协调逻辑（合并、去重、冲突检测、优先级排序）
    - 将协调结果写入黑板 coordinator_result
    - 返回协调后的结果 dict

    黑板协议：
    - 读取：navigator_result, cipher_result
    - 写入：coordinator_result, G6-coordinator_result（execute 自动写入）
    """

    def __init__(self, team_room: TeamRoom):
        """
        初始化数据协调员

        Args:
            team_room: 共享黑板实例
        """
        super().__init__(name="G6-coordinator", team_room=team_room)

    def on_message(self, message: str) -> None:
        """
        处理消息

        当消息以 @G6-coordinator 开头时触发执行。

        Args:
            message: 接收到的消息字符串
        """
        if message.startswith(f"@{self.name}"):
            self.execute({"action": "coordinate"})

    def do_work(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行数据协调工作

        从黑板读取多来源数据，执行协调逻辑，写回结果。

        Args:
            task: 任务字典，可包含协调参数（如 merge_strategy）

        Returns:
            协调后的结果字典，包含 merged_data、conflicts、metadata
        """
        # 从黑板读取多来源数据
        navigator_result: Optional[Any] = self.team_room.read("navigator_result")
        cipher_result: Optional[Any] = self.team_room.read("cipher_result")

        # 执行本地协调逻辑
        coordinated_data: Dict[str, Any] = self._coordinate(
            navigator_result=navigator_result,
            cipher_result=cipher_result,
            task_params=task,
        )

        # 写回黑板 coordinator_result
        self.team_room.write(
            "coordinator_result",
            coordinated_data,
            updated_by="G6-coordinator",
        )

        return coordinated_data

    def _coordinate(
        self,
        navigator_result: Optional[Any],
        cipher_result: Optional[Any],
        task_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        核心协调逻辑

        合并多来源数据，执行去重、冲突检测、优先级排序。

        Args:
            navigator_result: Navigator Agent 的检索结果
            cipher_result: Cipher Agent 的加密分析结果
            task_params: 任务参数（如 merge_strategy）

        Returns:
            协调后的结果字典
        """
        result: Dict[str, Any] = {
            "status": "coordinated",
            "sources": {
                "navigator": navigator_result,
                "cipher": cipher_result,
            },
            "merged_data": [],
            "conflicts": [],
            "metadata": {
                "coordinator": self.name,
                "session_id": "260809-sleek-creek",
                "strategy": task_params.get("merge_strategy", "append"),
            },
        }

        # 合并策略：简单追加（可扩展为优先级排序、去重等）
        merged: List[Any] = []
        strategy: str = task_params.get("merge_strategy", "append")

        if navigator_result is not None:
            merged.extend(self._normalize_to_list(navigator_result))

        if cipher_result is not None:
            merged.extend(self._normalize_to_list(cipher_result))

        # 简单去重（基于 str 表示）
        if strategy == "dedup":
            seen: set = set()
            unique: List[Any] = []
            for item in merged:
                key = str(item)
                if key not in seen:
                    seen.add(key)
                    unique.append(item)
            merged = unique

        result["merged_data"] = merged

        # 冲突检测：如果两来源都存在且类型不同，记录冲突
        if navigator_result is not None and cipher_result is not None:
            if type(navigator_result) != type(cipher_result):
                result["conflicts"].append({
                    "type": "type_mismatch",
                    "navigator_type": type(navigator_result).__name__,
                    "cipher_type": type(cipher_result).__name__,
                    "resolution": "keep_both",
                })

        return result

    @staticmethod
    def _normalize_to_list(value: Any) -> List[Any]:
        """
        将值规范化为列表

        Args:
            value: 任意值

        Returns:
            列表形式的值
        """
        if isinstance(value, list):
            return value
        return [value]
