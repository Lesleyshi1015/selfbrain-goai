# @agent: session-260809-true-swamp | module: skills/access_control | ts: 2026-08-09T12:55+08:00
"""
skills.access_control — 访问控制 Skill（AccessControl）

基于「角色 × 动作 × 资源」规则表判定数据访问是否允许，供 Policy Enforcer 等
上层组件调用。本模块完全开源，不依赖任何闭源 SDK：规则表内置于本文件，判定
逻辑明确、可审计、可测试。

设计要点：
    1. 继承 agent-teams-sdk 的 BaseSkill，输入/输出均带 JSON Schema；
       jsonschema 可用时执行完整 schema 校验，不可用时降级为手工类型校验。
    2. 内置角色-权限规则表（PERMISSION_MATRIX）：
           admin  — 任意资源 read / write / delete
           owner  — 任意资源 read / write，delete 仅限自有资源
           user   — 公共或自有资源 read，自有资源 write，无 delete
           guest  — 仅公共资源 read，无 write / delete
    3. 判定遵循「默认拒绝（fail-closed）」：未命中任何规则一律返回
       allowed=False，并在 reason 说明原因、在 suggested_actions 给出补救建议。
    4. 可选 context 支持细粒度约束：
           public          (bool)  资源是否公共（guest/user 读权限判定）
           requester_id    (str)   请求者身份（自有资源判定）
           resource_owner  (str)   资源归属者（自有资源判定）
           restricted      (bool)  受限资源（仅 admin 可访问）

返回值契约（execute 的固定返回结构）：
    {
        "allowed": bool,           # 是否允许
        "rule": str,               # 命中的规则标识（NO_MATCH:* 表示未命中）
        "reason": str,             # 判定原因（人读）
        "suggested_actions": [...],# 建议的替代动作 / 补救措施
    }

异常层次：
    AccessControlError             — 技能基异常
    AccessControlValidationError   — 输入校验失败（缺字段 / 类型错误 / 空资源）
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_teams_sdk.skills.base_skill import BaseSkill

try:  # pragma: no cover - 环境分支
    import jsonschema

    _HAS_JSONSCHEMA: bool = True
except ImportError:  # pragma: no cover - 降级路径
    jsonschema = None  # type: ignore[assignment]
    _HAS_JSONSCHEMA = False

# ---------------------------------------------------------------------------
# 异常层次
# ---------------------------------------------------------------------------


class AccessControlError(Exception):
    """access_control 技能基异常。

    所有由本技能抛出的异常均继承自此异常；上层可通过捕获它统一处理。
    """


class AccessControlValidationError(AccessControlError, ValueError):
    """输入校验失败。

    当请求缺少必填字段、字段类型错误、或资源名为空时抛出（fail-closed，
    校验失败绝不返回授权）。
    """


# ---------------------------------------------------------------------------
# 内置角色-权限规则表
# ---------------------------------------------------------------------------

# 角色层次（数值越大权限越高），用于排序与聚合建议
ROLE_HIERARCHY: Dict[str, int] = {
    "guest": 0,
    "user": 1,
    "owner": 2,
    "admin": 3,
}

# 系统支持的全部动作（常量，供 schema 与建议输出共用）
SUPPORTED_ACTIONS: List[str] = ["read", "write", "delete"]

# 权限作用域语义说明（见模块 docstring 第 2 条）：
#   "*"               — 任意资源
#   "public"          — 仅公共资源（context.public == True）
#   "owned"           — 仅自有资源（requester_id == resource_owner）
#   "public_or_owned" — 公共资源或自有资源
#   None              — 该角色无此动作权限（直接拒绝）
PERMISSION_MATRIX: Dict[str, Dict[str, Optional[str]]] = {
    "admin": {"read": "*", "write": "*", "delete": "*"},
    "owner": {"read": "*", "write": "*", "delete": "owned"},
    "user": {"read": "public_or_owned", "write": "owned", "delete": None},
    "guest": {"read": "public", "write": None, "delete": None},
}

# 人类可读的角色说明（用于 reason 输出与文档）
ROLE_DESCRIPTIONS: Dict[str, str] = {
    "admin": "管理员：任意资源读写删",
    "owner": "资源所有者：任意资源读写，仅可删除自有资源",
    "user": "普通用户：读写公共或自有资源，仅可写自有资源",
    "guest": "访客：仅可读公共资源",
}


# ---------------------------------------------------------------------------
# Schema 定义
# ---------------------------------------------------------------------------

# 输入 Schema：role/action/resource 必填，context 可选。
# 注意：role/action 不设 enum 枚举——未知值属于「未命中规则」业务场景，
# 应由 execute 返回 allowed=False + 建议，而不是在 schema 层直接抛错。
_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["role", "action", "resource"],
    "properties": {
        "role": {
            "type": "string",
            "minLength": 1,
            "description": "请求者角色（admin/owner/user/guest，未知角色将默认拒绝）",
        },
        "action": {
            "type": "string",
            "minLength": 1,
            "description": "请求动作（read/write/delete，未知动作将默认拒绝）",
        },
        "resource": {
            "type": "string",
            "minLength": 1,
            "description": "目标资源标识（如 memory/notes、system/config）",
        },
        "context": {
            "type": "object",
            "description": "可选上下文：public/requester_id/resource_owner/restricted 等",
            "properties": {
                "public": {"type": "boolean", "description": "资源是否公共"},
                "requester_id": {"type": "string", "description": "请求者身份标识"},
                "resource_owner": {"type": "string", "description": "资源归属者标识"},
                "restricted": {"type": "boolean", "description": "是否受限资源（仅 admin）"},
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": False,
}

# 输出 Schema：execute 的固定返回结构
_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["allowed", "rule", "reason", "suggested_actions"],
    "properties": {
        "allowed": {"type": "boolean", "description": "是否允许访问"},
        "rule": {"type": "string", "description": "命中的规则标识（NO_MATCH:* 表示未命中）"},
        "reason": {"type": "string", "description": "判定原因（人读）"},
        "suggested_actions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "建议的替代动作 / 补救措施",
        },
    },
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# AccessControl Skill
# ---------------------------------------------------------------------------


class AccessControl(BaseSkill):
    """访问控制 Skill。

    判定 `role` 对 `resource` 执行 `action` 是否被允许。规则表内置于本类
    （PERMISSION_MATRIX），判定默认拒绝（fail-closed），未命中任何规则时
    返回 ``allowed=False`` 并附带 `rule`/`reason`/`suggested_actions` 说明。

    用法（两种调用形态等价）::

        ac = AccessControl()
        # 形态一：传入完整 input 字典
        ac.execute({"role": "guest", "action": "read", "resource": "memory/notes",
                    "context": {"public": True}})
        # 形态二：关键字传参
        ac.execute(role="guest", action="write", resource="memory/notes")

    校验：必填字段缺失 / 类型错误 / 资源名为空时抛出
    :class:`AccessControlValidationError`（fail-closed，不返回授权）。
    """

    name: str = "access_control"
    version: str = "1.0.0"
    description: str = (
        "访问控制：基于角色-权限规则表判定数据访问是否允许，"
        "供 Policy Enforcer 等上层组件调用（fail-closed）。"
    )

    # 供 BaseSkill.validate_input / get_schema 使用的 schema（兼容基类契约）
    input_schema: Dict[str, Any] = _INPUT_SCHEMA
    output_schema: Dict[str, Any] = _OUTPUT_SCHEMA

    def __init__(self) -> None:
        """初始化：设置默认名并挂载 schema 到基类契约。"""
        super().__init__()
        self.schema = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "input": self.input_schema,
            "output": self.output_schema,
        }

    # ------------------------------------------------------------------
    # 公共查询接口（供 Policy / 调试使用）
    # ------------------------------------------------------------------

    @classmethod
    def list_roles(cls) -> List[str]:
        """返回规则表中定义的全部角色（按权限从低到高）。"""
        return sorted(ROLE_HIERARCHY, key=ROLE_HIERARCHY.get)

    @classmethod
    def list_actions(cls) -> List[str]:
        """返回系统支持的全部动作。"""
        return list(SUPPORTED_ACTIONS)

    @classmethod
    def get_matrix(cls) -> Dict[str, Dict[str, Optional[str]]]:
        """返回当前生效的权限矩阵副本（外部只读）。"""
        return {role: dict(actions) for role, actions in PERMISSION_MATRIX.items()}

    # ------------------------------------------------------------------
    # BaseSkill 接口实现
    # ------------------------------------------------------------------

    def execute(
        self, input: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        """执行访问控制判定。

        Args:
            input: 完整请求字典，须含 role/action/resource，可选 context。
            **kwargs: 关键字形态（role=..., action=..., resource=..., context=...），
                与 input 同时给出时 kwargs 覆盖 input 中的同名键。

        Returns:
            判定结果字典：``{"allowed": bool, "rule": str, "reason": str,
            "suggested_actions": list[str]}``。未命中任何规则时 ``allowed``
            恒为 ``False``（默认拒绝）。

        Raises:
            AccessControlValidationError: 输入校验失败（缺字段 / 类型错误 /
                资源名为空）。
            AccessControlError: 判定过程出现未预期内部错误（fail-closed，
                校验失败绝不返回授权）。
        """
        data: Dict[str, Any] = self._assemble_input(input, kwargs)
        try:
            self.validate_input(**data)  # 基类必填字段检查（schema["input"]["required"]）
        except ValueError as exc:
            # 统一异常契约：基类抛出的裸 ValueError 包装为技能内校验异常
            raise AccessControlValidationError(str(exc)) from exc
        self._validate_types(data)   # jsonschema 或手工类型校验
        try:
            return self._resolve(data)
        except AccessControlError:
            raise
        except Exception as exc:  # fail-closed：内部异常不允许访问
            raise AccessControlError(
                f"访问控制判定内部错误（已默认拒绝）: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    @staticmethod
    def _assemble_input(
        input: Optional[Dict[str, Any]], kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """归一化两种调用形态为单个请求字典。

        - 仅传 input 字典：直接使用。
        - 仅传 kwargs：组装为字典。
        - 两者同传：kwargs 覆盖 input 同名键。

        Raises:
            AccessControlValidationError: input 非字典或两者均为空。
        """
        if input is not None:
            if not isinstance(input, dict):
                raise AccessControlValidationError(
                    f"input 必须为字典，实际为 {type(input).__name__}"
                )
            data: Dict[str, Any] = dict(input)
            data.update(kwargs)  # kwargs 优先
        elif kwargs:
            data = dict(kwargs)
        else:
            raise AccessControlValidationError(
                "缺少请求参数：须提供 role/action/resource"
            )
        return data

    def _validate_types(self, data: Dict[str, Any]) -> None:
        """执行输入校验（jsonschema 优先，缺失时手工校验）。

        Raises:
            AccessControlValidationError: 任一项校验不通过。
        """
        if _HAS_JSONSCHEMA:
            try:
                jsonschema.validate(instance=data, schema=self.input_schema)
                return
            except jsonschema.ValidationError as exc:
                raise AccessControlValidationError(f"输入校验失败: {exc.message}") from exc
        # 降级：手工类型校验（覆盖必填、类型、非空）
        for field in ("role", "action", "resource"):
            value = data.get(field)
            if not isinstance(value, str):
                raise AccessControlValidationError(
                    f"字段 '{field}' 必须为字符串，实际为 {type(value).__name__}"
                )
            if not value.strip():
                raise AccessControlValidationError(f"字段 '{field}' 不能为空")
        context = data.get("context")
        if context is not None and not isinstance(context, dict):
            raise AccessControlValidationError(
                f"字段 'context' 必须为字典，实际为 {type(context).__name__}"
            )

    def _resolve(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """核心判定：角色/动作归一化 → 逐条匹配规则 → 返回结果（默认拒绝）。"""
        role: str = str(data.get("role") or "").strip().lower()
        action: str = str(data.get("action") or "").strip().lower()
        resource: str = str(data.get("resource") or "").strip()
        context: Dict[str, Any] = data.get("context") or {}

        # 1) 未匹配：未知角色
        if role not in PERMISSION_MATRIX:
            return {
                "allowed": False,
                "rule": "NO_MATCH:unknown_role",
                "reason": (
                    f"未知角色 '{role}'；有效角色: {', '.join(self.list_roles())}。"
                    "请使用已分配角色重试，或联系策略管理员。"
                ),
                "suggested_actions": [
                    "request_role_assignment",
                    "contact_policy_admin",
                ],
            }

        # 2) 未匹配：未知动作
        if action not in SUPPORTED_ACTIONS:
            return {
                "allowed": False,
                "rule": "NO_MATCH:unknown_action",
                "reason": (
                    f"未知动作 '{action}'；有效动作: {', '.join(SUPPORTED_ACTIONS)}"
                ),
                "suggested_actions": list(SUPPORTED_ACTIONS),
            }

        # 3) 受限资源：仅 admin（最高优先级的显式拒绝）
        if context.get("restricted") is True and role != "admin":
            return {
                "allowed": False,
                "rule": "RESTRICTED:admin_only",
                "reason": (
                    f"资源 '{resource}' 为受限资源，仅 admin 可访问；"
                    f"当前角色 '{role}' 无权访问。"
                ),
                "suggested_actions": ["request_admin_approval", "read_public_copy"],
            }

        # 4) 查表：该角色对此动作的权限作用域
        scope: Optional[str] = PERMISSION_MATRIX[role].get(action)
        if scope is None:
            permitted = self._permitted_actions(role)
            return {
                "allowed": False,
                "rule": f"NO_MATCH:{role}:{action}",
                "reason": (
                    f"角色 '{role}'（{ROLE_DESCRIPTIONS[role]}）不允许执行 "
                    f"'{action}'。"
                ),
                "suggested_actions": permitted
                or ["request_role_escalation", "contact_policy_admin"],
            }

        # 5) 作用域判定（read/write/delete 的精细化授权）
        allowed, reason = self._match_scope(role, action, resource, scope, context)
        rule = f"MATCH:{role}:{action}:{scope}" if allowed else f"DENY:{role}:{action}:{scope}"
        return {
            "allowed": allowed,
            "rule": rule,
            "reason": reason,
            "suggested_actions": (
                [] if allowed else self._suggest_for_deny(role, action, scope, context)
            ),
        }

    # ------------------------------------------------------------------
    # 规则匹配辅助
    # ------------------------------------------------------------------

    @classmethod
    def _permitted_actions(cls, role: str) -> List[str]:
        """返回指定角色被允许的全部动作（按系统顺序）。"""
        return [a for a in SUPPORTED_ACTIONS if PERMISSION_MATRIX[role].get(a)]

    @staticmethod
    def _identity(context: Dict[str, Any]) -> str:
        """从上下文中解析请求者身份（兼容 requester_id / owner_id 别名）。"""
        return str(
            context.get("requester_id") or context.get("owner_id") or ""
        ).strip()

    def _match_scope(
        self,
        role: str,
        action: str,
        resource: str,
        scope: str,
        context: Dict[str, Any],
    ) -> tuple[bool, str]:
        """按权限作用域（scope）判定是否授权，返回 (allowed, reason)。

        作用域语义见 PERMISSION_MATRIX 注释；owner 判定采用
        requester_id == resource_owner，缺失身份时视为非自有（fail-closed）。
        """
        requester_id: str = self._identity(context)
        resource_owner: str = str(context.get("resource_owner") or "").strip()
        is_public: bool = context.get("public") is True
        is_owner: bool = bool(requester_id and resource_owner and requester_id == resource_owner)

        if scope == "*":
            return True, (
                f"角色 '{role}' 对资源 '{resource}' 拥有 '{action}' 权限（任意资源）"
            )

        if scope == "public":
            if is_public:
                return True, (
                    f"资源 '{resource}' 为公共资源，角色 '{role}' 允许 '{action}'"
                )
            return False, (
                f"资源 '{resource}' 非公共资源；角色 '{role}' 的 '{action}' 仅限公共资源"
            )

        if scope == "owned":
            if is_owner:
                return True, (
                    f"资源 '{resource}' 归属当前请求者（owner 匹配），允许 '{action}'"
                )
            hint = "；缺少请求者身份（context.requester_id）" if not requester_id else ""
            return False, (
                f"资源 '{resource}' 非请求者自有{hint}；角色 '{role}' 的 "
                f"'{action}' 仅限自有资源"
            )

        if scope == "public_or_owned":
            if is_public or is_owner:
                basis = "公共资源" if is_public else "自有资源（owner 匹配）"
                return True, (
                    f"资源 '{resource}' 为{basis}，角色 '{role}' 允许 '{action}'"
                )
            hint = "；缺少请求者身份（context.requester_id）" if not requester_id else ""
            return False, (
                f"资源 '{resource}' 既非公共也非自有{hint}；角色 '{role}' 的 "
                f"'{action}' 仅限公共或自有资源"
            )

        # 理论不可达（scope 均来自 PERMISSION_MATRIX），fail-closed
        return False, f"未知权限作用域 '{scope}'，已默认拒绝"

    def _suggest_for_deny(
        self, role: str, action: str, scope: str, context: Dict[str, Any]
    ) -> List[str]:
        """为「已知角色但作用域不满足」的拒绝生成补救建议。"""
        suggestions: List[str] = self._permitted_actions(role)
        if scope in ("owned", "public_or_owned") and not self._identity(context):
            suggestions.append("provide_identity:context.requester_id")
        if scope == "owned":
            suggestions.append("request_resource_owner_share")
        if scope == "public":
            suggestions.append("request_owner_make_public")
        if context.get("restricted") is True:
            suggestions.append("request_admin_approval")
        return suggestions
