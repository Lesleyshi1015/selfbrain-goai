# @agent: session-260809-lucid-copper | module: agents/guardian | ts: 2026-08-09T12:52+08:00
"""
PrivacyGuardian — 隐私守护小组长（CuratorAgent）

SelfBrain-GOAI 适配项目 · G3-guardian

职责：
    - 接收用户隐私查询，作为 Curator 调度 Navigator / Cipher /
      Coordinator / Policy 等 Worker 协同处理
    - 将任务发布到 TeamRoom 黑板，驱动 Worker 执行
    - 评估黑板完整度，决定是否需要继续调度
    - 重建最终结果并通过 sb_api 融合后返回

黑板协议（.swarm-board/board.json）：
    agents["G3-guardian"] 下记录：
        status  — pending | working | done | error
        sessionId — 当前 session 短 ID
        output  — 完成时的输出摘要
        files   — 产出文件列表
        foundIssue — 发现的问题（如有）

用法：
    from agent_teams_sdk import TeamRoom
    from agents.guardian import PrivacyGuardian

    room = TeamRoom("privacy-query-001")
    guardian = PrivacyGuardian("PrivacyGuardian", room)
    result = guardian.process_query("我的账号密码存在哪？")
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_teams_sdk.core.team_room import TeamRoom
from agent_teams_sdk.roles.curator import CuratorAgent

logger = logging.getLogger(__name__)

# ── 黑板路径 ──────────────────────────────────────────────
_BOARD_PATH = Path(__file__).resolve().parents[2] / ".swarm-board" / "board.json"
_AGENT_KEY = "G3-guardian"
_SESSION_ID = "260809-lucid-copper"

# ── Worker 列表（按调度顺序）───────────────────────────────
DEFAULT_WORKERS: List[str] = [
    "navigator",    # 记忆检索
    "cipher",       # 加密分析
    "coordinator",  # 协调汇总
    "policy",       # 策略校验
]


class PrivacyGuardian(CuratorAgent):
    """
    PrivacyGuardian — 隐私守护小组长

    继承 CuratorAgent，负责：
        1. 接收用户查询（process_query）
        2. 将查询写入黑板，调度各 Worker
        3. 评估黑板完整度（evaluate_completeness）
        4. 通过 sb_api 融合各 Worker 结果，重建最终输出

    构造参数：
        name        Agent 名称（默认 "PrivacyGuardian"）
        team_room   TeamRoom 实例（共享黑板）
        workers     Worker 名称列表（默认 DEFAULT_WORKERS）

    示例：
        >>> room = TeamRoom("query-001")
        >>> guardian = PrivacyGuardian("Guardian", room)
        >>> result = guardian.process_query("我的隐私数据存储在哪里？")
    """

    def __init__(
        self,
        name: str = "PrivacyGuardian",
        team_room: Optional[TeamRoom] = None,
        workers: Optional[List[str]] = None,
    ) -> None:
        """
        初始化 PrivacyGuardian。

        Args:
            name: Agent 名称，默认 "PrivacyGuardian"。
            team_room: TeamRoom 实例。若为 None 则创建临时黑板。
            workers: Worker 名称列表，默认 DEFAULT_WORKERS。
        """
        if team_room is None:
            team_room = TeamRoom("privacy-guardian-default")
        if workers is None:
            workers = DEFAULT_WORKERS.copy()

        super().__init__(name=name, team_room=team_room, workers=workers)
        self._board_updated: bool = False

    # ──────────────────────────────────────────────────────
    # 主入口
    # ──────────────────────────────────────────────────────

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        处理用户隐私查询的主入口。

        流程：
            1. 将查询写入黑板（user_query）
            2. 依次调度各 Worker（通过 team_room.write 发布任务）
            3. 每调度一轮后评估完整度
            4. 完整度 >= 0.8 时停止调度，重建结果
            5. 通过 sb_api.fuse 融合后返回

        Args:
            query: 用户隐私查询文本。

        Returns:
            融合后的结果字典 {"status": ..., "data": ..., "component": ...}。

        Raises:
            PrivacyGuardianError: 调度过程中出现不可恢复错误时抛出。
        """
        self._board_write(status="working", sessionId=_SESSION_ID)

        try:
            # 1. 写入用户查询
            self.team_room.write("user_query", query, updated_by=self.name)

            # 2. 依次调度 Worker
            for worker in self.workers:
                self._dispatch_to_worker(worker, query)

                # 3. 评估完整度
                blackboard = self.team_room.read_all()
                completeness = self.evaluate_completeness(blackboard)
                logger.info(
                    "[%s] 调度 %s 后完整度: %.2f",
                    self.name, worker, completeness,
                )

                if completeness >= 0.8:
                    logger.info("[%s] 完整度达标 (%.2f)，停止调度", self.name, completeness)
                    break

            # 4. 重建结果
            blackboard = self.team_room.read_all()
            raw_result = self.reconstruct_result(blackboard)

            # 5. 通过 sb_api 融合
            fused = self._fuse_results(raw_result)

            self._board_write(
                status="done",
                sessionId=_SESSION_ID,
                output=f"PrivacyGuardian 完成处理，完整度={self.evaluate_completeness(blackboard):.2f}",
                files=["src/agents/guardian.py"],
            )
            self._board_updated = True

            return fused

        except Exception as exc:
            logger.error("[%s] 处理查询失败: %s", self.name, exc, exc_info=True)
            self._board_write(
                status="error",
                sessionId=_SESSION_ID,
                output=f"处理失败: {exc}",
                foundIssue=str(exc),
            )
            return {
                "status": "error",
                "data": str(exc),
                "component": "guardian",
            }

    # ──────────────────────────────────────────────────────
    # 完整度评估（覆写 CuratorAgent 抽象方法）
    # ──────────────────────────────────────────────────────

    def evaluate_completeness(self, blackboard: Dict[str, Any]) -> float:
        """
        评估黑板完整度（0.0 – 1.0）。

        评估规则（参照框架示例）：
            - navigator_result 存在  → +0.35
            - cipher_result 存在     → +0.30
            - coordinator_result 存在 → +0.20
            - policy_result 存在     → +0.15
            - 四项齐全且有 user_query → 0.95（封顶）

        Args:
            blackboard: 黑板当前状态（team_room.read_all() 返回值）。

        Returns:
            完整度分数（0.0 – 1.0）。
        """
        score: float = 0.0
        weights: Dict[str, float] = {
            "navigator_result": 0.35,
            "cipher_result": 0.30,
            "coordinator_result": 0.20,
            "policy_result": 0.15,
        }

        for key, weight in weights.items():
            value = blackboard.get(key)
            if value is not None and value != "":
                score += weight

        # 有 user_query 时额外加权（最多补到 0.95）
        if blackboard.get("user_query") and score > 0:
            score = min(score + 0.05, 0.95)

        return round(score, 2)

    # ──────────────────────────────────────────────────────
    # 结果重建（覆写 CuratorAgent 方法）
    # ──────────────────────────────────────────────────────

    def reconstruct_result(self, blackboard: Dict[str, Any]) -> Dict[str, Any]:
        """
        从黑板重建最终结果。

        收集各 Worker 的 result 条目，组装为结构化字典。

        Args:
            blackboard: 黑板当前状态。

        Returns:
            包含各 Worker 结果的字典。
        """
        results: Dict[str, Any] = {
            "guardian": self.name,
            "query": blackboard.get("user_query", ""),
            "worker_results": {},
            "completeness": self.evaluate_completeness(blackboard),
        }

        for worker in self.workers:
            result_key = f"{worker}_result"
            value = blackboard.get(result_key)
            if value is not None:
                results["worker_results"][worker] = value
            else:
                results["worker_results"][worker] = None

        return results

    # ──────────────────────────────────────────────────────
    # 基类方法覆写
    # ──────────────────────────────────────────────────────

    def on_message(self, message: str) -> None:
        """
        接收外部消息（用户/其他 Agent）。

        将消息写入黑板 user_message 字段，并触发执行。

        Args:
            message: 收到的消息文本。
        """
        self.team_room.write("user_message", message, updated_by=self.name)
        logger.info("[%s] 收到消息: %s", self.name, message)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务（基类约定入口）。

        从 task 中提取 query 字段，委托给 process_query。

        Args:
            task: 任务字典，需包含 "query" 键。

        Returns:
            process_query 的返回值。
        """
        query = task.get("query", "")
        if not query and self.team_room.has("user_query"):
            query = self.team_room.read("user_query") or ""
        return self.process_query(query)

    # ──────────────────────────────────────────────────────
    # 私有方法
    # ──────────────────────────────────────────────────────

    def _dispatch_to_worker(self, worker: str, query: str) -> None:
        """
        向指定 Worker 分发任务（写入黑板）。

        Args:
            worker: Worker 名称。
            query: 原始查询文本。
        """
        task_msg = {
            "action": "work",
            "query": query,
            "guardian": self.name,
            "timestamp": datetime.now().isoformat(),
        }
        self.team_room.write(
            f"task_to_{worker}",
            task_msg,
            updated_by=self.name,
        )
        logger.info("[%s] 分发任务给 %s", self.name, worker)

    def _fuse_results(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        通过 sb_api.fuse 融合各 Worker 结果。

        若 sb_api 不可用或融合失败，返回降级结果（stub envelope）。

        Args:
            raw_result: reconstruct_result 的输出。

        Returns:
            sb_api envelope: {"status": ..., "data": ..., "component": ...}
        """
        try:
            from sb_api import create_engine as _create_engine

            engine = _create_engine()
            parts = raw_result.get("worker_results", {})
            fused = engine.fuse(parts)
            return fused  # type: ignore[no-any-return]

        except ImportError:
            logger.warning("[%s] sb_api 未安装，返回降级结果", self.name)
            return {
                "status": "pending",
                "data": raw_result,
                "component": "guardian",
            }
        except Exception as exc:
            logger.error("[%s] fuse 失败: %s", self.name, exc)
            return {
                "status": "error",
                "data": str(exc),
                "component": "guardian",
            }

    def _board_write(self, **kwargs: Any) -> None:
        """
        更新 .swarm-board/board.json 中 G3-guardian 条目。

        原子写入：读→改→写，保留其他 Agent 条目。
        """
        try:
            board: Dict[str, Any] = {"agents": {}}
            if _BOARD_PATH.exists():
                with _BOARD_PATH.open("r", encoding="utf-8") as f:
                    board = json.load(f)

            board.setdefault("agents", {})
            entry = board["agents"].get(_AGENT_KEY, {})
            entry.update(kwargs)
            entry["updatedAt"] = datetime.now().isoformat()
            board["agents"][_AGENT_KEY] = entry

            _BOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
            with _BOARD_PATH.open("w", encoding="utf-8") as f:
                json.dump(board, f, ensure_ascii=False, indent=2)

        except Exception as exc:
            logger.warning("[%s] 黑板写入失败: %s", self.name, exc)

    @property
    def board_updated(self) -> bool:
        """是否已完成黑板写入。"""
        return self._board_updated


class PrivacyGuardianError(Exception):
    """PrivacyGuardian 专用异常。"""

    pass
