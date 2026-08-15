# @agent: session-260809-tidy-tide | module: sb-api | ts: 2026-08-09T12:45+08:00
"""
sb_api.engine — SBEngine 高层 API（stub 级，Wave 1）

封装 agent 层要用的核心操作，统一返回 envelope 结构：

    {"status": "ok" | "pending" | "error", "data": ..., "component": ..., "note"?: ...}

    status:
        ok      — 已产生有效结果（如 search 的空检索结构）
        pending — 接口就绪，真实模型调用逻辑待 Wave 2 补全（见各方法 TODO）
        error   — 模型加载失败或调用异常（data.error 为错误信息）

实现级别说明（Wave 1 = stub）：
    - 全部 8 个方法签名 + 文档字符串完整，惰性加载框架就位
    - search() 最小可跑：返回空检索结构（不 mock 假数据、不加载模型）
    - 其余方法返回 status="pending" 的空结构 + note 标注 Wave 2 补全点
      （stub 方法不触发模型加载、不触发推理，全部 8 个方法零模型依赖）
    - 真实模型调用逻辑以 TODO(G2/Wave2) 注释标注，Wave 2 各 Agent 补全

组件映射：
    decompose      → core（调度总指挥）
    dispatch       → core（调度 MEMO 组件）
    search         → navigator（记忆检索）
    cipher_analyze → cipher（加密/隐私分析）
    policy_check   → broker（策略校验）
    fuse           → core（结果融合）
"""

from __future__ import annotations

from typing import Any, TypedDict

from . import loader
from .loader import ModelLoadError, SBAPIError


class SubTask(TypedDict):
    """子任务结构（对齐 F:\\SelfBrain\\src\\core.py 的 SubTask 契约）。

    字段说明：
        id: 子任务编号（1 起）。
        description: 子任务描述。
        agent: 负责的 Agent，"broker" | "navigator" | "cipher" | "core"。
        dependencies: 依赖的子任务 id 列表（可为空）。
    """

    id: int
    description: str
    agent: str  # "broker" | "navigator" | "cipher" | "core"
    dependencies: list[int]


__all__ = ["SBEngine", "SubTask"]


class SBEngine:
    """SelfBrain 引擎高层 API。

    对主项目引擎组件（core / navigator / cipher / broker）的统一访问入口，
    封装模型惰性加载、显存管理和结果 envelope 结构。

    Args:
        config: 可选配置字典。当前支持的键：
            - max_new_tokens: int，生成最大 token 数（默认 800）
            - temperature: float，采样温度（默认 0.3）
            - lazy: bool，是否惰性加载（默认 True，加载延后到首次调用）
            其余键原样保存，供 Wave 2 各 Agent 使用。
    """

    def __init__(self, config: dict | None = None) -> None:
        """初始化 SBEngine，登记组件状态。

        Args:
            config: 可选配置字典（见类文档字符串）。
        """
        cfg = dict(config or {})
        self.config: dict[str, Any] = {
            "max_new_tokens": 800,
            "temperature": 0.3,
            "lazy": True,
            **cfg,  # 用户配置覆盖默认值
        }
        # 组件状态登记（所有组件初始为未加载）
        self._models: dict[str, Any] = {}  # name -> model
        self._tokenizers: dict[str, Any] = {}  # name -> tokenizer
        self._loaded: dict[str, bool] = {
            name: False for name in ("core", "navigator", "cipher", "broker")
        }

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _ensure_loaded(self, name: str) -> tuple[Any, Any]:
        """惰性加载指定组件模型（实例级缓存，幂等）。

        委托 loader.load_component(name)，首次调用时注入路径并加载模型，
        之后复用实例内缓存。模型加载失败时抛出 ModelLoadError/SBAPIError。

        Args:
            name: 组件名，∈ {"core", "navigator", "cipher", "broker"}。

        Returns:
            (model, tokenizer) 二元组。

        Raises:
            ModelLoadError: 模型加载失败时抛出。
            SBAPIError: 路径缺失或组件名未知时抛出。
        """
        if self._loaded.get(name):
            return self._models[name], self._tokenizers[name]
        model, tokenizer = loader.load_component(name)
        self._models[name] = model
        self._tokenizers[name] = tokenizer
        self._loaded[name] = True
        return model, tokenizer

    def _envelope(
        self,
        status: str,
        data: Any,
        component: str,
        note: str | None = None,
    ) -> dict:
        """构建统一返回 envelope。

        Args:
            status: "ok" | "pending" | "error"。
            data: 业务数据载荷。
            component: 关联组件名。
            note: 可选说明（如 Wave 2 补全点）。

        Returns:
            {"status", "data", "component", "note"?}。
        """
        env: dict[str, Any] = {
            "status": status,
            "data": data,
            "component": component,
        }
        if note is not None:
            env["note"] = note
        return env

    def _error(self, exc: Exception, component: str) -> dict:
        """构建 error envelope。

        Args:
            exc: 捕获的异常。
            component: 关联组件名。

        Returns:
            {"status": "error", "data": {"error": str(exc)}, "component"}。
        """
        return self._envelope(
            "error",
            {"error": str(exc)},
            component,
        )

    # ------------------------------------------------------------------
    # 核心操作（8 个公开方法）
    # ------------------------------------------------------------------

    def decompose(self, query: str) -> dict:
        """将用户查询拆解为子任务列表（调用 core 模型）。

        Args:
            query: 用户原始查询。

        Returns:
            统一 envelope：
                data: list[SubTask]（空列表表示 Wave 2 待补全）
                    每个子任务: {"id", "description", "agent", "dependencies"}。

        TODO(G2/Wave2):
            调用 self._ensure_loaded("core") 后的模型 generate，
            提示词模板与解析逻辑参照 F:\\SelfBrain\\src\\core.py 的
            SYSTEM_DECOMPOSE / _parse_subtasks。
            本 Wave（stub）不加载模型、不触发推理，仅返回空结构。
        """
        return self._envelope(
            "pending",
            [],  # 空 list[SubTask]：不 mock 假数据
            "core",
            note="Wave 2 补全：Core 模型拆解（参照 core.py:decompose）",
        )

    def dispatch(self, subtasks: list) -> dict:
        """子任务分发（调用 core 模型 + MEMO 组件）。

        Args:
            subtasks: decompose() 返回的子任务列表
                （元素为 SubTask: {"id", "description", "agent", "dependencies"}）。

        Returns:
            统一 envelope：
                data: dict[str, str]（{子任务描述: 执行结果}，
                    参照 core.py:dispatch 契约；本 Wave 为空 dict）。

        TODO(G2/Wave2):
            按子任务 agent 分发：MEMO 组件走 memo.run_component(name, task)，
            core 子任务走 Core.generate。参照 F:\\SelfBrain\\src\\core.py:dispatch。
            本 Wave（stub）不加载模型、不触发推理，仅返回空结构。
        """
        return self._envelope(
            "pending",
            {},  # 空 {描述: 结果}：不 mock 假数据
            "core",
            note="Wave 2 补全：子任务分发（参照 core.py:dispatch / memo.run_component）",
        )

    def search(self, query: str) -> dict:
        """记忆检索：语义查询 → 数据位置映射（调用 navigator 模型）。

        Wave 1 最小可跑：返回空检索结构（不加载模型、不 mock 假数据），
        供上层链路先打通；Wave 2 由 G4-navigator 补全真实检索。

        Args:
            query: 用户查询文本。

        Returns:
            统一 envelope：
                data: {
                    "query": str,             # 原查询
                    "results": list[dict],    # 检索命中的记忆条目
                    "memory_paths": list[str] # 定位到的数据位置路径
                }

        TODO(G2/Wave2):
            调用 navigator 模型（self._ensure_loaded("navigator")）实现
            语义查询 → 数据位置映射。
        """
        return self._envelope(
            "ok",
            {
                "query": query,
                "results": [],
                "memory_paths": [],
                "provider": "sb_api.stub",
            },
            "navigator",
        )

    def cipher_analyze(self, text: str) -> dict:
        """加密/隐私分析：动态密码生成与解密（调用 cipher 模型）。

        Args:
            text: 待分析的文本。

        Returns:
            统一 envelope：
                data: {
                    "input_length": int,          # 输入文本长度
                    "cipher_result": str | None,  # 加密/解密结果
                    "action": str | None          # "encrypt" | "decrypt" | None
                }

        TODO(G2/Wave2):
            调用 cipher 模型（self._ensure_loaded("cipher")）实现
            动态密码生成与解密。
        """
        return self._envelope(
            "pending",
            {
                "input_length": len(text),
                "cipher_result": None,
                "action": None,
            },
            "cipher",
            note="Wave 2 补全：Cipher 模型加密/隐私分析",
        )

    def policy_check(self, text: str) -> dict:
        """策略校验（调用 broker 模型）。

        Args:
            text: 待校验的文本（如对外发布的输出）。

        Returns:
            统一 envelope：
                data: {
                    "policy": str,            # 命中的策略/规则
                    "allowed": bool | None,   # 是否允许（None = 待 Wave 2 判定）
                    "reason": str             # 判定理由
                }

        TODO(G2/Wave2):
            调用 broker 模型（self._ensure_loaded("broker")）实现策略校验。
        """
        return self._envelope(
            "pending",
            {
                "policy": "",
                "allowed": None,
                "reason": "Wave 2 补全：Broker 模型策略校验",
            },
            "broker",
            note="Wave 2 补全：Broker 策略校验",
        )

    def fuse(self, parts: list[dict]) -> dict:
        """结果融合：合并多源结果为统一方案（调用 core 模型）。

        Args:
            parts: 待融合的部分列表，每个元素为统一 envelope
                （含 "component"/"data" 字段）或原始 {source, content} 结构。

        Returns:
            统一 envelope：
                data: str（融合后的最终方案文本，本 Wave 为空字符串）。

        TODO(G2/Wave2):
            调用 core 模型（self._ensure_loaded("core")）执行融合，
            提示词模板参照 F:\\SelfBrain\\src\\core.py 的 SYSTEM_FUSE。
            本 Wave（stub）不加载模型、不触发推理，仅返回空结构。
        """
        return self._envelope(
            "pending",
            "",
            "core",
            note="Wave 2 补全：Core 模型结果融合（参照 core.py:fuse）",
        )

    def unload_all(self) -> dict:
        """释放全部已加载组件模型（显存回收）。

        Returns:
            统一 envelope：
                data: {
                    "released": list[str],   # 已释放的组件名
                    "remaining": list[str]   # 仍持有引用的组件名（应为空）
                }
        """
        released: list[str] = []
        for name in [n for n, loaded in self._loaded.items() if loaded]:
            model = self._models.get(name)
            loader.unload_component(model)
            self._models.pop(name, None)
            self._tokenizers.pop(name, None)
            self._loaded[name] = False
            released.append(name)

        remaining = [n for n, loaded in self._loaded.items() if loaded]
        return self._envelope(
            "ok",
            {"released": released, "remaining": remaining},
            "all",
        )
