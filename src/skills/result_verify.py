# @agent: session-260809-golden-eagle | module: skills/result_verify | ts: 2026-08-09T12:53+08:00
"""
skills.result_verify — 结果验证 Skill（ResultVerify）

对最终答案执行**确定性自检**（纯逻辑、零模型依赖），输出核查结论与评分，
供 Validator Agent 在结果出厂前做最后把关。

核查维度（3 项布尔检查 + 加权评分）：

    completeness（完整性）
        - 答案非空且达到最小实质长度（_MIN_ANSWER_LEN = 10），排除"完成"式占位答复
        - 若提供 expected_keys：每个期望键/要点均出现在答案中
          （答案可解析为 JSON 对象时按顶层键精确匹配，否则按子串匹配）

    format（格式）
        - 答案类型为 str（input_schema 亦强制，双保险）
        - 不含占位/未完成标记（TODO / TBD / 待补充 等，见 _PLACEHOLDERS）
        - 不是 "null" / "None" / "N/A" 等空值文本
        - 若以 { 或 [ 开头声明 JSON：必须能通过 json.loads 解析
          （拦截"看起来像 JSON 其实是坏文本"的输出）

    consistency（一致性）
        - 内部自洽：答案中不出现互为否定的句子对
          （如「系统支持加密」与「系统不支持加密」并存；
          判定规则：一方去除否定词后与另一方归一化文本完全一致）
        - 与 reference 一致（若提供）：
            * 引用句覆盖比例 >= _REF_COVERAGE_THRESHOLD (0.6)
            * 覆盖判定：归一化子串匹配，或 2-gram 重叠 >= _TOKEN_COVERAGE_THRESHOLD
              （容忍「并记录了完整的…」这类插入语）
            * 矛盾判定：答案包含「否定词 + 引用句核心后缀」即判矛盾
              （如 reference 言「系统支持加密存储」，答案写「系统不支持加密存储」）

评分（deterministic，公式固定）：
    score = 0.4 * completeness + 0.3 * format + 0.3 * consistency
    passed = 三项检查全部为 True（此时 score 恒为 1.0）
    score 保留 2 位小数，夹取在 [0, 1]

返回结构（execute / verify_result 统一）：
    {
        "passed":  bool,    # 是否全部通过
        "checks":  {"completeness": bool, "format": bool, "consistency": bool},
        "issues":  list[str],  # 未通过检查及其原因（全通过时为空列表）
        "score":   float,   # [0, 1] 加权分
    }

异常层次（输入校验）：
    - 缺少 answer / 字段类型错误 / 违反 JSON Schema → ValueError（raise，
      属调用方编程错误，Validator 应修正调用而非吞掉）
    - 核查过程意外异常 → 兜底返回 passed=False 的失败结论（不抛出，
      保证 Validator 始终拿到一个可解释的判定）

设计约束：
    - 纯确定性逻辑：不 import 模型、不触发推理、无外部 IO、无随机性
    - 完整类型注解 + 文档字符串，供 G17-test 直接编写单元测试
    - F:\\SelfBrain 与 F:\\agent-teams-sdk 零修改（本模块只 import 其公开接口）
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from agent_teams_sdk.skills.base_skill import BaseSkill

# ---------------------------------------------------------------------------
# 常量（核查阈值与启发式规则，集中定义便于测试与调参）
# ---------------------------------------------------------------------------

#: 答案最小实质长度（去首尾空白后），低于视为"未完成"
_MIN_ANSWER_LEN: int = 10

#: 参与一致性比对的最小句子长度（归一化后字符数），过滤纯符号/极短句
_MIN_SENTENCE_LEN: int = 4

#: 与 reference 比对时的最低要点覆盖率（matched / 引用句总数）
_REF_COVERAGE_THRESHOLD: float = 0.6

#: 引用句"覆盖"判定的 2-gram 重叠阈值（句内 token 覆盖比例，容忍插入语）
_TOKEN_COVERAGE_THRESHOLD: float = 0.6

#: 句内否定检测的最小核心后缀长度（否定词紧邻该后缀，如「不+支持加密存储」）
_MIN_NEGATED_CORE_LEN: int = 3

#: 评分权重：完整性 0.4 / 格式 0.3 / 一致性 0.3（三者之和恒为 1.0）
_W_COMPLETENESS: float = 0.4
_W_FORMAT: float = 0.3
_W_CONSISTENCY: float = 0.3

#: 占位/未完成标记（小写子串匹配）
_PLACEHOLDERS: Tuple[str, ...] = (
    "todo",
    "tbd",
    "fixme",
    "lorem ipsum",
    "placeholder",
    "待补充",
    "待完善",
    "占位",
    "未实现",
    "此处省略",
)

#: 空值文本（归一化后精确匹配）
_NULLISH: Tuple[str, ...] = ("null", "none", "na", "n/a")

#: 否定词前缀（多字在前，用于「否定词 + 引用句」矛盾检测）
_NEGATORS: Tuple[str, ...] = (
    "不支持",
    "不包含",
    "没有",
    "无法",
    "不会",
    "不能",
    "未",
    "没",
    "不",
    "无",
    "非",
    "not ",
    "no ",
    "never ",
)

#: 归一化时移除的字符集合（中英文标点 + 空白 + 引号括号）
_PUNCT_RE = re.compile(r"[，。！？；：、,.!?;:()（）\[\]【】\"\"''\"'<>《》\s\-—_]+")

#: JSON 解析失败哨兵（区别于合法返回的 None）
_INVALID: object = object()

__all__ = ["ResultVerify", "verify_result"]


# ---------------------------------------------------------------------------
# 纯函数核心（不依赖 Skill 实例，便于 G17-test 单测）
# ---------------------------------------------------------------------------


def verify_result(
    answer: str,
    expected_keys: Optional[List[str]] = None,
    reference: Optional[str] = None,
) -> Dict[str, Any]:
    """对最终答案执行三项自检并评分（纯函数，ResultVerify.execute 的内核）。

    Args:
        answer: 待核查的最终答案文本（必填，str）。
        expected_keys: 期望出现在答案中的键/要点列表（可选）。
            答案可解析为 JSON 对象时按顶层键精确匹配；否则按子串匹配。
        reference: 参考答案/权威原文（可选），用于一致性比对：
            - 引用句覆盖率 >= _REF_COVERAGE_THRESHOLD 才算一致
            - 答案中出现「否定词 + 引用句原文」即判矛盾

    Returns:
        核查结论 dict：
            passed: 三项检查是否全部通过。
            checks: {"completeness", "format", "consistency"} 各自的布尔结果。
            issues: 未通过检查及其原因列表（全通过时为空列表）。
            score: 加权评分（0.4*完整性 + 0.3*格式 + 0.3*一致性），保留 2 位小数。
    """
    c_ok, c_issues = _check_completeness(answer, expected_keys)
    f_ok, f_issues = _check_format(answer)
    k_ok, k_issues = _check_consistency(answer, reference)

    checks: Dict[str, bool] = {
        "completeness": c_ok,
        "format": f_ok,
        "consistency": k_ok,
    }
    issues: List[str] = c_issues + f_issues + k_issues

    score = round(
        _W_COMPLETENESS * float(c_ok)
        + _W_FORMAT * float(f_ok)
        + _W_CONSISTENCY * float(k_ok),
        2,
    )
    return {
        "passed": bool(all(checks.values())),
        "checks": checks,
        "issues": issues,
        "score": score,
    }


# ---------------------------------------------------------------------------
# 三项检查的私有实现
# ---------------------------------------------------------------------------


def _check_completeness(
    answer: str,
    expected_keys: Optional[List[str]],
) -> Tuple[bool, List[str]]:
    """完整性检查：非空 + 最小长度 + expected_keys 覆盖。

    Args:
        answer: 答案文本。
        expected_keys: 期望键列表（None 或空列表表示不检查键覆盖）。

    Returns:
        (是否通过, 问题列表)。问题列表为空表示通过。
    """
    issues: List[str] = []
    ok = True
    stripped = answer.strip()

    if not stripped:
        return False, ["答案为空，完整性不满足"]

    if len(stripped) < _MIN_ANSWER_LEN:
        ok = False
        issues.append(
            f"答案过短（{len(stripped)} 字符 < {_MIN_ANSWER_LEN}），疑似未完成"
        )

    keys = expected_keys or []
    if keys:
        parsed = _try_loads(stripped)
        if isinstance(parsed, dict):
            # JSON 对象：按顶层键精确匹配
            missing = [k for k in keys if k not in parsed]
        else:
            # 普通文本：子串匹配（归一化后再比一次，容忍标点差异）
            answer_norm = _norm(answer)
            missing = [
                k for k in keys if k not in answer and _norm(k) not in answer_norm
            ]
        if missing:
            ok = False
            issues.append(f"缺少期望键/要点: {missing}")

    return ok, issues


def _check_format(answer: str) -> Tuple[bool, List[str]]:
    """格式检查：类型 / 占位标记 / 空值文本 / 伪 JSON。

    Args:
        answer: 答案文本。

    Returns:
        (是否通过, 问题列表)。问题列表为空表示通过。
    """
    issues: List[str] = []
    ok = True

    if not isinstance(answer, str):
        return False, [f"answer 类型不是 str（实际 {type(answer).__name__}），格式不满足"]

    low = answer.lower()
    hits = [p for p in _PLACEHOLDERS if p in low]
    if hits:
        ok = False
        issues.append(f"包含占位/未完成标记: {hits}")

    if _norm(answer.strip()) in _NULLISH:
        ok = False
        issues.append(f"答案为空值文本（{answer.strip()!r}），疑似无实际输出")

    stripped = answer.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        if _try_loads(stripped) is _INVALID:
            ok = False
            issues.append("答案以 JSON 对象/数组形式开头，但无法解析为合法 JSON")

    return ok, issues


def _check_consistency(
    answer: str,
    reference: Optional[str],
) -> Tuple[bool, List[str]]:
    """一致性检查：内部自洽 + 与 reference 一致（若提供）。

    内部自洽：任意两句子对 (A, B)，若 B ∈ _negated_variants(A)（B 可由 A 去除
    一个否定词得到，或反之），判定为矛盾——如「支持加密」与「不支持加密」并存。

    与 reference 一致：
        - 每个有语义载荷的引用句 S：先查矛盾（答案包含「否定词 + S 的核心后缀」），
          再查覆盖（norm(S) ⊆ norm(answer)，或 2-gram 重叠 >= 阈值）。
        - 覆盖率 = matched / 引用句总数，低于 _REF_COVERAGE_THRESHOLD 即不通过。

    Args:
        answer: 答案文本。
        reference: 参考答案（None 或空白则跳过 reference 比对）。

    Returns:
        (是否通过, 问题列表)。问题列表为空表示通过。
    """
    issues: List[str] = []
    ok = True

    # 1. 内部自洽
    sents = _meaningful(_split_sentences(answer))
    for i in range(len(sents)):
        for j in range(i + 1, len(sents)):
            a = _norm(sents[i])
            b = _norm(sents[j])
            if a == b:
                continue  # 重复表述不视为矛盾
            if _mutually_negated(a, b):
                ok = False
                issues.append(
                    f"内部矛盾: 「{sents[i]}」与「{sents[j]}」互为否定"
                )

    # 2. 与 reference 一致（可选）
    if reference and reference.strip():
        ref_sents = _meaningful(_split_sentences(reference))
        if ref_sents:
            answer_norm = _norm(answer)
            matched = 0
            contradicted: List[str] = []
            for s in ref_sents:
                sn = _norm(s)
                if not sn:
                    continue
                if _answer_negates(answer_norm, sn):
                    # 矛盾优先判定：被否定的引用句不计入覆盖
                    contradicted.append(s)
                elif _sentence_covered(sn, answer_norm):
                    matched += 1
            if contradicted:
                ok = False
                issues.append(
                    f"答案与 reference 矛盾（对引用句采用了否定形式）: "
                    f"{contradicted[:5]}"
                )
            ratio = matched / len(ref_sents)
            if ratio < _REF_COVERAGE_THRESHOLD:
                ok = False
                issues.append(
                    f"答案对 reference 的要点覆盖率不足: "
                    f"{ratio:.2f} < {_REF_COVERAGE_THRESHOLD}"
                )

    return ok, issues


# ---------------------------------------------------------------------------
# 文本工具
# ---------------------------------------------------------------------------


def _norm(text: str) -> str:
    """归一化文本：去中英文标点/空白/引号括号并转小写，用于一致性比对。

    Args:
        text: 原始文本。

    Returns:
        归一化后的紧凑小写字符串。
    """
    return _PUNCT_RE.sub("", text).lower()


def _split_sentences(text: str) -> List[str]:
    """按中英文句末标点/分号/换行切分句子。

    Args:
        text: 原始文本。

    Returns:
        非空句子列表（已 strip）。
    """
    return [s.strip() for s in re.split(r"[。！？!?；;\n]+", text) if s.strip()]


def _meaningful(sentences: Sequence[str]) -> List[str]:
    """过滤过短/纯符号句子，保留有语义载荷的句子。

    Args:
        sentences: 原始句子序列。

    Returns:
        归一化长度 >= _MIN_SENTENCE_LEN 的句子列表。
    """
    return [s for s in sentences if len(_norm(s)) >= _MIN_SENTENCE_LEN]


def _try_loads(text: str) -> Any:
    """尝试将文本解析为 JSON。

    Args:
        text: 待解析文本。

    Returns:
        解析成功返回对应 Python 对象；失败返回哨兵 _INVALID。
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return _INVALID


def _negated_variants(s: str) -> set[str]:
    """生成去除任意一个否定词后的变体集合（含原串）。

    用于句子级矛盾判定：A 与 B 互为否定 ⇔ B 可通过从 A 中移除一个否定词得到
    （或反之）。例如「系统不支持加密存储」移除「不」→「系统支持加密存储」。

    Args:
        s: 归一化文本。

    Returns:
        {原串} ∪ {移除一个否定词片段后的各变体}。
    """
    variants: set[str] = {s}
    for neg in _NEGATORS:
        idx = s.find(neg)
        if idx != -1:
            variants.add(s[:idx] + s[idx + len(neg):])
    return variants


def _mutually_negated(a: str, b: str) -> bool:
    """判断两个归一化句子是否互为否定（一方向去除否定词后与另一方一致）。

    Args:
        a: 句子 A 的归一化文本。
        b: 句子 B 的归一化文本。

    Returns:
        True 表示互为否定（矛盾）；否则 False。
    """
    return a != b and (b in _negated_variants(a) or a in _negated_variants(b))


def _answer_negates(answer_norm: str, ref_sentence_norm: str) -> bool:
    """判断答案是否对引用句采用了否定形式（句内否定检测）。

    规则：答案中包含「否定词 + 引用句核心后缀（长度 >= _MIN_NEGATED_CORE_LEN）」
    即判矛盾。核心后缀取引用句去掉前 (0..len-MIN) 个字符后的剩余片段，
    覆盖「系统不支持加密存储」（= 系统 + 不 + 支持加密存储）这类句内否定，
    同时避免把无关位置的否定词误判为矛盾。

    Args:
        answer_norm: 答案的归一化文本。
        ref_sentence_norm: 引用句的归一化文本。

    Returns:
        True 表示答案包含该引用句的否定形式（矛盾信号）。
    """
    sn = ref_sentence_norm
    for neg in _NEGATORS:
        # 整句前缀否定（neg + 全句）
        if (neg + sn) in answer_norm:
            return True
        # 句内否定（neg + 后缀，后缀长度 >= _MIN_NEGATED_CORE_LEN）
        if len(sn) >= _MIN_NEGATED_CORE_LEN + 1:
            for i in range(len(sn) - _MIN_NEGATED_CORE_LEN + 1):
                if (neg + sn[i:]) in answer_norm:
                    return True
    return False


def _bigrams(s: str) -> set[str]:
    """生成句子的 2-gram 集合（长度 < 2 时退化为单字符集合）。

    用于覆盖判定：引用句与答案的 2-gram 重叠比例 >= _TOKEN_COVERAGE_THRESHOLD
    即视为被覆盖，容忍「并记录了完整的…」这类插入语造成的子串失配。

    Args:
        s: 归一化文本。

    Returns:
        2-gram 集合（空串返回空集）。
    """
    if not s:
        return set()
    if len(s) < 2:
        return {s}
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _sentence_covered(ref_norm: str, answer_norm: str) -> bool:
    """判断引用句是否被答案覆盖（精确子串 或 2-gram 重叠 >= 阈值）。

    Args:
        ref_norm: 引用句的归一化文本。
        answer_norm: 答案的归一化文本。

    Returns:
        True 表示覆盖；否则 False。
    """
    if ref_norm in answer_norm:
        return True
    ref_bigrams = _bigrams(ref_norm)
    if not ref_bigrams:
        return False
    answer_bigrams = _bigrams(answer_norm)
    overlap = len(ref_bigrams & answer_bigrams) / len(ref_bigrams)
    return overlap >= _TOKEN_COVERAGE_THRESHOLD


# ---------------------------------------------------------------------------
# Skill 类
# ---------------------------------------------------------------------------


class ResultVerify(BaseSkill):
    """结果验证 Skill：对最终答案做完整性/格式/一致性自检并评分。

    继承 agent-teams-sdk 的 BaseSkill：
        - schema（input/output JSON Schema）由本类提供，
          BaseSkill.validate_input / get_schema 均可用
        - execute(input) 接收含 answer / expected_keys / reference 的输入 dict，
          返回核查结论 dict

    Attributes:
        name: Skill 名（"result_verify"）。
        version: 版本号。
        description: 人类可读说明。
        input_schema: 输入 JSON Schema（answer 必填，expected_keys/reference 可选）。
        output_schema: 输出 JSON Schema（passed/checks/issues/score）。
        schema: BaseSkill 契约格式 {"input": ..., "output": ...}。

    Example:
        >>> skill = ResultVerify()
        >>> result = skill.execute(input={
        ...     "answer": "系统支持加密存储，并记录了完整的审计日志。",
        ...     "expected_keys": ["加密", "审计日志"],
        ... })
        >>> result["passed"]
        True
    """

    name: str = "result_verify"
    version: str = "1.0.0"
    description: str = (
        "结果验证：对最终答案做完整性/格式/一致性自检并评分，"
        "输出核查结论（供 Validator 使用）。"
    )

    input_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "minLength": 1,
                "description": "待核查的最终答案文本（必填）。",
            },
            "expected_keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "期望出现在答案中的键/要点列表（可选）。",
            },
            "reference": {
                "type": "string",
                "description": "参考答案/权威原文，用于一致性比对（可选）。",
            },
        },
        "required": ["answer"],
        "additionalProperties": False,
    }

    output_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "passed": {
                "type": "boolean",
                "description": "三项检查是否全部通过。",
            },
            "checks": {
                "type": "object",
                "properties": {
                    "completeness": {"type": "boolean"},
                    "format": {"type": "boolean"},
                    "consistency": {"type": "boolean"},
                },
                "required": ["completeness", "format", "consistency"],
            },
            "issues": {
                "type": "array",
                "items": {"type": "string"},
                "description": "未通过检查及其原因（全通过时为空）。",
            },
            "score": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "加权评分（保留 2 位小数）。",
            },
        },
        "required": ["passed", "checks", "issues", "score"],
    }

    #: BaseSkill 契约：schema.input 供 validate_input / get_schema 使用
    schema: Dict[str, Any] = {"input": input_schema, "output": output_schema}

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def execute(self, input: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        """执行结果自检（BaseSkill.execute 实现）。

        入参两种形态均支持（内部合并为同一 payload）：
            1. skill.execute(input={"answer": ..., "expected_keys": [...], "reference": ...})
            2. skill.execute(answer=..., expected_keys=[...])  # kwargs 展开形态

        校验顺序：
            1. BaseSkill.validate_input(**payload) —— required=["answer"] 必填检查
            2. jsonschema.validate(payload, input_schema) —— 深度类型校验
               （环境缺 jsonschema 时降级为 _manual_validate）
            校验失败抛 ValueError（调用方编程错误，需修正后重试）。

        Args:
            input: 输入 dict，含 answer（必填）/ expected_keys（可选）/ reference（可选）。
            **kwargs: 若 input 为 None，接受展开后的同名关键字参数。

        Returns:
            核查结论 dict：{"passed", "checks", "issues", "score"}（见模块文档）。
            核查过程本身异常时兜底返回 passed=False 的失败结论（不抛出）。

        Raises:
            ValueError: payload 缺少 answer 或字段类型违反 JSON Schema。
        """
        payload = input if isinstance(input, dict) else {}
        if not payload:
            payload = kwargs

        self._validate_schema(payload)

        try:
            return verify_result(
                answer=payload["answer"],
                expected_keys=payload.get("expected_keys"),
                reference=payload.get("reference"),
            )
        except Exception as exc:  # noqa: BLE001 —— 兜底：核查异常也给出可解释判定
            return {
                "passed": False,
                "checks": {
                    "completeness": False,
                    "format": False,
                    "consistency": False,
                },
                "issues": [f"核查过程异常: {type(exc).__name__}: {exc}"],
                "score": 0.0,
            }

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _validate_schema(self, payload: Dict[str, Any]) -> None:
        """输入 schema 校验：BaseSkill 必填检查 + jsonschema 深度校验。

        Args:
            payload: 待校验的输入 dict。

        Raises:
            ValueError: 缺少必填字段或字段类型违反 JSON Schema。
        """
        # 1) BaseSkill 契约校验（required=["answer"]，缺失时抛 ValueError）
        self.validate_input(**payload)

        # 2) jsonschema 深度校验（类型/可选字段/禁止多余字段）
        if _HAS_JSONSCHEMA:
            try:
                jsonschema.validate(payload, self.input_schema)
            except jsonschema.ValidationError as exc:
                path = "/".join(str(p) for p in exc.path)
                raise ValueError(
                    f"input 未通过 JSON Schema 校验: {exc.message}"
                    + (f"（字段路径: {path}）" if path else "")
                ) from exc
        else:
            # 环境缺少 jsonschema 时的手动降级校验（等价规则）
            _manual_validate(payload)


# ---------------------------------------------------------------------------
# jsonschema 可用性探测 + 手动降级校验
# ---------------------------------------------------------------------------

try:  # pyproject 已声明 jsonschema>=4.0，此处仅为裸环境兜底
    import jsonschema  # noqa: F401

    _HAS_JSONSCHEMA: bool = True
except ImportError:  # pragma: no cover —— 正常环境不可达
    _HAS_JSONSCHEMA = False


def _manual_validate(payload: Dict[str, Any]) -> None:
    """jsonschema 不可用时的等价手动校验（规则与 input_schema 一致）。

    Args:
        payload: 待校验的输入 dict。

    Raises:
        ValueError: 缺少必填字段或字段类型不符合 input_schema。
    """
    if "answer" not in payload:
        raise ValueError("缺少必填字段: answer")
    if not isinstance(payload["answer"], str):
        raise ValueError(f"answer 必须为 str（实际 {type(payload['answer']).__name__}）")
    if not payload["answer"]:
        raise ValueError("answer 不能为空字符串")

    if "expected_keys" in payload:
        if not isinstance(payload["expected_keys"], list):
            raise ValueError("expected_keys 必须为 array[str]")
        if not all(isinstance(k, str) for k in payload["expected_keys"]):
            raise ValueError("expected_keys 的元素必须全部为 str")

    if "reference" in payload and not isinstance(payload["reference"], str):
        raise ValueError(
            f"reference 必须为 str（实际 {type(payload['reference']).__name__}）"
        )

    allowed = {"answer", "expected_keys", "reference"}
    extra = set(payload) - allowed
    if extra:
        raise ValueError(f"不允许的多余字段: {sorted(extra)}")
