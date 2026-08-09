# @agent: session-260809-grand-sunset | module: tests/test_skills | ts: 2026-08-09T13:06+08:00
"""
tests/test_skills.py — 6 个 Skill 测试

覆盖：
    PrivacyShield  — PII 检测正反例、脱敏、风险等级
    MemoryProbe    — 语义扩展、查询拆解
    DataFusion     — 去重、打分排序、top_n
    AccessControl  — 角色判定（admin/owner/user/guest）、受限资源、默认拒绝
    AuditTrail     — 格式化、聚合统计、报告生成
    ResultVerify   — 完整性/格式/一致性核查、评分
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from skills.privacy_shield import PrivacyShield  # noqa: E402
from skills.memory_probe import MemoryProbe  # noqa: E402
from skills.data_fusion import DataFusion  # noqa: E402
from skills.access_control import AccessControl, AccessControlValidationError  # noqa: E402
from skills.audit_trail import AuditTrail  # noqa: E402
from skills.result_verify import ResultVerify, verify_result  # noqa: E402

# ---------------------------------------------------------------------------
# PrivacyShield 测试
# ---------------------------------------------------------------------------


class TestPrivacyShield:
    """隐私盾 Skill 测试"""

    @pytest.fixture
    def shield(self):
        return PrivacyShield()

    # ---- 正例：检测到 PII ----

    def test_detect_phone(self, shield):
        result = shield.execute(text="我的手机号是13812345678，请保存。")
        assert len(result["detected"]) >= 1
        phone_hits = [d for d in result["detected"] if d["type"] == "phone"]
        assert len(phone_hits) >= 1
        assert phone_hits[0]["value_masked"] == "138****5678"
        assert phone_hits[0]["position"] == [6, 17]

    def test_detect_id_card(self, shield):
        # 18位身份证：110101199003078816
        result = shield.execute(text="身份证110101199003078816")
        id_hits = [d for d in result["detected"] if d["type"] == "id_card"]
        assert len(id_hits) >= 1
        assert id_hits[0]["value_masked"] == "110101********8816"

    def test_detect_bank_card(self, shield):
        result = shield.execute(text="银行卡6222021234567890123")
        bank_hits = [d for d in result["detected"] if d["type"] == "bank_card"]
        assert len(bank_hits) >= 1

    def test_detect_email(self, shield):
        result = shield.execute(text="邮箱test@example.com请保存")
        email_hits = [d for d in result["detected"] if d["type"] == "other"]
        assert len(email_hits) >= 1
        assert email_hits[0]["value_masked"].endswith("@example.com")

    def test_detect_api_key(self, shield):
        result = shield.execute(text="AWS Key: AKIAIOSFODNN7EXAMPLE")
        key_hits = [d for d in result["detected"] if d["type"] == "key"]
        assert len(key_hits) >= 1

    # ---- 反例：无 PII ----

    def test_no_pii_clean_text(self, shield):
        result = shield.execute(text="今天天气不错，适合出门。")
        assert result["detected"] == []
        assert result["masked_text"] == "今天天气不错，适合出门。"
        assert result["risk_level"] == "low"

    def test_empty_text(self, shield):
        result = shield.execute(text="")
        assert result["detected"] == []
        assert result["risk_level"] == "low"

    # ---- 风险等级 ----

    def test_risk_level_high_for_key(self, shield):
        result = shield.execute(text="api_key=abcdefghij1234567890")
        assert result["risk_level"] == "high"

    def test_risk_level_medium_for_phone(self, shield):
        result = shield.execute(text="手机13812345678")
        assert result["risk_level"] == "medium"

    # ---- 异常 ----

    def test_non_string_input_raises(self, shield):
        with pytest.raises(TypeError, match="期望 str 类型"):
            shield.execute(text=12345)  # type: ignore

    # ---- masked_text ----

    def test_masked_text_replaces_pii(self, shield):
        result = shield.execute(text="电话13812345678")
        assert "13812345678" not in result["masked_text"]
        assert "138****5678" in result["masked_text"]


# ---------------------------------------------------------------------------
# MemoryProbe 测试
# ---------------------------------------------------------------------------


class TestMemoryProbe:
    """记忆探测 Skill 测试"""

    @pytest.fixture
    def probe(self):
        return MemoryProbe()

    def test_expand_generates_variants(self, probe):
        result = probe.execute(input={"query": "怎么查找记忆"})
        assert result["original"] == "怎么查找记忆"
        assert isinstance(result["expanded"], list)
        assert len(result["expanded"]) > 0
        assert result["note"] == "规则/词典驱动"

    def test_decompose_compound_query(self, probe):
        result = probe.execute(input={
            "query": "用户的加密记录和删除时间",
            "context": "user_data",
        })
        assert isinstance(result["decomposed"], list)
        assert len(result["decomposed"]) >= 2
        # context 前缀变体应存在
        assert any("user_data" in d for d in result["decomposed"])

    def test_decompose_simple_query(self, probe):
        result = probe.execute(input={"query": "单一查询"})
        # 无连接词、少关键词 → 返回原查询
        assert result["decomposed"] == ["单一查询"]

    def test_empty_query_raises(self, probe):
        with pytest.raises(ValueError, match="不能为空"):
            probe.execute(input={"query": ""})

    def test_non_dict_input_raises(self, probe):
        with pytest.raises(TypeError, match="必须是 dict"):
            probe.execute(input="not a dict")  # type: ignore

    def test_kwargs_form(self, probe):
        result = probe.execute(query="test query")
        assert result["original"] == "test query"

    def test_context_none(self, probe):
        result = probe.execute(input={"query": "test", "context": None})
        assert result["original"] == "test"


# ---------------------------------------------------------------------------
# DataFusion 测试
# ---------------------------------------------------------------------------


class TestDataFusion:
    """数据融合 Skill 测试"""

    @pytest.fixture
    def fusion(self):
        return DataFusion()

    def test_dedup_similar_items(self, fusion):
        items = [
            {"source": "web", "content": "GOAI 初赛 8 月 16 日提交", "score": 0.9},
            {"source": "doc", "content": "GOAI 初赛 8 月 16 日提交", "score": 0.7},
        ]
        result = fusion.execute({"items": items, "threshold": 0.8, "top_n": 5})

        assert result["deduped"] == 1
        assert len(result["fused"]) == 1
        assert result["fused"][0]["source"] == "web"  # 高分保留
        assert result["fused"][0]["merged"] is True  # 被合并标记

    def test_no_dedup_different_items(self, fusion):
        # 使用差异足够大的内容（相似度低于阈值）
        items = [
            {"source": "a", "content": "苹果香蕉橘子", "score": 0.9},
            {"source": "b", "content": "汽车飞机轮船", "score": 0.8},
        ]
        result = fusion.execute({"items": items, "threshold": 0.8})

        # 相似度应低于 0.8，不去重
        assert result["deduped"] == 0
        assert len(result["fused"]) == 2

    def test_top_n_truncation(self, fusion):
        items = [
            {"source": f"s{i}", "content": f"内容{i}", "score": 0.1 * (i + 1)}
            for i in range(10)
        ]
        # threshold=0.0 会导致所有项被去重（相似度>0），只保留最高分
        result = fusion.execute({"items": items, "threshold": 0.0, "top_n": 3})

        # 去重后只保留最高分项，top_n 再截取
        assert len(result["top"]) <= 3
        # 按分数降序
        if len(result["top"]) >= 2:
            assert result["top"][0]["score"] >= result["top"][1]["score"]

    def test_top_n_zero_returns_all(self, fusion):
        items = [
            {"source": "a", "content": "x", "score": 0.5},
        ]
        result = fusion.execute({"items": items, "top_n": 0})
        assert len(result["top"]) == 1

    def test_invalid_item_missing_source(self, fusion):
        items = [{"content": "no source", "score": 0.5}]
        with pytest.raises(ValueError, match="source"):
            fusion.execute({"items": items})

    def test_invalid_item_missing_content(self, fusion):
        items = [{"source": "s", "score": 0.5}]
        with pytest.raises(ValueError, match="content"):
            fusion.execute({"items": items})

    def test_invalid_score_type(self, fusion):
        items = [{"source": "s", "content": "c", "score": "not a number"}]
        with pytest.raises(TypeError, match="score"):
            fusion.execute({"items": items})

    def test_score_clamped_to_range(self, fusion):
        items = [{"source": "s", "content": "c", "score": 1.5}]
        result = fusion.execute({"items": items})
        assert result["fused"][0]["score"] == 1.0

    def test_similarity_identical(self, fusion):
        assert fusion._similarity("abc", "abc") == 1.0

    def test_similarity_empty(self, fusion):
        assert fusion._similarity("", "abc") == 0.0

    def test_normalize_removes_spaces(self, fusion):
        assert fusion._normalize("8 月 16 日") == fusion._normalize("8月16日")


# ---------------------------------------------------------------------------
# AccessControl 测试
# ---------------------------------------------------------------------------


class TestAccessControl:
    """访问控制 Skill 测试"""

    @pytest.fixture
    def ac(self):
        return AccessControl()

    # ---- admin ----

    def test_admin_read(self, ac):
        result = ac.execute(role="admin", action="read", resource="anything")
        assert result["allowed"] is True
        assert result["rule"] == "MATCH:admin:read:*"

    def test_admin_delete(self, ac):
        result = ac.execute(role="admin", action="delete", resource="anything")
        assert result["allowed"] is True

    # ---- owner ----

    def test_owner_delete_owned(self, ac):
        result = ac.execute(
            role="owner", action="delete", resource="my_resource",
            context={"requester_id": "user1", "resource_owner": "user1"},
        )
        assert result["allowed"] is True

    def test_owner_delete_not_owned(self, ac):
        result = ac.execute(
            role="owner", action="delete", resource="other_resource",
            context={"requester_id": "user1", "resource_owner": "user2"},
        )
        assert result["allowed"] is False

    # ---- user ----

    def test_user_read_public(self, ac):
        result = ac.execute(
            role="user", action="read", resource="public_doc",
            context={"public": True},
        )
        assert result["allowed"] is True

    def test_user_read_private_not_owned(self, ac):
        result = ac.execute(
            role="user", action="read", resource="private_doc",
            context={"public": False, "requester_id": "u1", "resource_owner": "u2"},
        )
        assert result["allowed"] is False

    def test_user_write_owned(self, ac):
        result = ac.execute(
            role="user", action="write", resource="my_doc",
            context={"requester_id": "u1", "resource_owner": "u1"},
        )
        assert result["allowed"] is True

    def test_user_delete_not_allowed(self, ac):
        result = ac.execute(role="user", action="delete", resource="doc")
        assert result["allowed"] is False
        assert "NO_MATCH" in result["rule"]

    # ---- guest ----

    def test_guest_read_public(self, ac):
        result = ac.execute(
            role="guest", action="read", resource="public",
            context={"public": True},
        )
        assert result["allowed"] is True

    def test_guest_read_private(self, ac):
        result = ac.execute(
            role="guest", action="read", resource="private",
            context={"public": False},
        )
        assert result["allowed"] is False

    def test_guest_write_always_denied(self, ac):
        result = ac.execute(role="guest", action="write", resource="anything")
        assert result["allowed"] is False

    # ---- restricted ----

    def test_restricted_resource_admin_only(self, ac):
        result = ac.execute(
            role="user", action="read", resource="secret",
            context={"restricted": True},
        )
        assert result["allowed"] is False
        assert "RESTRICTED" in result["rule"]

    # ---- unknown ----

    def test_unknown_role(self, ac):
        result = ac.execute(role="superuser", action="read", resource="doc")
        assert result["allowed"] is False
        assert "unknown_role" in result["rule"]

    def test_unknown_action(self, ac):
        result = ac.execute(role="admin", action="execute", resource="doc")
        assert result["allowed"] is False
        assert "unknown_action" in result["rule"]

    # ---- validation ----

    def test_missing_role_raises(self, ac):
        with pytest.raises(AccessControlValidationError):
            ac.execute(action="read", resource="doc")

    def test_empty_resource_raises(self, ac):
        # [转派修复·G2-sbapi] @agent: session-260809-tidy-tide | module: tests | ts: 2026-08-09T13:50+08:00
        # 实际异常消息为 jsonschema 格式: "输入校验失败: '' should be non-empty"
        with pytest.raises(AccessControlValidationError, match="should be non-empty"):
            ac.execute(role="admin", action="read", resource="")

    # ---- class methods ----

    def test_list_roles(self, ac):
        roles = AccessControl.list_roles()
        assert roles == ["guest", "user", "owner", "admin"]

    def test_list_actions(self, ac):
        assert AccessControl.list_actions() == ["read", "write", "delete"]

    def test_get_matrix(self, ac):
        matrix = AccessControl.get_matrix()
        assert "admin" in matrix
        assert matrix["admin"]["read"] == "*"


# ---------------------------------------------------------------------------
# AuditTrail 测试
# ---------------------------------------------------------------------------


class TestAuditTrail:
    """审计追踪 Skill 测试"""

    @pytest.fixture
    def trail(self):
        return AuditTrail()

    def test_format_entries(self, trail):
        events = [
            {"ts": "2026-01-01T10:00", "agent": "G1", "action": "work", "result": "ok"},
            {"ts": "2026-01-01T10:01", "agent": "G2", "action": "audit", "result": "ok"},
        ]
        result = trail.execute({"events": events})

        assert len(result["entries"]) == 2
        assert "[2026-01-01T10:00] G1: work -> ok" in result["entries"][0]

    def test_summary_aggregation(self, trail):
        events = [
            {"ts": "t1", "agent": "G1", "action": "a", "result": "ok"},
            {"ts": "t2", "agent": "G1", "action": "b", "result": "ok"},
            {"ts": "t3", "agent": "G2", "action": "c", "result": "ok"},
        ]
        result = trail.execute({"events": events})

        assert result["summary"]["total"] == 3
        assert result["summary"]["by_agent"] == {"G1": 2, "G2": 1}

    def test_report_generation(self, trail):
        events = [
            {"ts": "2026-01-01T10:00", "agent": "G1", "action": "work", "result": "ok"},
        ]
        result = trail.execute({"events": events})

        assert "审计报告" in result["report"]
        assert "G1" in result["report"]

    def test_empty_events_raises(self, trail):
        with pytest.raises(ValueError, match="不能为空列表"):
            trail.execute({"events": []})

    def test_missing_events_raises(self, trail):
        with pytest.raises(ValueError):
            trail.execute({})

    def test_invalid_event_missing_field(self, trail):
        events = [{"ts": "t1", "agent": "G1"}]  # 缺 action/result
        with pytest.raises(ValueError):
            trail.execute({"events": events})


# ---------------------------------------------------------------------------
# ResultVerify 测试
# ---------------------------------------------------------------------------


class TestResultVerify:
    """结果验证 Skill 测试"""

    @pytest.fixture
    def verify(self):
        return ResultVerify()

    # ---- completeness ----

    def test_completeness_good_answer(self, verify):
        result = verify.execute(input={
            "answer": "系统支持加密存储，并记录了完整的审计日志。",
            "expected_keys": ["加密", "审计日志"],
        })
        assert result["checks"]["completeness"] is True

    def test_completeness_missing_keys(self, verify):
        result = verify.execute(input={
            "answer": "系统运行正常。",
            "expected_keys": ["加密", "审计"],
        })
        assert result["checks"]["completeness"] is False
        assert any("缺少期望键" in i for i in result["issues"])

    def test_completeness_empty_answer(self, verify):
        # [转派修复·G2-sbapi] @agent: session-260809-tidy-tide | module: tests | ts: 2026-08-09T13:50+08:00
        # schema minLength=1：空 answer 直接抛 ValueError（不返回 checks）
        with pytest.raises(ValueError, match="should be non-empty"):
            verify.execute(input={"answer": ""})

    def test_completeness_too_short(self, verify):
        result = verify.execute(input={"answer": "完成"})
        assert result["checks"]["completeness"] is False

    # ---- format ----

    def test_format_placeholder_detected(self, verify):
        result = verify.execute(input={"answer": "TODO: 待实现"})
        assert result["checks"]["format"] is False
        assert any("占位" in i for i in result["issues"])

    def test_format_null_text(self, verify):
        result = verify.execute(input={"answer": "null"})
        assert result["checks"]["format"] is False

    def test_format_invalid_json(self, verify):
        result = verify.execute(input={"answer": "{invalid json"})
        assert result["checks"]["format"] is False

    def test_format_valid_json(self, verify):
        result = verify.execute(input={"answer": '{"key": "value"}'})
        assert result["checks"]["format"] is True

    # ---- consistency ----

    def test_consistency_internal_contradiction(self, verify):
        result = verify.execute(input={
            "answer": "系统支持加密存储。系统不支持加密存储。",
        })
        assert result["checks"]["consistency"] is False
        assert any("矛盾" in i for i in result["issues"])

    def test_consistency_with_reference(self, verify):
        # [转派修复·G2-sbapi] @agent: session-260809-tidy-tide | module: tests | ts: 2026-08-09T13:50+08:00
        # 实现为引用句覆盖率判定（>= 0.6）：answer 需覆盖 reference 全部要点
        result = verify.execute(input={
            "answer": "系统支持加密存储，并记录完整审计日志。",
            "reference": "系统支持加密存储，并记录完整审计日志。",
        })
        assert result["checks"]["consistency"] is True

    def test_consistency_reference_contradiction(self, verify):
        result = verify.execute(input={
            "answer": "系统不支持加密存储。",
            "reference": "系统支持加密存储。",
        })
        assert result["checks"]["consistency"] is False

    # ---- scoring ----

    def test_score_all_pass(self, verify):
        result = verify.execute(input={
            "answer": "系统支持加密存储，并记录了完整的审计日志。",
        })
        assert result["passed"] is True
        assert result["score"] == 1.0

    def test_score_partial(self, verify):
        result = verify.execute(input={
            "answer": "TODO 完成",  # format 失败
        })
        assert result["score"] < 1.0
        assert 0 <= result["score"] <= 1

    # ---- pure function ----

    def test_verify_result_function(self):
        result = verify_result(
            answer="系统支持加密存储。",
            expected_keys=["加密"],
        )
        assert "passed" in result
        assert "score" in result

    def test_missing_answer_raises(self, verify):
        with pytest.raises(ValueError):
            verify.execute(input={})
