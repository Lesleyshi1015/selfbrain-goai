# @agent: session-260809-tidy-tide | module: sb-api | ts: 2026-08-09T12:45+08:00
"""
sb_api.loader — SelfBrain 引擎桥接层（路径注入 + 模型加载统一入口）

核心设计：
    sb_api 是 SelfBrain-GOAI 对主项目引擎源码（含模型加载器 model_loader）的
    **唯一访问入口**。本模块通过 sys.path 注入方式加载引擎源码，并集中封装路径
    耦合。引擎源码目录为本地路径示例（不随本仓库分发），实际路径通过环境变量
    SB_SELFBRAIN_SRC 注入。

    引擎源码目录为只读引用（零修改），本模块只做：
        1. ensure_src_path() — 注入并校验源码路径（环境变量 SB_SELFBRAIN_SRC 可覆盖）
        2. 包装 model_loader 的 4 个加载函数 + unload（惰性导入，import 时不加载模型）
        3. 统一入口 load_component / unload_component / is_available

惰性加载约定：
    import sb_api.loader 本身**不**加载任何模型、不 import torch/transformers；
    真正调用 load_component / load_core 等函数时才导入 model_loader 并加载模型。

异常层次：
    SBAPIError      — 桥接层基异常（路径缺失、未知组件、model_loader 导入失败）
    ModelLoadError  — 桥接层模型加载异常（包装 model_loader.ModelLoadError 及底层错误）
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Callable, Tuple

# ---------------------------------------------------------------------------
# 异常定义（桥接层统一异常层次）
# ---------------------------------------------------------------------------


class SBAPIError(Exception):
    """sb_api 桥接层基异常。

    当 SelfBrain 源码路径缺失、组件名未知或 model_loader 无法导入时抛出。
    """

    pass


class ModelLoadError(SBAPIError):
    """sb_api 桥接层模型加载异常。

    包装底层 model_loader.ModelLoadError 及任何模型加载失败，
    向上层（engine / agents）提供统一的异常类型。
    """

    pass


# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------

#: 默认引擎源码目录（本地路径示例，非真实路径，不随本仓库分发）。
#: 生产环境请通过环境变量 SB_SELFBRAIN_SRC 指向实际引擎源码目录。
_DEFAULT_SRC = "<selfbrain-engine-src>"


def _resolve_src_path() -> Path:
    """解析引擎源码目录（可移植，可测试）。

    优先取环境变量 SB_SELFBRAIN_SRC；未设置时回退到占位路径
    （非真实目录，is_dir() 为 False，模块按不可用处理）。

    Returns:
        解析后的引擎源码目录 Path。
    """
    return Path(os.environ.get("SB_SELFBRAIN_SRC", _DEFAULT_SRC)).resolve()


#: SelfBrain 主项目源码目录（只读引用）。默认占位路径，可用环境变量 SB_SELFBRAIN_SRC 覆盖。
SRC_PATH: Path = _resolve_src_path()

#: 组件名 → model_loader 加载函数名
_LOADERS: dict[str, str] = {
    "core": "load_core",
    "navigator": "load_navigator",
    "cipher": "load_cipher",
    "broker": "load_broker",
}

#: 惰性导入的 model_loader 模块（首次调用时填充）
_model_loader: Any = None
#: SRC_PATH 是否已注入 sys.path
_SRC_PATH_READY: bool = False
#: 已加载模型注册表：name -> (model, tokenizer)（避免重复加载占用显存）
_LOADED: dict[str, Tuple[Any, Any]] = {}

__all__ = [
    "SRC_PATH",
    "SBAPIError",
    "ModelLoadError",
    "ensure_src_path",
    "load_component",
    "unload_component",
    "is_available",
    "load_core",
    "load_navigator",
    "load_cipher",
    "load_broker",
    "unload",
]


# ---------------------------------------------------------------------------
# 路径注入与校验
# ---------------------------------------------------------------------------


def ensure_src_path() -> Path:
    """注入并校验 SelfBrain 源码路径（幂等）。

    将 SRC_PATH（默认占位路径，环境变量 SB_SELFBRAIN_SRC 可覆盖）
    插入 sys.path[0]，并校验目录存在。

    Returns:
        校验通过后的 SRC_PATH。

    Raises:
        SBAPIError: 源码目录不存在时抛出（附明确提示）。
    """
    global _SRC_PATH_READY
    if _SRC_PATH_READY:
        return SRC_PATH
    if not SRC_PATH.is_dir():
        raise SBAPIError(
            f"SelfBrain 源码目录不存在: {SRC_PATH}\n"
            f"请设置环境变量 SB_SELFBRAIN_SRC 指向实际引擎源码目录。"
        )
    sp = str(SRC_PATH)
    if sp not in sys.path:
        sys.path.insert(0, sp)
    _SRC_PATH_READY = True
    return SRC_PATH


def _get_model_loader() -> Any:
    """惰性导入 model_loader 模块（首次调用时注入路径并导入）。

    Returns:
        model_loader 模块对象（模块级缓存）。

    Raises:
        SBAPIError: 路径缺失或 model_loader 导入失败时抛出。
    """
    global _model_loader
    if _model_loader is None:
        ensure_src_path()
        try:
            import model_loader as ml
        except ImportError as exc:
            raise SBAPIError(
                f"无法导入 model_loader（SRC_PATH={SRC_PATH}）。"
                f"请确认 SRC_PATH/model_loader.py 存在且依赖已安装: {exc}"
            ) from exc
        _model_loader = ml
    return _model_loader


# ---------------------------------------------------------------------------
# 统一加载入口
# ---------------------------------------------------------------------------


def load_component(name: str) -> Tuple[Any, Any]:
    """统一加载入口：按名称加载组件模型（惰性 + 注册表缓存）。

    支持的组件名（name ∈ {core, navigator, cipher, broker}）：
        core       — 蜂群调度总指挥（合并模型，4bit）
        navigator  — 记忆导航（语义查询 → 数据位置映射）
        cipher     — 加密/隐私分析（动态密码生成与解密）
        broker     — 数据提取/加密/外部通信（策略校验）

    同一组件重复调用返回缓存的 (model, tokenizer)，不会重复加载占显存；
    调用 unload_component(model) 后再次调用会重新加载。

    Args:
        name: 组件名，∈ {"core", "navigator", "cipher", "broker"}。

    Returns:
        (model, tokenizer) 二元组。

    Raises:
        SBAPIError: 组件名未知。
        ModelLoadError: 模型加载失败（路径缺失/文件损坏等）。
    """
    if name not in _LOADERS:
        raise SBAPIError(f"未知组件: {name!r}，可选: {sorted(_LOADERS)}")
    if name in _LOADED:
        return _LOADED[name]

    loader_fn: Callable[[], Tuple[Any, Any]] = getattr(
        _get_model_loader(), _LOADERS[name]
    )
    try:
        model, tokenizer = loader_fn()
    except Exception as exc:
        # 包装底层异常（含 model_loader.ModelLoadError），统一为桥接层异常
        raise ModelLoadError(f"[sb_api] 组件 {name!r} 加载失败: {exc}") from exc

    _LOADED[name] = (model, tokenizer)
    return model, tokenizer


def unload(model: Any) -> None:
    """释放模型占用的显存（幂等，桥接封装）。

    委托给 model_loader.unload(model)（完整的 torch.cuda 清理序列），
    同时清理本模块注册表中对该模型的引用。

    注意：调用方持有的其他引用需自行置 None，否则显存不会真正释放。

    Args:
        model: 需要释放的模型对象，可为 None（直接返回）。
    """
    if model is None:
        return

    # 清理注册表中引用该模型的条目
    for name in [n for n, (m, _t) in _LOADED.items() if m is model]:
        del _LOADED[name]

    try:
        loader = _get_model_loader()
    except SBAPIError:
        # 模型加载器不可用（如路径已移除）：已清理注册表，无需进一步操作
        return
    loader.unload(model)


def unload_component(model: Any) -> None:
    """按模型对象释放组件（幂等）。

    Args:
        model: 待释放的组件模型对象（来自 load_component 返回值）。
    """
    unload(model)


def is_available(name: str) -> bool:
    """惰性检查组件是否可用（不加载模型）。

    检查顺序：
        1. 组件名是否合法
        2. SRC_PATH 目录是否存在
        3. model_loader 是否可导入且包含对应加载函数

    注意：本函数可能触发 model_loader 导入（含 torch），但不加载任何模型。

    Args:
        name: 组件名，∈ {"core", "navigator", "cipher", "broker"}。

    Returns:
        True 表示可加载（注意：不代表已加载）；否则 False。
    """
    if name not in _LOADERS:
        return False
    if not SRC_PATH.is_dir():
        return False
    try:
        loader = _get_model_loader()
        return callable(getattr(loader, _LOADERS[name], None))
    except (ImportError, SBAPIError):
        return False


# ---------------------------------------------------------------------------
# 4 个加载函数包装（与 model_loader 同名，供直接调用）
# ---------------------------------------------------------------------------


def load_core() -> Tuple[Any, Any]:
    """加载 Core 模型（桥接封装，等价 load_component("core")）。

    Core 是蜂群调度总指挥（合并模型，4bit），常驻内存，
    调用 unload() 手动释放。

    Returns:
        (model, tokenizer) 二元组。

    Raises:
        ModelLoadError: 模型加载失败时抛出。
    """
    return load_component("core")


def load_navigator() -> Tuple[Any, Any]:
    """加载 Navigator 模型（桥接封装，等价 load_component("navigator")）。

    Navigator 负责语义查询 → 数据位置映射（轻量本地模型，INT4 量化）。

    Returns:
        (model, tokenizer) 二元组。

    Raises:
        ModelLoadError: 模型加载失败时抛出。
    """
    return load_component("navigator")


def load_cipher() -> Tuple[Any, Any]:
    """加载 Cipher 模型（桥接封装，等价 load_component("cipher")）。

    Cipher 负责动态密码生成与解密（轻量本地模型，INT4 量化）。

    Returns:
        (model, tokenizer) 二元组。

    Raises:
        ModelLoadError: 模型加载失败时抛出。
    """
    return load_component("cipher")


def load_broker() -> Tuple[Any, Any]:
    """加载 Broker 模型（桥接封装，等价 load_component("broker")）。

    Broker 负责数据提取、加密和外部通信（轻量本地模型，INT4 量化）。

    Returns:
        (model, tokenizer) 二元组。

    Raises:
        ModelLoadError: 模型加载失败时抛出。
    """
    return load_component("broker")
