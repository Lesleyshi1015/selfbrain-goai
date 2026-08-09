# @agent: session-260809-dynamic-plateau | module: agents/cipher | ts: 2026-08-09T12:52+08:00
"""
agents.cipher — CipherGenerator（加密/隐私分析员）

SelfBrain-GOAI 蜂群模式执行 Agent（G5），继承自 agent-teams-sdk 的
WorkerAgent。负责接收需加密或隐私分析的文本，调用 sb_api 桥接层
的 cipher 模型进行分析，将结果写回黑板供 Guardian 评估完整度。

黑板协议（TeamRoom）：
    - 读取键：待分析文本（由 Guardian 或 Coordinator 写入，键名由任务指定）
    - 写入键：cipher_result（加密/隐私分析结果 envelope）

任务追踪（board.json）：
    - 开始：agents["G5-cipher"].status = "working"，记录 sessionId
    - 完成：agents["G5-cipher"].status = "done"，记录 output + files
    - 完成后自动打标：board::done + needs-review

用法：
    from agent_teams_sdk import TeamRoom
    from agents.cipher import CipherGenerator

    room = TeamRoom("privacy-query-001")
    agent = CipherGenerator(room)
    result = agent.execute({"action": "work"})
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from agent_teams_sdk.roles.worker import WorkerAgent
from agent_teams_sdk.core.team_room import TeamRoom

from sb_api import SBEngine, SBAPIError

logger = logging.getLogger(__name__)

#: board.json 路径（任务追踪用，与 TeamRoom 黑板不同）
_BOARD_PATH = Path(__file__).resolve().parents[2] / ".swarm-board" / "board.json"

#: 本 Agent 在 board.json 中的标识
_AGENT_ID = "G5-cipher"

#: TeamRoom 黑板写入键名（Guardian 评估完整度时读取此键）
_CIPHER_RESULT_KEY = "cipher_result"


class CipherGenerator(WorkerAgent):
    """加密/隐私分析员 WorkerAgent。

    接收待分析文本 → 调用 sb_api.SBEngine.cipher_analyze() →
    将结果写回 TeamRoom 黑板（cipher_result）并更新 board.json 任务状态。

    Attributes:
        engine: SBEngine 实例（惰性初始化，首次 do_work 时创建）。
    """

    def __init__(self, team_room: TeamRoom) -> None:
        """初始化 CipherGenerator。

        Args:
            team_room: 共享黑板实例，用于读写分析文本和结果。
        """
        super().__init__(_AGENT_ID, team_room)
        self._engine: SBEngine | None = None

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    @property
    def engine(self) -> SBEngine:
        """惰性获取 SBEngine 实例（单例，首次访问时创建）。

        Returns:
            SBEngine 实例。
        """
        if self._engine is None:
            self._engine = SBEngine()
        return self._engine

    # ------------------------------------------------------------------
    # WorkerAgent 接口
    # ------------------------------------------------------------------

    def do_work(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行加密/隐私分析（WorkerAgent 抽象方法实现）。

        流程：
            1. 从 TeamRoom 黑板读取待分析文本（键由 task["text_key"] 指定，
               默认为 "user_query"）。
            2. 调用 SBEngine.cipher_analyze(text) 进行分析。
            3. 将结果写入 TeamRoom 黑板（键 "cipher_result"）。
            4. 更新 board.json 任务状态为 working → done。

        Args:
            task: 任务字典，可选包含：
                - text_key: TeamRoom 中待分析文本的键名（默认 "user_query"）。

        Returns:
            cipher_analyze 返回的统一 envelope：
                {
                    "status": "ok" | "pending" | "error",
                    "data": {
                        "input_length": int,
                        "cipher_result": str | None,
                        "action": str | None
                    },
                    "component": "cipher",
                    "note"?: str
                }

        Raises:
            SBAPIError: sb_api 桥接层异常（路径缺失、组件加载失败等）。
            Exception: 其他未预期异常（记录日志并转换为 error envelope）。
        """
        text_key: str = task.get("text_key", "user_query")

        # 1. 读取待分析文本
        text: Any = self.team_room.read(text_key)
        if text is None:
            logger.warning(
                "[%s] 黑板键 %r 为空，跳过分析", self.name, text_key
            )
            return self._error_envelope(
                ValueError(f"黑板键 {text_key!r} 无数据"),
                "input_missing",
            )

        if not isinstance(text, str):
            text = str(text)

        # 2. 更新 board.json 状态为 working
        self._update_board_status("working")

        # 3. 调用 cipher 模型分析
        try:
            result = self.engine.cipher_analyze(text)
        except SBAPIError as exc:
            logger.error("[%s] sb_api 调用失败: %s", self.name, exc)
            result = self._error_envelope(exc, "sb_api_error")
        except Exception as exc:
            logger.exception("[%s] 未预期异常: %s", self.name, exc)
            result = self._error_envelope(exc, "unexpected_error")

        # 4. 写回黑板
        self.team_room.write(
            _CIPHER_RESULT_KEY, result, updated_by=self.name
        )

        # 5. 更新 board.json 状态为 done
        self._update_board_done(result)

        return result

    def execute(self, task: Dict[str, Any]) -> Any:
        """执行任务并写回黑板（覆盖基类以使用固定键名 cipher_result）。

        基类 WorkerAgent.execute 会将结果写入 {self.name}_result，
        但 Guardian 评估完整度时期望键名为 cipher_result，
        因此覆盖此方法以确保键名一致。

        Args:
            task: 任务字典（透传给 do_work）。

        Returns:
            do_work 的返回值。
        """
        result = self.do_work(task)
        # 同时写入固定键名（Guardian 读取）和基类约定键名（兼容）
        self.team_room.write(_CIPHER_RESULT_KEY, result, updated_by=self.name)
        self.team_room.write(
            f"{self.name}_result", result, updated_by=self.name
        )
        return result

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _error_envelope(
        self, exc: Exception, error_type: str
    ) -> Dict[str, Any]:
        """构建 error 状态的统一 envelope。

        Args:
            exc: 捕获的异常。
            error_type: 错误类型标识（用于 note）。

        Returns:
            {"status": "error", "data": {"error": ...}, "component": "cipher"}。
        """
        return {
            "status": "error",
            "data": {"error": str(exc), "type": error_type},
            "component": "cipher",
        }

    def _read_board(self) -> Dict[str, Any]:
        """读取 board.json（不存在时返回空结构）。

        Returns:
            board.json 内容字典。
        """
        if not _BOARD_PATH.exists():
            return {"agents": {}}
        try:
            return json.loads(_BOARD_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("[%s] 读取 board.json 失败: %s", self.name, exc)
            return {"agents": {}}

    def _write_board(self, board: Dict[str, Any]) -> None:
        """写入 board.json（确保目录存在）。

        Args:
            board: 要写入的 board 字典。
        """
        _BOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
        _BOARD_PATH.write_text(
            json.dumps(board, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _update_board_status(self, status: str) -> None:
        """更新 board.json 中本 Agent 的状态。

        Args:
            status: 新状态（"working" | "done"）。
        """
        board = self._read_board()
        agents = board.setdefault("agents", {})
        agent_entry = agents.setdefault(_AGENT_ID, {})
        agent_entry["sessionId"] = "260809-dynamic-plateau"
        agent_entry["module"] = "agents/cipher"
        agent_entry["status"] = status
        if status == "done":
            # output 和 files 由 _update_board_done 填充
            pass
        self._write_board(board)

    def _update_board_done(
        self, result: Dict[str, Any]
    ) -> None:
        """更新 board.json 为完成状态，填充 output 和 files。

        Args:
            result: do_work 返回的分析结果 envelope。
        """
        board = self._read_board()
        agent_entry = board.setdefault("agents", {}).setdefault(
            _AGENT_ID, {}
        )
        agent_entry["status"] = "done"
        agent_entry["sessionId"] = "260809-dynamic-plateau"
        agent_entry["module"] = "agents/cipher"

        # 生成简要 output 摘要
        status = result.get("status", "unknown")
        component = result.get("component", "cipher")
        data = result.get("data", {})
        action = data.get("action") or "pending(Wave2)"
        agent_entry["output"] = (
            f"CipherGenerator 完成：status={status}, "
            f"component={component}, action={action}"
        )
        agent_entry["files"] = ["src/agents/cipher.py"]
        agent_entry.pop("foundIssue", None)  # 清理遗留字段

        self._write_board(board)
