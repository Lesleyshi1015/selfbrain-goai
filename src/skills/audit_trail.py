# @agent: session-260809-airy-cedar | module: skills/audit_trail | ts: 2026-08-09T12:53+08:00
"""
audit_trail - 审计追踪 Skill

格式化审计事件（entries）、聚合各 Agent 统计（summary）、
并生成可读的审计报告（report）。供 Audit Agent（G8）在
review/audit 流程中记录与追溯系统行为使用。

接口契约（CHANGE-002 §验收标准）：
    input  : {"events": [{"ts": str, "agent": str, "action": str, "result": str}, ...]}
    output : {"entries": [str, ...],
              "summary": {"total": int, "by_agent": {agent: count}},
              "report": str}
"""
from __future__ import annotations

from typing import Any, Dict, List

import jsonschema

from agent_teams_sdk.skills.base_skill import BaseSkill


class AuditTrail(BaseSkill):
    """
    AuditTrail - 审计追踪技能

    职责：
        1. 将审计事件逐条格式化为固定样式的行（entries）
        2. 按 Agent 聚合事件数量，生成统计摘要（summary）
        3. 生成包含时间范围、各 Agent 明细与统计的文本报告（report）

    事件格式约定：
        每条事件为 dict，必含 4 个字段：
            ts     : 时间戳字符串（如 "2026-08-09T12:00+08:00"）
            agent  : 产生事件的 Agent 标识（如 "G8-audit"）
            action : 动作描述（如 "review:detect_changes"）
            result : 动作结果（如 "ok" / "fail: <原因>"）

    校验：
        - 输入经 JSON Schema 严格校验（jsonschema，Draft202012）
        - 缺失/类型错误/空列表均抛出 ValueError，调用方可安全捕获
    """

    name: str = "audit_trail"
    version: str = "1.0.0"
    description: str = (
        "审计追踪：格式化审计事件、按 Agent 汇总统计，并生成审计报告。"
        "输入 events（事件列表），输出 entries（格式化行）、summary（统计）与 report（文本报告）。"
    )

    # 输入 Schema（任务契约：events 为对象数组，每条含 ts/agent/action/result）
    input_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ts": {"type": "string"},
                        "agent": {"type": "string"},
                        "action": {"type": "string"},
                        "result": {"type": "string"},
                    },
                    "required": ["ts", "agent", "action", "result"],
                    "additionalProperties": True,
                },
            }
        },
        "required": ["events"],
    }

    # 输出 Schema（供 SchemaValidator.register 校验 execute 结果）
    output_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "entries": {
                "type": "array",
                "items": {"type": "string"},
            },
            "summary": {
                "type": "object",
                "properties": {
                    "total": {"type": "integer"},
                    "by_agent": {
                        "type": "object",
                        "additionalProperties": {"type": "integer"},
                    },
                },
                "required": ["total", "by_agent"],
            },
            "report": {"type": "string"},
        },
        "required": ["entries", "summary", "report"],
    }

    # 完整 Schema（与 BaseSkill.get_schema / SchemaValidator.register 对齐）
    schema: Dict[str, Any] = {
        "name": name,
        "version": version,
        "description": description,
        "input": input_schema,
        "output": output_schema,
    }

    # 单条事件格式化的模板（对齐系统固定样式）
    _ENTRY_TEMPLATE: str = "[{ts}] {agent}: {action} -> {result}"

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行审计追踪：格式化事件、聚合统计、生成报告。

        Args:
            input: 输入字典，必须含 "events" 键：
                events: List[Dict[str, str]]，每条含 ts/agent/action/result。

        Returns:
            Dict[str, Any]:
                entries : List[str] 格式化后的审计行，按输入顺序逐条生成
                summary : {"total": int, "by_agent": Dict[str, int]}
                          total 为事件总数，by_agent 为各 Agent 事件计数
                report  : str 多行审计报告（含时间范围、明细与统计）

        Raises:
            ValueError: input 非 dict / 缺 events / events 非列表 / 空列表 /
                        单条事件缺字段或字段类型错误时抛出，含具体原因。
        """
        # 基类契约校验（required 字段存在性） + 严格 jsonschema 校验
        if isinstance(input, dict):
            self.validate_input(**input)
        self._validate_input(input)

        events: List[Dict[str, str]] = input["events"]
        entries = [self._format_entry(e) for e in events]
        summary = self._build_summary(events)
        report = self._build_report(events, entries, summary)
        return {"entries": entries, "summary": summary, "report": report}

    def get_schema(self) -> Dict[str, Any]:
        """获取本 Skill 的完整 Schema（含 name/version/description/input/output）。"""
        return {**super().get_schema(), "description": self.description}

    def _validate_input(self, input: Any) -> None:
        """
        校验 execute 入参（严格 JSON Schema 校验）。

        Args:
            input: 待校验的入参，应为含 events 列表的 dict。

        Raises:
            ValueError: 结构不合法时抛出，错误信息含具体失败点。
        """
        if not isinstance(input, dict):
            raise ValueError(f"audit_trail 输入必须是 dict，实际为 {type(input).__name__}")
        try:
            jsonschema.validate(instance=input, schema=self.input_schema)
        except jsonschema.ValidationError as e:
            path = "/".join(str(p) for p in e.absolute_path) or "root"
            raise ValueError(
                f"audit_trail 输入校验失败 @ {path}: {e.message}"
            ) from e
        if not input["events"]:
            raise ValueError("audit_trail 输入校验失败: events 不能为空列表")

    def _format_entry(self, event: Dict[str, str]) -> str:
        """
        将单条事件格式化为审计行。

        Args:
            event: 事件 dict，含 ts/agent/action/result。

        Returns:
            str: 形如 "[ts] agent: action -> result" 的格式化行。
        """
        return self._ENTRY_TEMPLATE.format(
            ts=event["ts"],
            agent=event["agent"],
            action=event["action"],
            result=event["result"],
        )

    @staticmethod
    def _build_summary(events: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        按 Agent 聚合事件统计。

        Args:
            events: 事件列表。

        Returns:
            Dict[str, Any]: {"total": 总数, "by_agent": {agent: 计数}}，
                            by_agent 按键（Agent 标识）字典序排序，保证输出稳定。
        """
        by_agent: Dict[str, int] = {}
        for e in events:
            agent = e["agent"]
            by_agent[agent] = by_agent.get(agent, 0) + 1
        ordered = {a: by_agent[a] for a in sorted(by_agent)}
        return {"total": len(events), "by_agent": ordered}

    def _build_report(
        self,
        events: List[Dict[str, str]],
        entries: List[str],
        summary: Dict[str, Any],
    ) -> str:
        """
        生成审计报告文本。

        Args:
            events : 原始事件列表（用于时间范围计算）。
            entries: 格式化后的审计行。
            summary: 统计摘要（total/by_agent）。

        Returns:
            str: 多行报告，含标题、时间范围、逐条明细、按 Agent 统计与总数。
        """
        ts_list = [e["ts"] for e in events]
        time_span = (
            f"{min(ts_list)} ~ {max(ts_list)}" if len(ts_list) > 1 else ts_list[0]
        )
        lines: List[str] = [
            "========== 审计报告 ==========",
            f"时间范围: {time_span}",
            f"事件总数: {summary['total']}",
            "------------------------------",
        ]
        lines.extend(f"{i + 1}. {line}" for i, line in enumerate(entries))
        lines.append("------------------------------")
        lines.append("按 Agent 统计:")
        for agent, count in summary["by_agent"].items():
            lines.append(f"  - {agent}: {count}")
        lines.append("==============================")
        return "\n".join(lines)
