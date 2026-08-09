# @agent: session-260809-safe-cobble | module: agents/audit | ts: 2026-08-09T12:52+08:00

"""
审计日志记录员（AuditLogger）

负责记录系统内所有关键操作（查询、访问、加密、策略判定等），
生成审计日志条目并写入黑板 audit_result 及本地 JSONL 日志文件，
保证所有操作可追溯。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_teams_sdk.roles.worker import WorkerAgent
from agent_teams_sdk.core.team_room import TeamRoom


# 需要审计的黑板键（各 Agent 输出结果键名）
AUDITED_KEYS: List[str] = [
    "navigator_result",
    "cipher_result",
    "coordinator_result",
    "policy_result",
    "guardian_result",
    "validator_result",
    "shield_result",
    "probe_result",
    "fusion_result",
    "access_result",
    "audit_trail_result",
    "verify_result",
]

# 本地日志目录
DEFAULT_LOG_DIR: Path = Path(r"F:\SelfBrain-GOAI\logs")


class AuditLogger(WorkerAgent):
    """
    审计日志记录员 — WorkerAgent 子类。

    职责：
    - 从黑板读取各 Agent 操作记录
    - 生成审计日志条目（时间戳、操作、涉及 Agent、结果摘要）
    - 写回黑板 audit_result
    - 可选写入本地 JSONL 日志文件

    用法：
        room = TeamRoom("task-001")
        auditor = AuditLogger("G8-audit", room)
        result = auditor.execute({"action": "audit"})
    """

    def __init__(
        self,
        name: str,
        team_room: TeamRoom,
        log_dir: Optional[Path] = None,
        write_file: bool = True,
    ):
        """
        初始化审计日志记录员。

        Args:
            name: Agent 名称（如 "G8-audit"）
            team_room: 共享黑板实例
            log_dir: 本地日志文件目录，默认为 F:\\SelfBrain-GOAI\\logs
            write_file: 是否同时写入本地 JSONL 文件
        """
        super().__init__(name, team_room)
        self.log_dir = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
        self.write_file = write_file
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        """确保日志目录存在，不存在则创建。"""
        if self.write_file and not self.log_dir.exists():
            try:
                self.log_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                # 目录创建失败时降级为仅写黑板
                self.write_file = False
                self._log_warning(f"日志目录创建失败: {exc}，已降级为仅黑板模式")

    def _log_warning(self, message: str) -> None:
        """内部警告日志（打印到 stderr，避免依赖外部 logger）。"""
        print(f"[AuditLogger WARN] {message}", flush=True)

    def _now_iso(self) -> str:
        """返回当前时间的 ISO 8601 字符串（东八区）。"""
        tz_cst = timezone(timedelta(hours=8))
        return datetime.now(tz_cst).isoformat()

    def _summarize_value(self, value: Any, max_len: int = 200) -> str:
        """将黑板值转为摘要字符串，超长则截断。"""
        try:
            s = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            s = str(value)
        if len(s) > max_len:
            s = s[:max_len] + "...[truncated]"
        return s

    def _build_audit_entries(self, blackboard_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从黑板快照构建审计日志条目列表。

        每条条目包含：
        - timestamp: 审计时间
        - agent: 涉及的 Agent 键名
        - operation: 操作类型（固定为 "blackboard_write"）
        - result_summary: 结果摘要
        - has_data: 是否有实际数据
        """
        entries: List[Dict[str, Any]] = []
        now = self._now_iso()

        for key in AUDITED_KEYS:
            value = blackboard_snapshot.get(key)
            if value is None:
                continue

            agent_name = key.replace("_result", "")
            entries.append({
                "timestamp": now,
                "agent": agent_name,
                "operation": "blackboard_write",
                "result_summary": self._summarize_value(value),
                "has_data": bool(value),
            })

        # 如果没有审计到任何条目，仍记录一条系统级心跳
        if not entries:
            entries.append({
                "timestamp": now,
                "agent": "system",
                "operation": "audit_heartbeat",
                "result_summary": "no_agent_results_found_on_blackboard",
                "has_data": False,
            })

        return entries

    def _write_jsonl(self, entries: List[Dict[str, Any]]) -> Optional[str]:
        """
        将审计条目追加写入 JSONL 文件。

        文件名格式：audit_YYYYMMDD.jsonl
        返回写入的文件路径，失败返回 None。
        """
        if not self.write_file:
            return None

        today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
        log_path = self.log_dir / f"audit_{today}.jsonl"

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return str(log_path)
        except OSError as exc:
            self._log_warning(f"JSONL 写入失败: {exc}")
            return None

    def do_work(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行审计工作：读取黑板 → 生成审计条目 → 写回黑板 + 本地文件。

        Args:
            task: 任务字典（当前未使用具体字段，保留接口一致性）

        Returns:
            审计结果字典，包含：
            - entries_count: 生成的审计条目数
            - file_path: 本地 JSONL 文件路径（如有）
            - timestamp: 审计时间
            - status: 执行状态
        """
        try:
            # 读取黑板所有数据
            blackboard_data = self.team_room.read_all()

            # 构建审计条目
            entries = self._build_audit_entries(blackboard_data)

            # 写入本地 JSONL 文件
            file_path = self._write_jsonl(entries)

            # 组装审计结果
            result: Dict[str, Any] = {
                "entries": entries,
                "entries_count": len(entries),
                "file_path": file_path,
                "timestamp": self._now_iso(),
                "status": "completed",
            }

            return result

        except Exception as exc:
            # 异常时返回降级结果，不抛出（保证审计链路不中断）
            error_result: Dict[str, Any] = {
                "entries": [],
                "entries_count": 0,
                "file_path": None,
                "timestamp": self._now_iso(),
                "status": "error",
                "error_message": str(exc),
            }
            self._log_warning(f"审计执行异常: {exc}")
            return error_result

    def on_message(self, message: str) -> None:
        """
        处理消息：当消息以 @name 开头时触发执行。

        Args:
            message: 接收到的消息字符串
        """
        if message.startswith(f"@{self.name}"):
            self.execute({"action": "audit"})
