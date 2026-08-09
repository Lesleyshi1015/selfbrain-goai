# @agent: session-260809-brave-dawn | module: skills/memory_probe | ts: 2026-08-09T12:53+08:00
"""
skills.memory_probe — MemoryProbe 记忆探测 Skill（规则驱动，零模型依赖）

记忆探测（Memory Probing）：对 Navigator 输入的原始查询做**语义扩展**与**查询拆解**，
提升下游记忆检索（sb_api.SBEngine.search）的召回率：

1. **语义扩展（expanded）** —— 基于同义词词典，把查询中的关键词替换为同义/近义表达，
   生成若干等价查询变体。例如 "怎么找回忘记的密码" → "怎么找回遗忘的密码" / "怎么检索遗忘的密码"。
2. **查询拆解（decomposed）** —— 基于领域关键词与逻辑连接词，把复合查询拆成多个
   原子子查询。例如 "用户的加密记录和删除时间" → ["用户的加密记录", "删除时间"]。

实现说明：
    - **规则/词典驱动**：内置同义词组表 + 领域关键词表 + 连接词表，不调用任何模型，
      无网络请求，可离线运行、毫秒级响应、结果完全可复现。
    - **对 Navigator 的契约**：``execute(input)`` 返回
      ``{"original", "expanded", "decomposed", "note"}`` 四个字段的统一 envelope，
      供 Navigator 将扩展变体/子查询逐一送入记忆检索通道。
    - 输入经 JSON Schema 校验（``schema["input"]``），必填 ``query``（str），
      可选 ``context``（str，领域/场景上下文，辅助拆解）。
"""

from __future__ import annotations

from typing import Any, Dict, List

from agent_teams_sdk.skills.base_skill import BaseSkill

__all__ = ["MemoryProbe"]

# ---------------------------------------------------------------------------
# 词典与规则表（规则驱动的全部"知识"都集中在此，便于维护与扩展）
# ---------------------------------------------------------------------------

# 同义词组：组内各词互为近义表达（先长后短，保证最长匹配优先）。
SYNONYM_GROUPS: List[List[str]] = [
    ["记忆", "回忆", "回想", "记住", "remember", "memory"],
    ["查找", "检索", "搜索", "查询", "搜寻", "search", "retrieve", "find"],
    ["忘记", "遗忘", "记不起", "forget"],
    ["加密", "解密", "密文", "明文", "encrypt", "decrypt"],
    ["隐私", "保密", "私密", "敏感", "privacy", "private"],
    ["删除", "清除", "移除", "销毁", "delete", "remove"],
    ["保存", "备份", "存档", "留存", "save", "backup"],
    ["用户", "人物", "对象", "主体", "user"],
    ["时间", "日期", "时刻", "时段", "time", "date"],
    ["知道", "了解", "认识", "记得", "know"],
    ["记录", "笔记", "日志", "条目", "note", "record"],
    ["密码", "口令", "密钥", "passcode", "password"],
]

# 领域关键词：拆解时用于把查询切分为"主题概念"原子片段。
DOMAIN_KEYWORDS: List[str] = [
    "记忆", "隐私", "加密", "密码", "用户", "时间", "事件", "情绪",
    "记录", "笔记", "日志", "对话", "任务", "计划", "联系人",
    "文件", "图片", "位置", "提醒", "备份",
]

# 逻辑连接词：拆解时用于切分复合查询（按长度降序，避免"与"误吞"以及"）。
SPLIT_CONJUNCTIONS: List[str] = [
    "以及", "还有", "加上", "和", "与", "或", "且",
    "、", "，", ",", "；", ";", "？", "?", " ", "\t", "\n",
]

def _strip_punct(text: str) -> str:
    """去除首尾空白与常见标点，返回规整后的查询片段。"""
    return text.strip(" \t\r\n，。；、？?！!.,;:：\"'“”‘’（）()【】[]")

class MemoryProbe(BaseSkill):
    """记忆探测 Skill：对查询做语义扩展与拆解，提升记忆检索召回率。

    继承 :class:`agent_teams_sdk.skills.base_skill.BaseSkill`，遵循其
    ``name`` / ``schema`` / ``execute(**kwargs)`` / ``validate_input`` 契约。
    输入输出均定义在 :attr:`schema` 中，由 BaseSkill 的 JSON Schema 校验保证。

    典型调用（Navigator）：:

        probe = MemoryProbe()
        result = probe.execute(input={
            "query": "用户的加密记录和删除时间",
            "context": "user_data",
        })
        # result == {
        #   "original": "用户的加密记录和删除时间",
        #   "expanded":  ["用户的加密记录和删除时间", ...同义变体...],
        #   "decomposed": ["用户的加密记录", "删除时间"],
        #   "note": "规则/词典驱动",
        # }
    """

    name: str = "memory_probe"
    version: str = "1.0.0"
    description: str = (
        "记忆探测：对查询做语义扩展（同义词改写）与查询拆解（原子子查询），"
        "提升记忆检索召回率。规则/词典驱动，零模型依赖，毫秒级响应。"
    )

    # 输入输出 Schema（BaseSkill.validate_input 依据 schema["input"]["required"] 校验）
    schema: Dict[str, Any] = {
        "description": description,
        "input": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "原始查询语句（必填）",
                },
                "context": {
                    "type": "string",
                    "description": "可选的领域/场景上下文，辅助拆解与扩展",
                },
            },
            "required": ["query"],
        },
        "output": {
            "type": "object",
            "properties": {
                "original": {"type": "string"},
                "expanded": {"type": "array", "items": {"type": "string"}},
                "decomposed": {"type": "array", "items": {"type": "string"}},
                "note": {"type": "string"},
            },
            "required": ["original", "expanded", "decomposed", "note"],
        },
    }

    # alias：满足部分调用方以 input_schema 属性访问的习惯
    @property
    def input_schema(self) -> Dict[str, Any]:
        """输入 Schema 别名（``schema["input"]``）。"""
        return self.schema["input"]

    # ------------------------------------------------------------------
    # 语义扩展（同义改写）
    # ------------------------------------------------------------------

    def _expand_by_group(self, query: str, group: List[str], query_lower: str) -> List[str]:
        """把查询中命中 ``group`` 的词条替换为该组其他成员，生成同义变体。

        返回去重后的变体列表（不含原查询本身）。
        """
        variants: List[str] = []
        # 找出查询中所有属于该词组的命中词条（按长度降序，先替换长词）
        hits: List[str] = []
        for member in sorted(group, key=len, reverse=True):
            member_lower = member.lower()
            if member_lower in query_lower:
                hits.append(member)
        for hit in hits:
            for replacement in group:
                if replacement.lower() == hit.lower():
                    continue  # 跳过自身
                candidate = query.replace(hit, replacement)
                if candidate != query and candidate not in variants:
                    variants.append(candidate)
        return variants

    def _expand(self, query: str) -> List[str]:
        """生成语义扩展变体列表（同义词替换）。

        策略：对每个命中同义词组的词条，逐一替换为组内其他成员；
        同一查询可命中多个词组，分别生成变体（不强制做多词组合，避免组合爆炸）。
        """
        variants: List[str] = []
        query_lower = query.lower()
        seen_groups: List[List[str]] = []
        for group in SYNONYM_GROUPS:
            if any(member.lower() in query_lower for member in group):
                if group in seen_groups:
                    continue
                seen_groups.append(group)
                variants.extend(self._expand_by_group(query, group, query_lower))
        # 去重保序
        deduped: List[str] = []
        for v in variants:
            if v not in deduped:
                deduped.append(v)
        return deduped

    # ------------------------------------------------------------------
    # 查询拆解
    # ------------------------------------------------------------------

    def _split_by_conjunctions(self, query: str) -> List[str]:
        """按逻辑连接词把复合查询切分为片段列表。"""
        parts = [query]
        for conj in sorted(SPLIT_CONJUNCTIONS, key=len, reverse=True):
            new_parts: List[str] = []
            for part in parts:
                new_parts.extend(part.split(conj))
            parts = new_parts
        cleaned = [_strip_punct(p) for p in parts]
        return [p for p in cleaned if p]

    def _split_by_keywords(self, query: str) -> List[str]:
        """把查询按领域关键词切分为"主题概念"原子片段。

        规则：遍历词典词条（按出现位置升序），在两两关键词之间取片段；
        找不到多个关键词时回退为整个查询。
        """
        query_lower = query.lower()
        positions: List[tuple[int, str]] = []
        for kw in DOMAIN_KEYWORDS:
            start = 0
            while True:
                idx = query_lower.find(kw.lower(), start)
                if idx == -1:
                    break
                positions.append((idx, kw))
                start = idx + 1
        if len(positions) < 2:
            return [query]
        positions.sort()
        segments: List[str] = []
        for i, (pos, kw) in enumerate(positions[:-1]):
            next_pos = positions[i + 1][0]
            seg = _strip_punct(query[pos:next_pos])
            if seg and seg not in segments:
                segments.append(seg)
        last_seg = _strip_punct(query[positions[-1][0]:])
        if last_seg and last_seg not in segments:
            segments.append(last_seg)
        return segments

    def _decompose(self, query: str, context: str | None) -> List[str]:
        """生成拆解后的原子子查询列表。

        策略优先级：
            1. 若命中逻辑连接词 → 按连接词切分；
            2. 否则若命中 >= 2 个领域关键词 → 按关键词切分；
            3. 否则返回整条查询（单原子）。
        有 ``context`` 时，为每个子查询追加一个带上下文前缀的变体（供检索侧加权）。
        """
        parts = self._split_by_conjunctions(query)
        if len(parts) < 2:
            parts = self._split_by_keywords(query)
        result: List[str] = []
        for p in parts:
            if p not in result:
                result.append(p)
        if context:
            for p in list(result):
                prefixed = _strip_punct(f"{context} {p}")
                if prefixed and prefixed not in result:
                    result.append(prefixed)
        return result

    # ------------------------------------------------------------------
    # 对外执行入口
    # ------------------------------------------------------------------

    def execute(self, input: Dict[str, Any] | None = None, **kwargs: Any) -> Dict[str, Any]:
        """执行记忆探测，返回语义扩展与拆解结果。

        兼容两种调用方式：
            - ``execute(input={"query": "...", "context": "..."})``（标准方式）
            - ``execute(query="...", context="...")``（扁平方式）

        Args:
            input: 输入字典，须含 ``query``（str，必填）与可选 ``context``（str）。
            **kwargs: 扁平参数形式下的 ``query`` / ``context``。

        Returns:
            Dict[str, Any]: 统一 envelope ——
                ``{"original", "expanded", "decomposed", "note"}``。

        Raises:
            TypeError: input 非 dict 或类型不合法。
            ValueError: query 缺失、为空或非字符串。
        """
        # 1. 参数归并：扁平 kwargs 优先并入 input
        if input is None:
            input = {}
        if not isinstance(input, dict):
            raise TypeError(f"input 必须是 dict，实际为 {type(input).__name__}")
        if kwargs:
            merged = dict(input)
            merged.update(kwargs)
            input = merged

        # 2. Schema 校验（BaseSkill 契约，缺失 query 时抛 ValueError）
        self.validate_input(**input)

        query = input.get("query")
        context = input.get("context")

        # 3. 类型与内容守卫
        if not isinstance(query, str):
            raise TypeError(f"query 必须是 str，实际为 {type(query).__name__}")
        query = query.strip()
        if not query:
            raise ValueError("query 不能为空")
        if context is not None and not isinstance(context, str):
            raise TypeError(f"context 必须是 str，实际为 {type(context).__name__}")

        # 4. 规则驱动：扩展 + 拆解（纯内存操作，无外部依赖）
        try:
            expanded = self._expand(query)
            decomposed = self._decompose(query, context)
        except Exception as exc:  # 防御性兜底：规则逻辑异常不泄漏到上层
            raise RuntimeError(f"memory_probe 规则引擎执行失败: {exc}") from exc

        # 5. 组装结果 envelope（去重、保序）
        results: List[str] = []
        for item in [query, *expanded, *decomposed]:
            if item not in results:
                results.append(item)

        return {
            "original": query,
            "expanded": [e for e in expanded],
            "decomposed": [d for d in decomposed],
            "note": "规则/词典驱动",
        }
