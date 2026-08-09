# @agent: session-260809-tidy-tide | module: sb-api | ts: 2026-08-09T12:45+08:00
"""
sb_api — SelfBrain-GOAI 桥接层

SelfBrain 主项目引擎（F:\\SelfBrain\\src，4 个已微调模型：
core / navigator / cipher / broker）的**唯一访问入口**。

包结构：
    loader — 路径注入（sys.path）与模型加载统一入口
            （load_component / 4 个 load 包装 / unload / is_available）
    engine — SBEngine 高层 API（decompose / dispatch / search /
             cipher_analyze / policy_check / fuse / unload_all）

用法：
    from sb_api import SBEngine, create_engine

    engine = create_engine()
    result = engine.search("我的账号密码存在哪？")
    # result == {"status": "ok", "data": {...}, "component": "navigator"}
    engine.unload_all()  # 释放全部模型

版本：0.1.0（Wave 1，stub 级接口）
"""

from __future__ import annotations

from . import loader
from .engine import SBEngine, SubTask
from .loader import ModelLoadError, SBAPIError

__version__ = "0.1.0"

__all__ = [
    "SBEngine",
    "SubTask",
    "loader",
    "SBAPIError",
    "ModelLoadError",
    "create_engine",
    "__version__",
]


def create_engine(**kwargs) -> SBEngine:
    """创建 SBEngine 实例（工厂函数）。

    Args:
        **kwargs: 透传给 SBEngine.__init__ 的参数
            （如 config: dict | None）。

    Returns:
        SBEngine 实例。模型仍为惰性加载，首次调用具体方法时才加载。

    Examples:
        >>> engine = create_engine()                      # 默认配置
        >>> engine = create_engine(config={"lazy": True}) # 自定义配置
    """
    return SBEngine(**kwargs)
