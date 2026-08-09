# @agent: session-260809-grand-sunset | module: tests/test_sb_api | ts: 2026-08-09T13:06+08:00
"""
tests/test_sb_api.py — sb_api 模块测试

覆盖：
    loader — SRC_PATH 解析、ensure_src_path、is_available、未知组件异常、
             load_component 注册表、unload_all
    engine — 8 个方法 envelope 结构、stub 返回值、config 传递、unload_all
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 模块导入（sb_api 在 src/ 下，pytest 已通过 pythonpath 配置）
# ---------------------------------------------------------------------------

from sb_api import SBEngine, create_engine, loader  # noqa: E402
from sb_api.loader import ModelLoadError, SBAPIError  # noqa: E402

# ---------------------------------------------------------------------------
# Loader 测试
# ---------------------------------------------------------------------------


class TestLoaderConstants:
    """loader 模块级常量测试"""

    def test_src_path_is_path_object(self):
        """SRC_PATH 应为 pathlib.Path 实例"""
        assert isinstance(loader.SRC_PATH, Path)

    def test_src_path_default_value(self):
        """默认 SRC_PATH 应指向 F:/SelfBrain/src"""
        assert loader.SRC_PATH == Path("F:/SelfBrain/src").resolve()

    def test_loaders_mapping(self):
        """_LOADERS 应包含 4 个组件映射"""
        assert loader._LOADERS == {
            "core": "load_core",
            "navigator": "load_navigator",
            "cipher": "load_cipher",
            "broker": "load_broker",
        }

    def test_all_exported(self):
        """__all__ 应包含所有公开符号"""
        expected = {
            "SRC_PATH", "SBAPIError", "ModelLoadError",
            "ensure_src_path", "load_component", "unload_component",
            "is_available", "load_core", "load_navigator",
            "load_cipher", "load_broker", "unload",
        }
        assert set(loader.__all__) == expected


class TestSBAPIError:
    """异常类测试"""

    def test_sbapi_error_is_exception(self):
        assert issubclass(SBAPIError, Exception)

    def test_model_load_error_is_sbapi_error(self):
        assert issubclass(ModelLoadError, SBAPIError)

    def test_model_load_error_message(self):
        err = ModelLoadError("加载失败")
        assert str(err) == "加载失败"


class TestEnsureSrcPath:
    """ensure_src_path 测试"""

    def test_src_path_not_exists_raises(self, patch_loader):
        """SRC_PATH 不存在时应抛出 SBAPIError"""
        # patch_loader 已将 SRC_PATH.is_dir 设为 False
        # 重置 _SRC_PATH_READY 以确保重新检查
        with patch.object(loader, "_SRC_PATH_READY", False):
            with pytest.raises(SBAPIError, match="源码目录不存在"):
                loader.ensure_src_path()

    def test_src_path_exists_returns_path(self):
        """SRC_PATH 存在时返回路径"""
        # 使用一个确实存在的目录
        with patch.object(loader, "SRC_PATH", Path("/tmp")), \
             patch.object(loader, "_SRC_PATH_READY", False), \
             patch.object(loader, "sys") as mock_sys:
            mock_sys.path = []
            result = loader.ensure_src_path()
            assert result == Path("/tmp")
            assert loader._SRC_PATH_READY is True

    def test_ensure_src_path_idempotent(self):
        """已就绪后再次调用直接返回"""
        with patch.object(loader, "_SRC_PATH_READY", True):
            result = loader.ensure_src_path()
            assert result == loader.SRC_PATH


class TestIsAvailable:
    """is_available 测试"""

    def test_unknown_component_returns_false(self):
        """未知组件名返回 False"""
        assert loader.is_available("unknown") is False

    def test_src_path_not_exists_returns_false(self):
        """SRC_PATH 不存在返回 False"""
        with patch.object(loader, "SRC_PATH") as mock_path:
            mock_path.is_dir.return_value = False
            assert loader.is_available("core") is False

    def test_model_loader_import_error_returns_false(self):
        """model_loader 导入失败返回 False"""
        with patch.object(loader, "SRC_PATH") as mock_path:
            mock_path.is_dir.return_value = True
            with patch.object(loader, "_get_model_loader") as mock_get:
                mock_get.side_effect = ImportError("no module")
                assert loader.is_available("core") is False

    def test_callable_loader_returns_true(self):
        """loader 可调用时返回 True"""
        with patch.object(loader, "SRC_PATH") as mock_path:
            mock_path.is_dir.return_value = True
            with patch.object(loader, "_get_model_loader") as mock_get:
                mock_ml = MagicMock()
                mock_ml.load_core = MagicMock()
                mock_get.return_value = mock_ml
                assert loader.is_available("core") is True


class TestLoadComponent:
    """load_component 测试"""

    def test_unknown_component_raises(self):
        """未知组件名抛出 SBAPIError"""
        with pytest.raises(SBAPIError, match="未知组件"):
            loader.load_component("unknown")

    def test_load_component_caches(self):
        """同一组件重复调用返回缓存"""
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()

        with patch.object(loader, "_get_model_loader") as mock_get:
            mock_ml = MagicMock()
            mock_ml.load_core.return_value = (mock_model, mock_tokenizer)
            mock_get.return_value = mock_ml

            # 第一次调用
            result1 = loader.load_component("core")
            assert result1 == (mock_model, mock_tokenizer)

            # 第二次调用（应走缓存，不再调用 load_core）
            result2 = loader.load_component("core")
            assert result2 == (mock_model, mock_tokenizer)
            assert mock_ml.load_core.call_count == 1

    def test_load_component_model_load_error(self):
        """模型加载失败时抛出 ModelLoadError"""
        # [转派修复·G2-sbapi] @agent: session-260809-tidy-tide | module: tests | ts: 2026-08-09T13:50+08:00
        # 隔离 _LOADED 注册表：其他测试成功加载会缓存 "core"，命中缓存后本测试不抛错
        with patch.object(loader, "_LOADED", {}), \
             patch.object(loader, "_get_model_loader") as mock_get:
            mock_ml = MagicMock()
            mock_ml.load_core.side_effect = RuntimeError("disk error")
            mock_get.return_value = mock_ml

            with pytest.raises(ModelLoadError, match="加载失败"):
                loader.load_component("core")


class TestUnload:
    """unload 测试"""

    def test_unload_none_returns_early(self):
        """model 为 None 时直接返回"""
        # 不应抛出异常
        loader.unload(None)

    def test_unload_removes_from_loaded(self):
        """unload 应从 _LOADED 中移除引用"""
        mock_model = MagicMock()
        loader._LOADED["test_comp"] = (mock_model, MagicMock())

        with patch.object(loader, "_get_model_loader") as mock_get:
            mock_ml = MagicMock()
            mock_get.return_value = mock_ml
            loader.unload(mock_model)

        assert "test_comp" not in loader._LOADED
        mock_ml.unload.assert_called_once_with(mock_model)

    def test_unload_component_alias(self):
        """unload_component 是 unload 的别名"""
        mock_model = MagicMock()
        with patch.object(loader, "unload") as mock_unload:
            loader.unload_component(mock_model)
            mock_unload.assert_called_once_with(mock_model)


# ---------------------------------------------------------------------------
# Engine 测试
# ---------------------------------------------------------------------------


class TestSBEngineInit:
    """SBEngine 初始化测试"""

    def test_default_config(self):
        """默认配置值"""
        engine = SBEngine()
        assert engine.config["max_new_tokens"] == 800
        assert engine.config["temperature"] == 0.3
        assert engine.config["lazy"] is True

    def test_custom_config(self):
        """自定义配置覆盖默认值"""
        engine = SBEngine(config={"max_new_tokens": 512, "temperature": 0.7})
        assert engine.config["max_new_tokens"] == 512
        assert engine.config["temperature"] == 0.7
        assert engine.config["lazy"] is True  # 未被覆盖

    def test_models_initially_empty(self):
        """初始时 _models / _tokenizers / _loaded 为空/False"""
        engine = SBEngine()
        assert engine._models == {}
        assert engine._tokenizers == {}
        assert engine._loaded == {
            "core": False, "navigator": False,
            "cipher": False, "broker": False,
        }


class TestSBEngineEnvelope:
    """envelope 结构测试"""

    def test_envelope_structure_ok(self):
        engine = SBEngine()
        env = engine._envelope("ok", {"key": "val"}, "core")
        assert env == {
            "status": "ok",
            "data": {"key": "val"},
            "component": "core",
        }

    def test_envelope_with_note(self):
        engine = SBEngine()
        env = engine._envelope("pending", {}, "core", note="Wave 2")
        assert "note" in env
        assert env["note"] == "Wave 2"

    def test_error_envelope(self):
        engine = SBEngine()
        env = engine._error(ValueError("boom"), "cipher")
        assert env["status"] == "error"
        assert env["data"]["error"] == "boom"
        assert env["component"] == "cipher"


class TestSBEngineMethods:
    """8 个公开方法测试"""

    @pytest.fixture
    def engine(self) -> SBEngine:
        return SBEngine()

    def test_decompose_returns_pending(self, engine):
        result = engine.decompose("用户查询")
        assert result["status"] == "pending"
        assert result["data"] == []
        assert result["component"] == "core"
        assert "note" in result

    def test_dispatch_returns_pending(self, engine):
        result = engine.dispatch([{"id": 1, "description": "test"}])
        assert result["status"] == "pending"
        assert result["data"] == {}
        assert result["component"] == "core"

    def test_search_returns_ok(self, engine):
        result = engine.search("我的隐私数据在哪")
        assert result["status"] == "ok"
        assert "query" in result["data"]
        assert "results" in result["data"]
        assert "memory_paths" in result["data"]
        assert result["component"] == "navigator"

    def test_search_preserves_query(self, engine):
        result = engine.search("test query 123")
        assert result["data"]["query"] == "test query 123"

    def test_cipher_analyze_returns_pending(self, engine):
        result = engine.cipher_analyze("hello world")
        assert result["status"] == "pending"
        assert result["data"]["input_length"] == 11  # len("hello world")
        assert result["data"]["cipher_result"] is None
        assert result["component"] == "cipher"

    def test_policy_check_returns_pending(self, engine):
        result = engine.policy_check("some text")
        assert result["status"] == "pending"
        assert result["data"]["allowed"] is None
        assert result["component"] == "broker"

    def test_fuse_returns_pending(self, engine):
        result = engine.fuse([{"component": "nav", "data": {}}])
        assert result["status"] == "pending"
        assert result["data"] == ""
        assert result["component"] == "core"

    def test_unload_all_returns_ok(self, engine):
        result = engine.unload_all()
        assert result["status"] == "ok"
        assert "released" in result["data"]
        assert "remaining" in result["data"]
        assert result["data"]["remaining"] == []


class TestSBEngineEnsureLoaded:
    """_ensure_loaded 惰性加载测试"""

    def test_ensure_loaded_calls_loader(self):
        engine = SBEngine()
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()

        with patch.object(loader, "load_component") as mock_lc:
            mock_lc.return_value = (mock_model, mock_tokenizer)
            model, tokenizer = engine._ensure_loaded("core")

            assert model is mock_model
            assert tokenizer is mock_tokenizer
            mock_lc.assert_called_once_with("core")

    def test_ensure_loaded_caches_instance(self):
        engine = SBEngine()
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()

        with patch.object(loader, "load_component") as mock_lc:
            mock_lc.return_value = (mock_model, mock_tokenizer)

            engine._ensure_loaded("core")
            engine._ensure_loaded("core")  # 第二次

            assert mock_lc.call_count == 1
            assert engine._loaded["core"] is True

    def test_ensure_loaded_propagates_model_load_error(self):
        engine = SBEngine()
        with patch.object(loader, "load_component") as mock_lc:
            mock_lc.side_effect = ModelLoadError("fail")
            with pytest.raises(ModelLoadError):
                engine._ensure_loaded("core")


class TestCreateEngine:
    """create_engine 工厂函数测试"""

    def test_returns_sbengine(self):
        engine = create_engine()
        assert isinstance(engine, SBEngine)

    def test_passes_kwargs(self):
        engine = create_engine(config={"lazy": False})
        assert engine.config["lazy"] is False


class TestSubTask:
    """SubTask TypedDict 测试"""

    def test_subtask_structure(self):
        from sb_api.engine import SubTask
        task: SubTask = {
            "id": 1,
            "description": "test",
            "agent": "navigator",
            "dependencies": [],
        }
        assert task["id"] == 1
        assert task["agent"] in ("broker", "navigator", "cipher", "core")
