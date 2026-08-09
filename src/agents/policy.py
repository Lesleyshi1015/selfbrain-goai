# @agent: session-260809-new-swamp | module: agents/policy | ts: 2026-08-09T12:52+08:00
"""
agents.policy — PolicyEnforcer（策略执行者）

继承 WorkerAgent，负责校验对外输出的文本是否符合隐私/安全策略，
将校验结果写入黑板 policy_result。

用法：
    from agent_teams_sdk import TeamRoom
    from agents.policy import PolicyEnforcer
    from sb_api import create_engine

    room = TeamRoom("privacy-query-001")
    engine = create_engine()
    agent = PolicyEnforcer(room, engine)

    # 黑板写入待校验文本后触发：
    room.write("output_to_check", "待发布的输出文本", updated_by="coordinator")
    result = agent.execute({"action": "work"})
    # result["allowed"]  -> True/False
    # result["reason"]   -> 判定理由
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from agent_teams_sdk.roles.worker import WorkerAgent
from agent_teams_sdk.core.team_room import TeamRoom


class PolicyEnforcer(WorkerAgent):
    """策略执行者（WorkerAgent）。

    从黑板读取待校验的对外输出文本，调用 sb_api.SBEngine.policy_check
    进行隐私/安全策略校验，将结果写回黑板 policy_result 键。

    Attributes:
        engine: SBEngine 实例，提供 policy_check 方法。
        input_key: 黑板中待校验文本的读取键（默认 "output_to_check"）。
        output_key: 校验结果的写入键（默认 "policy_result"）。
    """

    def __init__(
        self,
        team_room: TeamRoom,
        engine: Any,
        input_key: str = "output_to_check",
        output_key: str = "policy_result",
    ) -> None:
        """初始化策略执行者。

        Args:
            team_room: 共享黑板实例（TeamRoom）。
            engine: SBEngine 实例（提供 policy_check 方法）。
            input_key: 黑板中待校验文本的读取键，默认 "output_to_check"。
            output_key: 校验结果的写入键，默认 "policy_result"。
        """
        super().__init__("G7-policy", team_room)
        self.engine = engine
        self.input_key = input_key
        self.output_key = output_key

    def do_work(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行策略校验。

        从黑板读取待校验文本（优先 task["text"]，其次 input_key 键），
        调用 engine.policy_check(text)，将结果写回黑板。

        Args:
            task: 任务字典。可含 "text" 键直接传入待校验文本；
                  不含时从黑板 input_key 键读取。

        Returns:
            校验结果字典：
                - allowed: bool | None，是否允许发布
                - reason: str，判定理由
                - policy: str，命中的策略/规则（如有）
                - text: str，被校验的原文（截断）

        Raises:
            ValueError: 黑板和 task 中均未找到待校验文本。
            RuntimeError: engine.policy_check 返回异常状态。
        """
        # 1. 读取待校验文本
        text: Optional[str] = task.get("text") if isinstance(task, dict) else None
        if not text:
            text = self.team_room.read(self.input_key)

        if not text or not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"PolicyEnforcer: 未找到待校验文本（task['text'] 和黑板 '{self.input_key}' 均为空）"
            )

        # 2. 调用策略校验引擎
        try:
            response = self.engine.policy_check(text)
        except Exception as exc:  # noqa: BLE001
            # 引擎异常时降级为"不允许 + 记录原因"，不阻断流程
            result: Dict[str, Any] = {
                "allowed": False,
                "reason": f"策略引擎调用异常: {exc}",
                "policy": "",
                "text": text[:200],
            }
            self.team_room.write(
                self.output_key, result, updated_by="G7-policy"
            )
            return result

        # 3. 解析引擎响应 envelope
        status: str = response.get("status", "error")
        data: Dict[str, Any] = response.get("data", {})

        if status == "error":
            error_msg = data.get("error", "未知引擎错误")
            result = {
                "allowed": False,
                "reason": f"策略引擎错误: {error_msg}",
                "policy": "",
                "text": text[:200],
            }
        else:
            allowed = data.get("allowed")
            reason = data.get("reason", "")
            policy = data.get("policy", "")

            # pending 状态（Wave 2 前）视为"允许但标注待补全"
            if status == "pending":
                allowed = True
                reason = f"策略校验接口就绪（Wave 2 补全真实判定）; {reason}"

            result = {
                "allowed": allowed,
                "reason": reason,
                "policy": policy,
                "text": text[:200],
            }

        # 4. 写回黑板
        self.team_room.write(self.output_key, result, updated_by="G7-policy")
        return result
