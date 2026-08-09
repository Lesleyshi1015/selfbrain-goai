# @agent: session-260809-airy-mesa | module: demo | ts: 2026-08-09T13:00+08:00
"""
src/demo.py — SelfBrain-GOAI 端到端演示入口

SelfBrain-GOAI 适配项目 · G16-demo

功能：
    跑通完整隐私查询流程：
    用户查询 → 黑板写入 → Workers 执行 → 完整度评估 →
    Skill 增强（PrivacyShield 脱敏 + ResultVerify 核查 + DataFusion 融合 +
    AccessControl 访问控制 + AuditTrail 审计追踪 + MemoryProbe 查询扩展）→
    Validator 6维核查 → 最终报告输出

双模式：
    - 默认 stub 模式：不加载真实模型，engine 返回 pending/空结构，
      demo 仍能完整跑通展示流程
    - --real 模式：真实加载模型；加载失败时优雅降级回 stub 并打印提示

用法：
    python src/demo.py "我的隐私数据存哪里"
    python src/demo.py "我的账号密码存在哪？" --real
    python -c "import sys; sys.path.insert(0,'src'); import demo; demo.main()"

身份指纹：
    文件头 @agent 注释为总调度 grep 定位归属 session 的铁证。
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── 路径注入：确保 src/ 在 sys.path 中 ──────────────────────────────────────
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# ── [转派修复·G2-sbapi] @agent: session-260809-tidy-tide | module: sb-api | ts: 2026-08-09T13:38+08:00 ──
# 模块级暴露 create_engine（测试 patch("demo.create_engine") 需要；
# sb_api import 零副作用、不加载模型）。import 失败时置 None，行为与延迟导入等价。
try:
    from sb_api import create_engine  # noqa: E402
    _SB_API_OK = True
except ImportError:
    create_engine = None  # type: ignore[assignment]
    _SB_API_OK = False


# ── 黑板路径 ─────────────────────────────────────────────────────────────────
_BOARD_PATH = _SRC_DIR.parent / ".swarm-board" / "board.json"
_AGENT_KEY = "G16-demo"
_SESSION_ID = "260809-airy-mesa"


# ══════════════════════════════════════════════════════════════════════════════
#  黑板读写工具
# ══════════════════════════════════════════════════════════════════════════════

def _read_board() -> Dict[str, Any]:
    """读取 board.json（不存在时返回空结构）。"""
    if not _BOARD_PATH.exists():
        return {"agents": {}}
    try:
        return json.loads(_BOARD_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"agents": {}}


def _write_board(board: Dict[str, Any]) -> None:
    """写入 board.json（确保目录存在）。"""
    _BOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    _BOARD_PATH.write_text(
        json.dumps(board, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _board_update(status: str, **kwargs: Any) -> None:
    """原子更新 board.json 中 G16-demo 条目。"""
    board = _read_board()
    board.setdefault("agents", {})
    entry = board["agents"].get(_AGENT_KEY, {})
    entry.update(kwargs)
    entry["status"] = status
    entry["updatedAt"] = datetime.now(timezone(timedelta(hours=8))).isoformat()
    board["agents"][_AGENT_KEY] = entry
    _write_board(board)


# ══════════════════════════════════════════════════════════════════════════════
#  Engine 管理（stub / real 双模式）
# ══════════════════════════════════════════════════════════════════════════════

def _try_create_engine(real_mode: bool) -> Tuple[Any, bool]:
    """
    尝试创建 SBEngine。

    Args:
        real_mode: True 则尝试真实加载；False 则始终 stub。

    Returns:
        (engine, is_real) — is_real 表示是否成功加载真实模型。
    """
    if not real_mode:
        try:
            if not _SB_API_OK or create_engine is None:
                raise ImportError("sb_api 不可用（create_engine 未导入）")
            return create_engine(), False
        except Exception as exc:
            print(f"  [WARN] stub 引擎创建失败: {exc}", file=sys.stderr)
            raise
    # real_mode
    try:
        if not _SB_API_OK or create_engine is None:
            raise ImportError("sb_api 不可用（create_engine 未导入）")
        engine = create_engine()
        # 试探性调用一个轻量方法，确认模型可加载
        engine.decompose("test")
        return engine, True
    except Exception as exc:
        print(f"  [WARN] 真实模型加载失败，降级为 stub 模式: {exc}", file=sys.stderr)
        try:
            if not _SB_API_OK or create_engine is None:
                raise ImportError("sb_api 不可用（create_engine 未导入）")
            return create_engine(), False
        except Exception:
            raise


# ══════════════════════════════════════════════════════════════════════════════
#  Worker 执行编排
# ══════════════════════════════════════════════════════════════════════════════

def _run_workers(
    team_room: Any,
    engine: Any,
    real_mode: bool,
) -> Dict[str, Any]:
    """
    依次执行各 Worker Agent，将结果写回黑板。

    执行顺序（有依赖关系）：
        1. MemoryNavigator  — 读取 user_query → navigator_result
        2. CipherGenerator  — 读取 user_query → cipher_result
        3. DataCoordinator  — 读取 navigator_result + cipher_result → coordinator_result
        4. PolicyEnforcer   — 读取 output_to_check → policy_result
        5. AuditLogger      — 读取所有 *_result → audit_result

    Args:
        team_room: TeamRoom 实例。
        engine: SBEngine 实例。
        real_mode: 是否真实模式（影响日志输出）。

    Returns:
        各 Worker 执行结果字典 {worker_name: result}。
    """
    from agents.navigator import MemoryNavigator
    from agents.cipher import CipherGenerator
    from agents.coordinator import DataCoordinator
    from agents.policy import PolicyEnforcer
    from agents.audit import AuditLogger

    results: Dict[str, Any] = {}
    mode_tag = "real" if real_mode else "stub"

    # 1. Navigator
    print(f"  [{mode_tag}] MemoryNavigator 执行记忆检索...")
    # [转派修复·G2-sbapi] @agent: session-260809-tidy-tide | module: demo | ts: 2026-08-09T13:58+08:00
    # R2 P0-2/P1-4：注入共享 engine，避免真实模式多实例重复加载模型、unload 不协调
    nav = MemoryNavigator("G4-navigator", team_room, engine)
    results["navigator"] = nav.execute({"action": "work"})
    print(f"    → status={results['navigator'].get('status')}")

    # 2. Cipher
    print(f"  [{mode_tag}] CipherGenerator 执行加密分析...")
    cipher = CipherGenerator(team_room, engine)
    results["cipher"] = cipher.execute({"action": "work"})
    print(f"    → status={results['cipher'].get('status')}")

    # 3. Coordinator
    print(f"  [{mode_tag}] DataCoordinator 执行数据协调...")
    coord = DataCoordinator(team_room)
    results["coordinator"] = coord.execute({"action": "work"})
    print(f"    → status={results['coordinator'].get('status')}")

    # 4. Policy — 需要先写入 output_to_check
    output_text = team_room.read("user_query") or "隐私查询结果"
    team_room.write("output_to_check", output_text, updated_by="G16-demo")
    print(f"  [{mode_tag}] PolicyEnforcer 执行策略校验...")
    policy = PolicyEnforcer(team_room, engine)
    results["policy"] = policy.execute({"action": "work"})
    print(f"    → allowed={results['policy'].get('allowed')}")

    # 5. Audit
    print(f"  [{mode_tag}] AuditLogger 执行审计记录...")
    audit = AuditLogger("G8-audit", team_room, write_file=True)
    results["audit"] = audit.execute({"action": "audit"})
    print(f"    → entries={results['audit'].get('entries_count', 0)}")

    return results


# ══════════════════════════════════════════════════════════════════════════════
#  Skills 增强
# ══════════════════════════════════════════════════════════════════════════════

def _run_skills(
    query: str,
    blackboard: Dict[str, Any],
) -> Dict[str, Any]:
    """
    用 6 个 Skills 对查询和结果做增强校验。

    Args:
        query: 用户原始查询。
        blackboard: 黑板全量数据。

    Returns:
        各 Skill 结果字典。
    """
    from skills.privacy_shield import PrivacyShield
    from skills.memory_probe import MemoryProbe
    from skills.data_fusion import DataFusion
    from skills.access_control import AccessControl
    from skills.audit_trail import AuditTrail
    from skills.result_verify import ResultVerify

    results: Dict[str, Any] = {}

    # 1. PrivacyShield — 脱敏检查
    print("  [Skill] PrivacyShield 脱敏检查...")
    shield = PrivacyShield()
    shield_result = shield.execute(text=query)
    results["privacy_shield"] = shield_result
    print(f"    → risk_level={shield_result.get('risk_level')}, "
          f"detected={len(shield_result.get('detected', []))}")

    # 2. MemoryProbe — 查询扩展
    print("  [Skill] MemoryProbe 查询扩展...")
    probe = MemoryProbe()
    probe_result = probe.execute(input={"query": query, "context": "privacy"})
    results["memory_probe"] = probe_result
    print(f"    → expanded={len(probe_result.get('expanded', []))}, "
          f"decomposed={len(probe_result.get('decomposed', []))}")

    # 3. DataFusion — 融合 Worker 结果
    print("  [Skill] DataFusion 数据融合...")
    fusion = DataFusion()
    items = []
    for key in ("navigator_result", "cipher_result", "coordinator_result", "policy_result"):
        val = blackboard.get(key)
        if val:
            items.append({
                "source": key.replace("_result", ""),
                "content": json.dumps(val, ensure_ascii=False, default=str)[:500],
                "score": 0.8,
            })
    if items:
        fusion_result = fusion.execute({"items": items, "threshold": 0.8, "top_n": 5})
    else:
        fusion_result = {"fused": [], "deduped": 0, "top": []}
    results["data_fusion"] = fusion_result
    print(f"    → fused={len(fusion_result.get('fused', []))}, "
          f"deduped={fusion_result.get('deduped', 0)}")

    # 4. AccessControl — 访问控制检查
    print("  [Skill] AccessControl 访问控制...")
    access = AccessControl()
    access_result = access.execute(
        role="user",
        action="read",
        resource="memory/notes",
        context={"public": True},
    )
    results["access_control"] = access_result
    print(f"    → allowed={access_result.get('allowed')}, rule={access_result.get('rule')}")

    # 5. AuditTrail — 审计追踪
    print("  [Skill] AuditTrail 审计追踪...")
    trail = AuditTrail()
    audit_result = blackboard.get("audit_result", {})
    events = audit_result.get("entries", [])
    # 字段归一化：AuditLogger 输出 (timestamp/operation/result_summary)
    # AuditTrail 要求 (ts/action/result)
    normalized_events = []
    for e in events:
        ne: Dict[str, str] = {}
        ne["ts"] = e.get("timestamp") or e.get("ts") or ""
        ne["agent"] = e.get("agent", "")
        ne["action"] = e.get("action") or e.get("operation") or ""
        ne["result"] = e.get("result") or e.get("result_summary") or ""
        normalized_events.append(ne)
    if not normalized_events:
        normalized_events = [{
            "ts": datetime.now(timezone(timedelta(hours=8))).isoformat(),
            "agent": "G16-demo",
            "action": "demo:skills_run",
            "result": "ok",
        }]
    trail_result = trail.execute({"events": normalized_events})
    results["audit_trail"] = trail_result
    print(f"    → entries={len(trail_result.get('entries', []))}, "
          f"total={trail_result.get('summary', {}).get('total', 0)}")

    # 6. ResultVerify — 结果核查
    print("  [Skill] ResultVerify 结果核查...")
    verify = ResultVerify()
    # 构造一个答案文本用于核查
    answer_text = json.dumps(
        {k: blackboard.get(k) for k in (
            "navigator_result", "cipher_result",
            "coordinator_result", "policy_result",
        ) if blackboard.get(k)},
        ensure_ascii=False,
        default=str,
    )[:1000]
    verify_result = verify.execute(input={
        "answer": answer_text,
        "expected_keys": ["status", "component"],
    })
    results["result_verify"] = verify_result
    print(f"    → passed={verify_result.get('passed')}, score={verify_result.get('score')}")

    return results


# ══════════════════════════════════════════════════════════════════════════════
#  Validator 6维核查
# ══════════════════════════════════════════════════════════════════════════════

def _run_validator(
    blackboard: Dict[str, Any],
) -> Any:
    """
    用 Validator 对黑板执行 6 维核查。

    Args:
        blackboard: 黑板全量数据。

    Returns:
        ValidationResult 对象。
    """
    from agents.validator import Validator
    from agent_teams_sdk import TeamRoom

    room = TeamRoom("validator-temp")
    # 将黑板数据写入临时黑板供 Validator 读取
    for k, v in blackboard.items():
        room.write(k, v, updated_by="G16-demo")

    validator = Validator("G9-validator", room)
    result = validator.validate(blackboard)
    print(f"  [Validator] 6维核查: passed={result.passed}, "
          f"errors={len(result.errors)}, warnings={len(result.warnings)}")
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  报告生成
# ══════════════════════════════════════════════════════════════════════════════

def _generate_report(
    query: str,
    guardian_result: Dict[str, Any],
    completeness: float,
    blackboard: Dict[str, Any],
    skills_result: Dict[str, Any],
    validator_result: Any,
    elapsed_ms: float,
    mode: str,
) -> str:
    """生成最终演示报告（markdown 格式）。"""
    now_str = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S %Z")

    lines: List[str] = [
        "=" * 60,
        "  SelfBrain-GOAI 端到端演示报告",
        "=" * 60,
        "",
        f"时间: {now_str}",
        f"模式: {mode}",
        f"查询: {query}",
        f"耗时: {elapsed_ms:.1f} ms",
        "",
        "─" * 60,
        "  1. Guardian 处理结果",
        "─" * 60,
        f"  状态: {guardian_result.get('status')}",
        f"  组件: {guardian_result.get('component')}",
        f"  完整度: {completeness:.2f}",
        "",
        "─" * 60,
        "  2. 黑板状态",
        "─" * 60,
    ]

    for key in (
        "user_query", "navigator_result", "cipher_result",
        "coordinator_result", "policy_result", "audit_result",
    ):
        val = blackboard.get(key)
        status = "✓" if val else "✗"
        summary = ""
        if val:
            if isinstance(val, dict):
                summary = f" status={val.get('status', '?')}"
            else:
                summary = f" {str(val)[:60]}"
        lines.append(f"  [{status}] {key}:{summary}")

    lines += [
        "",
        "─" * 60,
        "  3. Skills 增强结果",
        "─" * 60,
    ]

    # PrivacyShield
    ps = skills_result.get("privacy_shield", {})
    lines.append(f"  PrivacyShield:  risk={ps.get('risk_level', '?')}, "
                 f"detected={len(ps.get('detected', []))}")

    # MemoryProbe
    mp = skills_result.get("memory_probe", {})
    lines.append(f"  MemoryProbe:    expanded={len(mp.get('expanded', []))}, "
                 f"decomposed={len(mp.get('decomposed', []))}")

    # DataFusion
    df = skills_result.get("data_fusion", {})
    lines.append(f"  DataFusion:     fused={len(df.get('fused', []))}, "
                 f"deduped={df.get('deduped', 0)}")

    # AccessControl
    ac = skills_result.get("access_control", {})
    lines.append(f"  AccessControl:  allowed={ac.get('allowed')}, rule={ac.get('rule', '?')}")

    # AuditTrail
    at = skills_result.get("audit_trail", {})
    lines.append(f"  AuditTrail:     entries={len(at.get('entries', []))}, "
                 f"total={at.get('summary', {}).get('total', 0)}")

    # ResultVerify
    rv = skills_result.get("result_verify", {})
    lines.append(f"  ResultVerify:   passed={rv.get('passed')}, score={rv.get('score', 0)}")

    lines += [
        "",
        "─" * 60,
        "  4. Validator 6维核查",
        "─" * 60,
        f"  通过: {validator_result.passed}",
        f"  错误: {len(validator_result.errors)}",
        f"  警告: {len(validator_result.warnings)}",
    ]

    if validator_result.errors:
        lines.append("  错误详情:")
        for e in validator_result.errors[:5]:
            lines.append(f"    - {e}")
    if validator_result.warnings:
        lines.append("  警告详情:")
        for w in validator_result.warnings[:5]:
            lines.append(f"    - {w}")

    lines += [
        "",
        "─" * 60,
        "  5. 审计引用",
        "─" * 60,
    ]
    audit_result = blackboard.get("audit_result", {})
    file_path = audit_result.get("file_path")
    if file_path:
        lines.append(f"  审计日志: {file_path}")
    entries_count = audit_result.get("entries_count", 0)
    lines.append(f"  审计条目: {entries_count}")

    lines += [
        "",
        "=" * 60,
        "  演示完成",
        "=" * 60,
    ]

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  主函数
# ══════════════════════════════════════════════════════════════════════════════

def main(argv: Optional[List[str]] = None) -> int:
    """
    端到端演示主入口。

    Args:
        argv: 命令行参数（默认 sys.argv[1:]）。

    Returns:
        0 表示成功，非 0 表示失败。
    """
    # ── [P0 修复·转派 G2-sbapi] @agent: session-260809-tidy-tide | module: sb-api | ts: 2026-08-09T13:40+08:00 ──
    # 保存原始流引用（finally 恢复，幂等无害）
    _orig_stdout, _orig_stderr = sys.stdout, sys.stderr

    # Windows UTF-8 兼容（控制台 / 管道重定向 / pytest 均适用）。
    # 修复说明：原实现用 TextIOWrapper 替换 sys.stdout，替换对象 GC 时会关闭底层
    # buffer → pytest capture 损坏（"I/O operation on closed file"）；且 isatty 检查
    # 会让管道重定向（非 TTY，GBK 编码）打印 ✓ 等字符时 UnicodeEncodeError。
    # 改用 reconfigure()：不创建新 wrapper、不持有/关闭原 buffer，无 GC 风险，
    # 从根上消除两类问题。无 reconfigure 的流（如 io.StringIO）自动跳过。
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, io.UnsupportedOperation):
            pass

    parser = argparse.ArgumentParser(
        description="SelfBrain-GOAI 端到端演示",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python src/demo.py "我的隐私数据存哪里"
  python src/demo.py "我的账号密码存在哪？" --real
        """,
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="我的隐私数据存储在什么地方",
        help="用户隐私查询文本（默认: 我的隐私数据存储在什么地方）",
    )
    parser.add_argument(
        "--real",
        action="store_true",
        help="真实模式：尝试加载真实模型（失败则降级为 stub）",
    )

    args = parser.parse_args(argv)
    query: str = args.query
    real_mode: bool = args.real

    print("=" * 60)
    print("  SelfBrain-GOAI 端到端演示")
    print("=" * 60)
    print(f"  查询: {query}")
    print(f"  模式: {'real' if real_mode else 'stub'}")
    print()

    # 更新黑板：开始
    _board_update(
        status="working",
        sessionId=_SESSION_ID,
        module="demo",
    )

    start_time = time.perf_counter()

    try:
        # 1. 创建引擎
        print("> 步骤 1: 创建 SBEngine...")
        engine, is_real = _try_create_engine(real_mode)
        if is_real != real_mode:
            real_mode = is_real
            print(f"  [INFO] 当前运行模式: {'real' if is_real else 'stub'}")
        print(f"  ✓ 引擎就绪（{'real' if is_real else 'stub'} 模式）")
        print()

        # 2. 创建 TeamRoom 并写入查询
        print("> 步骤 2: 创建 TeamRoom 黑板...")
        from agent_teams_sdk import TeamRoom
        room = TeamRoom("g16-demo-query")
        room.write("user_query", query, updated_by="G16-demo")
        print(f"  ✓ 黑板创建完成，查询已写入")
        print()

        # 3. 执行 Workers
        print("> 步骤 3: 执行 Worker Agents...")
        worker_results = _run_workers(room, engine, real_mode)
        print("  ✓ 所有 Workers 执行完成")
        print()

        # 4. 读取黑板 + 评估完整度
        print("> 步骤 4: 评估黑板完整度...")
        from agents.guardian import PrivacyGuardian
        blackboard = room.read_all()
        guardian = PrivacyGuardian("PrivacyGuardian", room)
        completeness = guardian.evaluate_completeness(blackboard)
        print(f"  ✓ 完整度: {completeness:.2f}")
        print()

        # 5. Guardian 融合结果
        print("> 步骤 5: Guardian 重建 + 融合结果...")
        raw_result = guardian.reconstruct_result(blackboard)
        guardian_result = guardian._fuse_results(raw_result)
        # 写回黑板（供 Validator 完整性核查使用）
        room.write("guardian_result", guardian_result, updated_by="G16-demo")
        print(f"  ✓ status={guardian_result.get('status')}, "
              f"component={guardian_result.get('component')}")
        # 重新读取黑板（确保 guardian_result 可见于后续步骤）
        blackboard = room.read_all()
        print()

        # 6. Skills 增强
        print("> 步骤 6: Skills 增强校验...")
        skills_result = _run_skills(query, blackboard)
        print("  ✓ 6 个 Skills 执行完成")
        print()

        # 7. Validator 6维核查
        print("> 步骤 7: Validator 6维核查...")
        validator_result = _run_validator(blackboard)
        print()

        # 8. 生成报告
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        report = _generate_report(
            query=query,
            guardian_result=guardian_result,
            completeness=completeness,
            blackboard=blackboard,
            skills_result=skills_result,
            validator_result=validator_result,
            elapsed_ms=elapsed_ms,
            mode="real" if real_mode else "stub",
        )

        print()
        print(report)

        # 更新黑板：完成
        _board_update(
            status="done",
            sessionId=_SESSION_ID,
            module="demo",
            output=f"demo 完成: completeness={completeness:.2f}, "
                   f"validator_passed={validator_result.passed}, "
                   f"elapsed={elapsed_ms:.0f}ms",
            files=["src/demo.py"],
        )

        return 0

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        print(f"\n[X] 演示失败 ({elapsed_ms:.0f}ms): {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()

        _board_update(
            status="error",
            sessionId=_SESSION_ID,
            module="demo",
            output=f"演示失败: {exc}",
            foundIssue=str(exc),
        )
        return 1

    finally:
        # [P0 修复·转派 G2-sbapi] 恢复原始 stdout/stderr（幂等；reconfigure 未替换对象）
        sys.stdout, sys.stderr = _orig_stdout, _orig_stderr

        # 显存安全：释放所有模型
        try:
            from sb_api import create_engine as _create_engine
            _eng = _create_engine()
            _eng.unload_all()
            print("\n  [INFO] 模型已卸载 (unload_all)")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    sys.exit(main())
