# SECRET-CLEAN — 公开仓库去机密报告

> Agent: S1-secret-clean | session: 260815-frosty-ember
> 日期: 2026-08-15 | 状态: 完成
> 背景: github.com/Lesleyshi1015/selfbrain-goai 临时公开评审前的安全红线清理。

## 一、已从 git 移除（本地保留完整副本）

| 目录/文件 | 处理 | 数量 |
|---|---|---|
| `参赛PPT/` | `git rm -r --cached`（含 500字简介/内容源/建议新增/ppt 建议，全部移除） | 23 文件 |
| `docs/` | `git rm --cached`（先前已完成，本次随提交生效） | 22 文件 |
| `research/` | `git rm --cached`（先前已完成） | 7 文件 |
| `.specs/CONTEXT.md` / `ARCHITECTURE.md` / `01-goi-rewrite/` | `git rm --cached`（先前已完成） | 8 文件 |

> 全部使用 `git rm --cached`：仅从 git 索引移除，本地文件未删（WPS 制作 PPT、内部文档均不受影响）。

## 二、文档重写（去机密）

| 文件 | 处理 |
|---|---|
| `README.md` | 重写：删除 VibeThinker-3B/Qwen2.5/MEMO/"记忆即模型"；改为"本地轻量模型引擎（微调策略注入）"通用表述；保留运行入口/依赖/样例/运行证据(195 tests)/黑盒说明(SB_SELFBRAIN_SRC)/品牌 |
| `CHANGELOG.md` | 重写：删除模型名与选型细节，保留项目演进框架 |
| `LESSONS.md` | 重写：删除模型名/MEMO 方法论细节，保留工程经验框架（架构一致性、方法论 vs 产品表述边界） |

## 三、代码清理（src/ 与 tests/）

| 文件 | 处理 |
|---|---|
| `src/sb_api/loader.py` | docstring 去 `F:\SelfBrain\src` 与"4 个已微调模型"；`_DEFAULT_SRC` 改为占位符 `<selfbrain-engine-src>`（本地路径示例）；新增 `_resolve_src_path()`（环境变量 SB_SELFBRAIN_SRC 优先，未设置回退占位符）；Navigator/Cipher/Broker docstring 模型名 → "轻量本地模型（INT4 量化）"；错误提示改为引导设置环境变量 |
| `src/sb_api/__init__.py` | 包 docstring 去 `F:\SelfBrain\src`，改为"引擎源码路径由环境变量 SB_SELFBRAIN_SRC 注入" |
| `src/sb_api/engine.py` | SBEngine docstring 去"4 个微调模型"，改"引擎组件统一访问入口" |
| `src/demo.py` | `F:/memory-palace-goai` 硬编码 → 环境变量 `MEMORY_PALACE_SRC` 注入（未设置时优雅降级回 sbapi 后端）；补 `import os` |
| `tests/test_sb_api.py` | `F:/SelfBrain/src` 断言 → 可移植断言（默认占位符 + `_resolve_src_path()` + monkeypatch 环境变量覆盖测试） |

## 四、.gitignore 更新

新增排除规则（防止重新被跟踪）：
```
docs/
research/
参赛PPT/
.specs/01-goi-rewrite/
.specs/ARCHITECTURE.md
.specs/CONTEXT.md
```

## 五、测试与扫描验证

- ✅ `python -m pytest tests/ -q` → **199 passed**（原 198 全保留 + 1 新增环境变量可移植测试；功能零破坏）
- ✅ git 索引敏感词全扫描（VibeThinker/Qwen/QLoRA/NF4/F:/SelfBrain/F:/models/F:/memory/MEMO 训练/训练方法/Memory as a Model/580）→ **CLEAN**
- ✅ 磁盘级扫描 src/tests/agent_teams_sdk/README/CHANGELOG/LESSONS/pyproject/02-goai-adapt → 仅剩安全引用（`.specs/02-goai-adapt/CLONE-RUN-CHECK.md` 的 `F:/SelfBrain-GOAI` 为公开仓库本地克隆证据，属参赛工程证据，按任务要求保留）
- ✅ `src/selfbrain_goai.egg-info/` 过期构建产物（含旧 README 机密）已本地删除（gitignored 未跟踪，重新 `pip install -e .` 自动重建）

## 六、保留项（未触碰）

- `.specs/02-goai-adapt/`（CHANGE/CLONE-RUN-CHECK/REVIEW/TEST 为参赛工程证据）
- `agent_teams_sdk/`（共享框架，无机密，零修改）
- `src/agents/`、`src/skills/` 其余业务代码（无敏感引用）

## 七、遗留提示

1. 公开前请确认远程分支无历史泄露：若评审克隆的是 `master` 最新提交，本清理已生效；**历史 commit 中的旧 README/参赛PPT 仍在 git 历史里**——若评审可访问完整历史，需用 `git filter-repo` 或重建历史彻底清除（本任务仅保证最新提交干净，此为提交红线默认范围）。
2. `参赛PPT/` 本地保留（WPS 制作 PPT 用），不入代码包。
