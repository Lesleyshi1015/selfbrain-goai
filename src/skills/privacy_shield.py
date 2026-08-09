# @agent: session-260809-ready-horizon | module: skills/privacy_shield | ts: 2026-08-09T12:53+08:00
"""隐私盾 Skill（PrivacyShield）。

检测文本中的敏感信息（PII）——手机号 / 身份证号 / 银行卡号 / 地址 / 密钥 /
邮箱 / IP 等，并对每一处命中给出脱敏后的替换值（value_masked）与在原文中的
位置 [start, end)，同时输出整段脱敏后的文本 masked_text 与整体风险等级
risk_level（low / medium / high）。

设计依据
--------
- 继承 :class:`agent_teams_sdk.skills.base_skill.BaseSkill`（name / version /
  schema 类属性 + execute 抽象方法 + validate_input / get_schema）。
- ``schema`` 分为 ``input`` / ``output`` 两部分，均符合 JSON Schema Draft
  2020-12，可被 :class:`agent_teams_sdk.skills.schema_validator.SchemaValidator`
  注册并做输入输出校验。
- PII 检测采用正则（本文件模块级常量，便于审查与测试）；命中区间按
  ``key → id_card → bank_card → phone → address → other`` 优先级抢占，
  已占用的原文区间不再重复匹配，避免长数字串（如 18 位身份证）被子串规则
  二次命中。

返回结构
--------
``execute(text=...)`` 返回::

    {
        "detected": [
            {"type": "phone", "value_masked": "138****5678", "position": [3, 14]},
            ...
        ],
        "masked_text": "我的手机号是138****5678，请查收。",
        "risk_level": "medium",
    }

``type`` 取值: ``phone | id_card | bank_card | address | key | other``。
``position`` 为原始文本中的 [start, end) 半开区间。风险等级按命中类型最高权重
计算：key/id_card/bank_card=high，phone/other=medium，address=low。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence, Tuple

from agent_teams_sdk.skills.base_skill import BaseSkill

# ---------------------------------------------------------------------------
# 正则定义（模块级常量，便于单测直接引用）
# ---------------------------------------------------------------------------

# 手机号 / 固话：11 位大陆手机号（1[3-9] 开头）、带分隔符手机号、固定电话。
# 使用 (?<!\d) / (?!\d) 数字边界，避免命中长数字串的内部子串。
_PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:"
    r"1[3-9]\d{9}"                       # 大陆手机号 11 位
    r"|1[3-9]\d[\s-]\d{4}[\s-]\d{4}"     # 带分隔符手机号
    r"|0\d{2,3}[\s-]?\d{7,8}"            # 固定电话
    r")(?!\d)"
)

# 18 位身份证：6 位地区码 + 8 位出生日期（含 18/19/20 世纪）+ 3 位顺序码 +
# 1 位校验码（数字或 X/x）。
_ID_CARD_RE = re.compile(
    r"(?<!\d)"
    r"[1-9]\d{5}"
    r"(?:18|19|20)\d{2}"
    r"(?:0[1-9]|1[0-2])"
    r"(?:0[1-9]|[12]\d|3[01])"
    r"\d{3}"
    r"[\dXx]"
    r"(?!\d)"
)

# 银行卡：主流 BIN 前缀（银联 62/60/65/67/68/69、Visa 4、MasterCard 51-55、
# JCB 35、AMEX 34/37），长度 15-19 位。
_BANK_CARD_RE = re.compile(
    r"(?<!\d)"
    r"(?:"
    r"6[025789]\d{14,17}"     # 银联，16-19 位
    r"|4\d{15,18}"            # Visa，16-19 位
    r"|5[1-5]\d{14,17}"       # MasterCard，16-19 位
    r"|35\d{14,17}"           # JCB，16-19 位
    r"|3[47]\d{13,16}"        # AMEX，15-18 位
    r")(?!\d)"
)

# 密钥 / 凭证：AWS（AKIA/ASIA）、OpenAI 风格 sk-*、GitHub token、
# PEM 私钥块、JWT、以及 "key=value" 形式的键值式密钥。
_KEY_RE = re.compile(
    r"(?:"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}"                        # AWS Access Key
    r"|sk-[A-Za-z0-9_\-]{20,}"                          # OpenAI 风格
    r"|gh[pousr]_[A-Za-z0-9]{36,}"                      # GitHub token
    r"|-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"           # PEM 私钥块
    r"|eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\."     # JWT
    r"[A-Za-z0-9_\-]{8,}"
    r"|(?:api[_-]?key|apikey|access[_-]?token|secret|"
    r"password|passwd|token)\s*[=:：]\s*['\"]?"
    r"[A-Za-z0-9_\-\.]{16,}"                            # 键值式密钥
    r")"
)

# 中文地址：省/自治区（可选）+ 市/自治州（可选）+ 区/县 + 路/街/道 + 门牌楼栋。
# 要求必须出现"路/街/道/巷/村/庄"等层级，避免"北京市"这类地名单独被命中。
_ADDRESS_RE = re.compile(
    r"(?:[\u4e00-\u9fa5]{2,8}(?:省|自治区|特别行政区))?"
    r"(?:[\u4e00-\u9fa5]{2,8}(?:市|自治州|地区|盟))?"
    r"[\u4e00-\u9fa5]{1,8}(?:区|县|旗|市)"
    r"[\u4e00-\u9fa5A-Za-z0-9\-]{1,20}(?:路|街|道|巷|大道|公路|村|庄)"
    r"(?:[\u4e00-\u9fa5A-Za-z0-9\-号楼室栋单元组区座幢铺]{1,20}"
    r"(?:号|室|栋|单元))?"
)

# 邮箱地址。
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# IPv4 地址（每段 0-255 校验）。
_IPV4_RE = re.compile(
    r"(?<!\d)"
    r"(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
    r"(?!\d)"
)

# 中国大陆车牌号（含使领馆牌）。
_PLATE_RE = re.compile(
    r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领]"
    r"[A-Z][A-Z0-9]{5,6}"
)

# 统一社会信用代码（18 位，排除易混淆字母）。
_CREDIT_CODE_RE = re.compile(
    r"(?<![0-9A-Za-z])[0-9A-HJ-NPQRTUWXY]{2}\d{6}"
    r"[0-9A-HJ-NPQRTUWXY]{10}(?![0-9A-Za-z])"
)

# 检测管线：按优先级顺序执行；后检测的正则在原文坐标上跳过已占用区间。
# (编译正则, 类型, 脱敏策略)
_PATTERNS: Sequence[Tuple[re.Pattern, str, str]] = (
    (_KEY_RE, "key", "key"),
    (_ID_CARD_RE, "id_card", "id_card"),
    (_BANK_CARD_RE, "bank_card", "bank_card"),
    (_PHONE_RE, "phone", "phone"),
    (_ADDRESS_RE, "address", "address"),
    (_EMAIL_RE, "other", "email"),
    (_IPV4_RE, "other", "ip"),
    (_PLATE_RE, "other", "plate"),
    (_CREDIT_CODE_RE, "other", "credit_code"),
)

# 各类型对整体风险等级的权重：3=high, 2=medium, 1=low。
_RISK_WEIGHT: Dict[str, int] = {
    "key": 3,
    "id_card": 3,
    "bank_card": 3,
    "phone": 2,
    "address": 1,
    "other": 2,
}

# 输入输出 JSON Schema（Draft 2020-12）。
_PRIVACY_SHIELD_SCHEMA: Dict[str, Any] = {
    "input": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "待检测的原始文本",
            },
        },
        "required": ["text"],
        "additionalProperties": False,
    },
    "output": {
        "type": "object",
        "properties": {
            "detected": {
                "type": "array",
                "description": "检测到的敏感信息列表",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "phone",
                                "id_card",
                                "bank_card",
                                "address",
                                "key",
                                "other",
                            ],
                            "description": "敏感信息类型",
                        },
                        "value_masked": {
                            "type": "string",
                            "description": "脱敏后的替换值",
                        },
                        "position": {
                            "type": "array",
                            "description": "原文中的 [start, end) 区间",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                    },
                    "required": ["type", "value_masked", "position"],
                },
            },
            "masked_text": {
                "type": "string",
                "description": "脱敏后的整段文本",
            },
            "risk_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "整体风险等级",
            },
        },
        "required": ["detected", "masked_text", "risk_level"],
    },
}


def _mask(value: str, head: int, tail: int) -> str:
    """通用脱敏：保留前 head 个与后 tail 个字符，中间以 ``*`` 覆盖。

    Parameters
    ----------
    value : str
        待脱敏的原始值。
    head : int
        开头保留的字符数。
    tail : int
        结尾保留的字符数。

    Returns
    -------
    str
        脱敏后的字符串；若长度不足以保留 head+tail 个字符则整体打码。
    """
    if len(value) <= head + tail:
        return "*" * len(value)
    if tail == 0:
        return value[:head] + "*" * (len(value) - head)
    return value[:head] + "*" * (len(value) - head - tail) + value[-tail:]


def _mask_email(value: str) -> str:
    """邮箱脱敏：保留域名，用户名仅保留首字符。

    Parameters
    ----------
    value : str
        原始邮箱地址。

    Returns
    -------
    str
        脱敏后的邮箱，如 ``user@example.com`` -> ``u***@example.com``。
    """
    local, sep, domain = value.partition("@")
    if not sep or not domain:
        return _mask(value, 1, 1)
    return local[:1] + "*" * max(len(local) - 1, 3) + "@" + domain


def _mask_value(kind: str, value: str) -> str:
    """按敏感信息类型选择脱敏策略。

    Parameters
    ----------
    kind : str
        内部子类型（key / id_card / bank_card / phone / address /
        email / ip / plate / credit_code）。
    value : str
        命中的原始值。

    Returns
    -------
    str
        脱敏后的值。
    """
    if kind == "phone":
        return _mask(value, 3, 4)      # 138****5678
    if kind == "id_card":
        return _mask(value, 6, 4)      # 110101********1234
    if kind == "bank_card":
        return _mask(value, 6, 4)      # 622202******5678
    if kind == "address":
        return _mask(value, 3, 0)      # 保留省市前缀
    if kind == "email":
        return _mask_email(value)
    if kind in ("key", "credit_code"):
        return _mask(value, 4, 4)
    return _mask(value, 1, 1)          # ip / plate / 兜底


def _overlaps(start: int, end: int, occupied: List[Tuple[int, int]]) -> bool:
    """判断区间 [start, end) 是否与任一已占用区间重叠。

    Parameters
    ----------
    start : int
        候选区间起点。
    end : int
        候选区间终点。
    occupied : List[Tuple[int, int]]
        已占用区间列表。

    Returns
    -------
    bool
        存在重叠返回 True。
    """
    for os_, oe in occupied:
        if start < oe and os_ < end:
            return True
    return False


def _risk_level(types: Sequence[str]) -> str:
    """根据命中的类型列表计算整体风险等级。

    Parameters
    ----------
    types : Sequence[str]
        命中条目的 type 列表。

    Returns
    -------
    str
        ``low`` / ``medium`` / ``high`` 之一。
    """
    weight = max((_RISK_WEIGHT.get(t, 1) for t in types), default=0)
    if weight >= 3:
        return "high"
    if weight == 2:
        return "medium"
    return "low"


class PrivacyShield(BaseSkill):
    """隐私盾：检测文本中的敏感信息并给出脱敏建议。

    支持检测：手机号/固话（phone）、身份证号（id_card）、银行卡号（bank_card）、
    中文地址（address）、密钥凭证（key）、邮箱/IP/车牌/统一社会信用代码（other）。

    使用示例::

        skill = PrivacyShield()
        result = skill.execute(
            text="我的手机号是13812345678，身份证110101199003078816。"
        )
        # result["masked_text"] 已脱敏；result["risk_level"] == "high"
    """

    name: str = "privacy_shield"
    version: str = "1.0.0"
    schema: Dict[str, Any] = _PRIVACY_SHIELD_SCHEMA

    def execute(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """执行隐私检测与脱敏。

        Parameters
        ----------
        text : str
            待检测的原始文本（必须为字符串）。

        Returns
        -------
        Dict[str, Any]
            形如 ``{"detected": [...], "masked_text": "...", "risk_level": "..."}``
            的检测结果。``detected`` 中每项为
            ``{"type", "value_masked", "position": [start, end]}``。

        Raises
        ------
        TypeError
            当 ``text`` 不是字符串时抛出。
        ValueError
            当文本处理过程中出现异常（如正则执行失败）时抛出。
        """
        if not isinstance(text, str):
            raise TypeError(
                f"PrivacyShield.execute 期望 str 类型 text，实际为 {type(text).__name__}"
            )

        # 空文本快速返回，避免无意义扫描。
        if not text:
            return {"detected": [], "masked_text": "", "risk_level": "low"}

        try:
            occupied: List[Tuple[int, int]] = []
            detected: List[Dict[str, Any]] = []

            for pattern, pii_type, kind in _PATTERNS:
                for match in pattern.finditer(text):
                    start, end = match.span()
                    if _overlaps(start, end, occupied):
                        continue
                    raw = match.group(0)
                    occupied.append((start, end))
                    detected.append(
                        {
                            "type": pii_type,
                            "value_masked": _mask_value(kind, raw),
                            "position": [start, end],
                        }
                    )
        except re.error as exc:  # pragma: no cover - 防御性兜底
            raise ValueError(f"PrivacyShield 正则执行失败: {exc}") from exc

        # 从后往前替换，保证原始坐标不受前序替换影响。
        masked_chars: List[str] = list(text)
        for det in sorted(detected, key=lambda d: d["position"], reverse=True):
            start, end = det["position"]
            masked_chars[start:end] = det["value_masked"]

        return {
            "detected": detected,
            "masked_text": "".join(masked_chars),
            "risk_level": _risk_level([d["type"] for d in detected]),
        }
