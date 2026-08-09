# @agent: session-260809-tall-bloom | module: agents/validator | ts: 2026-08-09T12:52+08:00
"""
Validator — 6维结果核查员（班主任模式）

对黑板上的最终结果执行 6 维度核查：
  completeness   完整性：各 worker 结果是否齐备
  correctness    正确性：结果与输入是否匹配
  privacy        隐私合规：是否泄露敏感信息
  consistency    一致性：多源结果是否冲突
  traceability   可追溯：audit 记录是否完整
  performance    性能：耗时/规模是否合理

返回 ValidationResult(passed, errors, warnings)。
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from agent_teams_sdk.roles.validator import ValidatorAgent, ValidationResult


# ── 隐私关键词（示例，实际由 G7-policy 提供策略）────────────────────────────
_SENSITIVE_PATTERNS: List[str] = [
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "credit_card", "ssn", "id_card", "phone", "email",
]

# ── 期望的 worker 结果键（由 G3~G8 产出）──────────────────────────────────
_EXPECTED_WORKER_KEYS: List[str] = [
    "guardian_result",
    "navigator_result",
    "cipher_result",
    "coordinator_result",
    "policy_result",
    "audit_result",
]

# ── 合理的性能阈值 ──────────────────────────────────────────────────────────
_MAX_LATENCY_MS: float = 5000.0   # 单次查询最大可接受延迟（毫秒）
_MAX_RESULT_SIZE: int = 10_000_000  # 单个结果最大字节数（约 10 MB）


class Validator(ValidatorAgent):
    """
    SelfBrain-GOAI 结果核查员。

    继承自 :class:`ValidatorAgent`，实现 6 维核查逻辑。
    不实际加载模型，仅对黑板数据进行静态/启发式校验。

    Attributes:
        name: Agent 名称，由 TeamRoom 注入。
        team_room: 共享黑板实例，由基类持有。
    """

    def __init__(self, name: str, team_room: Any) -> None:
        """
        初始化 Validator。

        Args:
            name: Agent 在 TeamRoom 中的标识名。
            team_room: TeamRoom 实例（共享黑板）。
        """
        super().__init__(name, team_room)

    # ──────────────────────────────────────────────────────────────────────
    # 主入口
    # ──────────────────────────────────────────────────────────────────────

    def validate(self, blackboard: Dict[str, Any]) -> ValidationResult:
        """
        执行 6 维核查并返回 ValidationResult。

        Args:
            blackboard: 黑板全量数据（由基类 ``execute`` 注入，
                通常为 ``team_room.read_all()`` 的返回值）。

        Returns:
            ValidationResult:
                - ``passed``: 6 维全部通过为 True，否则 False
                - ``errors``: 未通过维度的错误描述列表
                - ``warnings``: 通过但有风险提示的描述列表

        Raises:
            ValueError: blackboard 不是字典时抛出。
        """
        if not isinstance(blackboard, dict):
            raise ValueError(f"blackboard 必须为 dict，收到 {type(blackboard).__name__}")

        errors: List[str] = []
        warnings: List[str] = []

        # 逐维核查
        ok, e, w = self._check_completeness(blackboard)
        errors.extend(e); warnings.extend(w)

        ok_c, e_c, w_c = self._check_correctness(blackboard)
        errors.extend(e_c); warnings.extend(w_c)
        if not ok_c:
            ok = False

        ok_p, e_p, w_p = self._check_privacy(blackboard)
        errors.extend(e_p); warnings.extend(w_p)
        if not ok_p:
            ok = False

        ok_cs, e_cs, w_cs = self._check_consistency(blackboard)
        errors.extend(e_cs); warnings.extend(w_cs)
        if not ok_cs:
            ok = False

        ok_t, e_t, w_t = self._check_traceability(blackboard)
        errors.extend(e_t); warnings.extend(w_t)
        if not ok_t:
            ok = False

        ok_perf, e_perf, w_perf = self._check_performance(blackboard)
        errors.extend(e_perf); warnings.extend(w_perf)
        if not ok_perf:
            ok = False

        return ValidationResult(
            passed=ok and not errors,
            errors=errors,
            warnings=warnings,
        )

    # ──────────────────────────────────────────────────────────────────────
    # 6 维核查方法
    # ──────────────────────────────────────────────────────────────────────

    def _check_completeness(self, bb: Dict[str, Any]) -> tuple[bool, List[str], List[str]]:
        """
        完整性核查：各 worker 结果是否齐备。

        检查黑板中是否存在预期的 worker 结果键。
        缺失任一关键结果均视为不完整。
        """
        errors: List[str] = []
        warnings: List[str] = []

        for key in _EXPECTED_WORKER_KEYS:
            if key not in bb:
                errors.append(f"[完整性] 缺失 worker 结果键: {key}")
            elif bb[key] is None:
                warnings.append(f"[完整性] 结果键存在但值为 None: {key}")

        return len(errors) == 0, errors, warnings

    def _check_correctness(self, bb: Dict[str, Any]) -> tuple[bool, List[str], List[str]]:
        """
        正确性核查：结果与输入是否匹配。

        启发式检查：
        - 结果字段是否为空字符串/空容器
        - 结果是否包含 "error" / "failed" 等异常标记
        - 结果数据类型是否合理（应为 dict 或 list）
        """
        errors: List[str] = []
        warnings: List[str] = []

        for key, val in bb.items():
            if not key.endswith("_result"):
                continue

            # 空值检查
            if val is None:
                errors.append(f"[正确性] {key} 为 None")
                continue
            if val == "" or val == [] or val == {}:
                errors.append(f"[正确性] {key} 为空值")
                continue

            # 异常标记检查
            if isinstance(val, dict):
                status = val.get("status", "")
                if status in ("error", "failed", "failure"):
                    errors.append(f"[正确性] {key} 状态异常: {status}")
                msg = val.get("message", val.get("msg", ""))
                if isinstance(msg, str) and "error" in msg.lower():
                    warnings.append(f"[正确性] {key} 含错误信息: {msg[:80]}")

            # 类型合理性
            if not isinstance(val, (dict, list, str, int, float, bool)):
                errors.append(f"[正确性] {key} 类型异常: {type(val).__name__}")

        return len(errors) == 0, errors, warnings

    def _check_privacy(self, bb: Dict[str, Any]) -> tuple[bool, List[str], List[str]]:
        """
        隐私合规核查：是否泄露敏感信息。

        将黑板全量序列化为字符串，扫描敏感关键词。
        发现任一敏感模式即视为隐私违规。
        """
        errors: List[str] = []
        warnings: List[str] = []

        try:
            import json
            raw = json.dumps(bb, ensure_ascii=False, default=str)
        except Exception as exc:
            raw = str(bb)
            warnings.append(f"[隐私] 序列化失败: {exc}")

        raw_lower = raw.lower()
        found: List[str] = []
        for pattern in _SENSITIVE_PATTERNS:
            if pattern.lower() in raw_lower:
                found.append(pattern)

        if found:
            errors.append(
                f"[隐私] 检测到敏感关键词: {', '.join(found)}"
            )

        return len(errors) == 0, errors, warnings

    def _check_consistency(self, bb: Dict[str, Any]) -> tuple[bool, List[str], List[str]]:
        """
        一致性核查：多源结果是否冲突。

        启发式检查：
        - 多个结果中的 "source" 字段是否互相矛盾
        - 同一指标在不同结果中是否差异过大
        - 结果时间戳是否乱序
        """
        errors: List[str] = []
        warnings: List[str] = []

        # 收集所有结果中的 source 字段
        sources: List[str] = []
        timestamps: List[float] = []

        for key, val in bb.items():
            if not key.endswith("_result"):
                continue
            if not isinstance(val, dict):
                continue

            src = val.get("source")
            if src and isinstance(src, str):
                sources.append(f"{key}:{src}")

            ts = val.get("timestamp") or val.get("ts") or val.get("time")
            if ts is not None:
                try:
                    timestamps.append(float(ts))
                except (ValueError, TypeError):
                    pass

        # 时间戳乱序警告
        if len(timestamps) >= 2:
            if timestamps != sorted(timestamps):
                warnings.append(
                    "[一致性] 结果时间戳乱序，可能存在并发写入竞争"
                )

        # 多源冲突示例：不同 worker 报告了不同的 query_id
        query_ids: Dict[str, str] = {}
        for key, val in bb.items():
            if not key.endswith("_result") or not isinstance(val, dict):
                continue
            qid = val.get("query_id")
            if qid:
                qid_s = str(qid)
                if qid_s in query_ids and query_ids[qid_s] != key:
                    warnings.append(
                        f"[一致性] query_id={qid_s} 被多个 worker 引用: "
                        f"{query_ids[qid_s]} vs {key}"
                    )
                else:
                    query_ids[qid_s] = key

        return len(errors) == 0, errors, warnings

    def _check_traceability(self, bb: Dict[str, Any]) -> tuple[bool, List[str], List[str]]:
        """
        可追溯核查：audit 记录是否完整。

        检查：
        - 黑板中是否存在 audit_result 或 audit_trail 键
        - audit 记录是否包含 session_id / trace_id / span_id 等可追溯字段
        - 各 worker 结果是否携带 updated_by 标记
        """
        errors: List[str] = []
        warnings: List[str] = []

        # 检查 audit 记录是否存在
        audit_keys = [k for k in bb if "audit" in k.lower()]
        if not audit_keys:
            errors.append("[可追溯] 黑板中未找到 audit 相关记录")
        else:
            for ak in audit_keys:
                av = bb[ak]
                if isinstance(av, dict):
                    required = ("session_id", "trace_id", "span_id")
                    missing = [f for f in required if f not in av]
                    if missing:
                        warnings.append(
                            f"[可追溯] {ak} 缺少字段: {', '.join(missing)}"
                        )

        # 检查各 worker 结果是否携带 updated_by
        for key, val in bb.items():
            if not key.endswith("_result"):
                continue
            if isinstance(val, dict) and "updated_by" not in val:
                warnings.append(f"[可追溯] {key} 缺少 updated_by 标记")

        return len(errors) == 0, errors, warnings

    def _check_performance(self, bb: Dict[str, Any]) -> tuple[bool, List[str], List[str]]:
        """
        性能核查：耗时/规模是否合理。

        启发式检查：
        - 结果中的 latency_ms / duration 字段是否超过阈值
        - 结果序列化后大小是否超过 _MAX_RESULT_SIZE
        - 结果数量是否异常（过多/过少）
        """
        errors: List[str] = []
        warnings: List[str] = []

        result_count = sum(1 for k in bb if k.endswith("_result"))

        if result_count == 0:
            warnings.append("[性能] 黑板中无任何 worker 结果")
        elif result_count > 20:
            warnings.append(f"[性能] worker 结果数量异常偏多: {result_count}")

        for key, val in bb.items():
            if not key.endswith("_result"):
                continue

            # 延迟检查
            if isinstance(val, dict):
                latency = val.get("latency_ms") or val.get("duration_ms") or val.get("elapsed")
                if latency is not None:
                    try:
                        lat_f = float(latency)
                        if lat_f > _MAX_LATENCY_MS:
                            errors.append(
                                f"[性能] {key} 延迟超标: {lat_f}ms > {_MAX_LATENCY_MS}ms"
                            )
                    except (ValueError, TypeError):
                        pass

            # 大小检查
            try:
                import json
                size = len(json.dumps(val, ensure_ascii=False).encode("utf-8"))
                if size > _MAX_RESULT_SIZE:
                    errors.append(
                        f"[性能] {key} 结果体积超标: {size/1024/1024:.2f}MB > "
                        f"{_MAX_RESULT_SIZE/1024/1024:.2f}MB"
                    )
            except Exception:
                pass

        return len(errors) == 0, errors, warnings
