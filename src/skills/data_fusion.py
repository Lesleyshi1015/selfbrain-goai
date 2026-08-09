# @agent: session-260809-tidy-willow | module: skills/data_fusion | ts: 2026-08-09T12:53+08:00
"""
数据融合 Skill —— DataFusion

将多来源/多结果数据合并去重、打分排序，输出统一结构，供 Coordinator 调度使用。

输入（input.items）:
    每个 item 形如 {"source": str, "content": str, "score": number}

处理流程:
    1. 输入校验（JSON Schema + 逐元素校验）
    2. 内容相似度去重：归一化文本后计算文本相似度，
       相似度 >= threshold 视为同一信息簇，簇内保留最高分条目并标记 merged=True
    3. 打分排序：按 score 降序排列，top 截取前 top_n 条

输出:
    {
        "fused":  [{"source", "content", "score", "merged": bool}],  # 去重后全部条目
        "deduped": int,          # 被合并去除的条目数
        "top":    [...]          # 按分数排序后的前 top_n 条（含全部字段）
    }

用法示例:
    skill = DataFusion()
    result = skill.execute({"items": [
        {"source": "web",   "content": "GOAI 初赛 8 月 16 日提交", "score": 0.9},
        {"source": "doc",   "content": "GOAI 初赛 8 月 16 日提交", "score": 0.7},
    ], "threshold": 0.8, "top_n": 5})
    # -> {"fused": [{"source": "web", "content": "GOAI 初赛 8 月 16 日提交",
    #                "score": 0.9, "merged": True}], "deduped": 1, "top": [...]}
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List

from agent_teams_sdk.skills.base_skill import BaseSkill

# 默认相似度阈值：归一化后文本相似度 >= 0.8 视为重复
DEFAULT_THRESHOLD: float = 0.8
# 默认返回 top 条数
DEFAULT_TOP_N: int = 5


class DataFusion(BaseSkill):
    """
    数据融合 Skill

    将来自多个来源（搜索引擎、文档、内部 Agent 结果等）的文本结果
    合并去重、打分排序，输出统一、可被下游直接消费的结构。
    """

    name: str = "data_fusion"
    version: str = "1.0.0"
    description: str = (
        "数据融合：将多来源/多结果数据合并去重、打分排序，输出统一结构。"
    )

    schema: Dict[str, Any] = {
        "input": {
            "type": "object",
            "required": ["items"],
            "properties": {
                "items": {
                    "type": "array",
                    "description": "待融合的条目列表",
                    "items": {
                        "type": "object",
                        "required": ["source", "content", "score"],
                        "properties": {
                            "source": {"type": "string", "description": "数据来源标识"},
                            "content": {"type": "string", "description": "文本内容"},
                            "score": {
                                "type": "number",
                                "description": "该条目的打分（0-1，越大越可信）",
                            },
                        },
                    },
                },
                "threshold": {
                    "type": "number",
                    "description": f"内容相似度去重阈值（默认 {DEFAULT_THRESHOLD}）",
                },
                "top_n": {
                    "type": "number",
                    "description": f"返回的 top 条数（默认 {DEFAULT_TOP_N}，<=0 表示全部）",
                },
            },
        }
    }

    @property
    def input_schema(self) -> Dict[str, Any]:
        """输入 Schema（任务约定的 input_schema 字段，指向 schema.input）"""
        return self.schema["input"]

    # ------------------------------------------------------------------ #
    # 公共接口
    # ------------------------------------------------------------------ #

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行数据融合。

        Args:
            input: 结构化输入，须包含 "items"（条目数组），可选的
                   "threshold"（去重阈值）与 "top_n"（返回条数）。

        Returns:
            {
                "fused":  去重后全部条目（含 merged 标记），按分数降序
                "deduped": 被合并去除的重复条目数
                "top":    分数最高的前 top_n 条
            }

        Raises:
            ValueError: 输入缺少 items / items 非数组 / 元素结构不合法
            TypeError:  items 中 score 非数字
        """
        # 1. Schema 校验：基类 validate_input 检查 schema.input.required 字段
        #    （以扁平 kwargs 展开，使基类校验对 input 包裹结构生效）
        if not isinstance(input, dict):
            raise ValueError(f"input 必须是 dict，实际为 {type(input).__name__}")
        if not all(isinstance(k, str) for k in input):
            raise ValueError("input 的所有键必须是字符串")
        self.validate_input(**input)

        # 2. 解析参数
        items = input.get("items")
        if not isinstance(items, list):
            raise ValueError(f"input['items'] 必须是数组，实际为 {type(items).__name__}")
        threshold = float(input.get("threshold", DEFAULT_THRESHOLD))
        top_n = int(input.get("top_n", DEFAULT_TOP_N))
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold 必须在 [0, 1] 区间内，实际为 {threshold}")

        # 3. 逐元素校验 + 归一化
        records: List[Dict[str, Any]] = []
        for idx, item in enumerate(items):
            records.append(self._validate_item(item, idx))

        # 4. 相似度去重：贪心聚类，簇内保留最高分
        fused: List[Dict[str, Any]] = []
        for record in sorted(records, key=lambda r: r["score"], reverse=True):
            placed = False
            for kept in fused:
                if self._similarity(record["_norm"], kept["_norm"]) >= threshold:
                    # 已有更高分条目覆盖同一信息 → 标记为合并，不单独保留
                    kept["merged"] = True
                    record["_merged"] = True
                    placed = True
                    break
            if not placed:
                record["merged"] = False
                fused.append(record)

        # 5. 输出整理：排序 + 去重统计 + top 截取
        deduped = len(records) - len(fused)
        fused_out: List[Dict[str, Any]] = [
            {
                "source": r["source"],
                "content": r["content"],
                "score": r["score"],
                "merged": r["merged"],
            }
            for r in sorted(fused, key=lambda r: r["score"], reverse=True)
        ]
        top = (
            fused_out
            if top_n <= 0
            else fused_out[: min(top_n, len(fused_out))]
        )

        return {"fused": fused_out, "deduped": deduped, "top": top}

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #

    def _validate_item(self, item: Any, idx: int) -> Dict[str, Any]:
        """
        校验并归一化单个条目。

        Raises:
            ValueError: 元素非 dict / 缺 source / 缺 content / score 不可转浮点
        """
        if not isinstance(item, dict):
            raise ValueError(f"items[{idx}] 必须是对象，实际为 {type(item).__name__}")
        source = item.get("source")
        content = item.get("content")
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"items[{idx}] 缺少非空 source 字段")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"items[{idx}] 缺少非空 content 字段")
        try:
            score = float(item.get("score", 0.0))
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"items[{idx}] 的 score 必须是数字，实际为 {item.get('score')!r}"
            ) from exc
        score = max(0.0, min(score, 1.0))  # 钳制到 [0, 1]
        return {
            "source": source,
            "content": content,
            "score": score,
            "merged": False,
            "_merged": False,
            "_norm": self._normalize(content),
        }

    @staticmethod
    def _normalize(text: str) -> str:
        """
        文本归一化：转小写、标点/空白替换后输出紧凑串（去所有空白）。

        去除空白使"8 月 16 日"与"8月16日"、"agent-teams-sdk"与
        "agent teams sdk"归一化为同一形式；汉字属于 \\w 字符集，分词不受影响。
        """
        text = text.lower()
        text = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE)
        return re.sub(r"\s+", "", text)

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """
        计算两条归一化文本的相似度（0.0 - 1.0）。

        策略：
        1. 完全相同或互为子串（包含关系）→ 1.0，视为重复；
        2. 否则基于 difflib.SequenceMatcher 字符级匹配比率
           ratio = 2 * M / (len(a) + len(b))，对短文本（<50 字符）
           额外叠加 bigram Jaccard 取加权平均，提升鲁棒性。

        空输入视为完全不相似（返回 0.0），避免除以零。
        """
        if not a or not b:
            return 0.0
        if a == b or a in b or b in a:
            return 1.0
        ratio = SequenceMatcher(None, a, b).ratio()
        if len(a) < 50 or len(b) < 50:
            return 0.5 * ratio + 0.5 * DataFusion._jaccard(a, b)
        return ratio

    @staticmethod
    def _jaccard(a: str, b: str) -> float:
        """字符 bigram 集合的 Jaccard 相似度。"""
        bigrams = lambda s: {s[i : i + 2] for i in range(len(s) - 1)}
        sa, sb = bigrams(a), bigrams(b)
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)
