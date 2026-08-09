<!-- @agent: session-260809-ruby-hill | module: ppt | ts: 2026-08-09T15:05+08:00 -->

# GOAI 参赛提交说明 — SelfBrain-GOAI

> **GOAI 2026 · 赛道一「新智基座 | AgentInfra」 · 初赛提交包（Wave 6）**
> 本文档是参赛提交的**总说明**，配套提交材料清单、复现方式与评审要点对照。

---

## 1. 项目一句话介绍

> **SelfBrain-GOAI**：面向个人数据分散存储隐私痛点的**多 Agent 隐私防护协作本地隐私模型**——
> 7 个专业 Agent 以黑板模式协同，6 个规则化 Skill 以 JSON Schema 校验约束，
> 通过桥接层黑盒引用主项目 4 大模型引擎，**"接入你想用的任何外部先进大模型，但把隐私留在你的手上"**。

| 项目属性 | 内容 |
|---------|------|
| **参赛赛道** | GOAI 2026 · 赛道一「新智基座 \| AgentInfra」 |
| **项目形态** | 独立代码 + 桥接引用（业务层独立仓库，引擎黑盒只读引用） |
| **核心成果** | sb_api 桥接层 + 7 Agents + 6 Skills + 端到端 demo + 195 测试 / 88% 覆盖 |
| **仓库位置** | `F:\SelfBrain-GOAI`（参赛业务层，独立 git 仓库） |
| **提交时间** | 2026-08-16 初赛截止（当前 8.9，已进入 Wave 6 提交准备） |

---

## 2. 架构总览

### 2.1 三层一框架的分层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│  F:\SelfBrain-GOAI（参赛业务层 · 独立仓库 · 本提交主体）              │
│                                                                     │
│  ┌───────────┐  ┌──────────────────────────────────────────────┐   │
│  │ src/demo  │  │ src/agents（7 Agent，继承 agent-teams-sdk）   │   │
│  │ 端到端演示 │  │  Guardian(调度) + 5 Worker + Validator(核查)  │   │
│  └───────────┘  └──────────────────────────────────────────────┘   │
│  ┌───────────────────────────────────────────┐  ┌──────────────┐   │
│  │ src/skills（6 Skill · BaseSkill + JSON    │  │ src/sb_api   │   │
│  │  Schema 双轨校验）                         │  │ 桥接层(只读)  │   │
│  └───────────────────────────────────────────┘  └──────┬───────┘   │
└─────────────────────────────────────────────────────────┼─────────┘
                        │ 只读引用（零修改、零写入）
┌───────────────────────▼───────────────────────────────────────────┐
│  F:\SelfBrain\src（主项目引擎 · 黑盒）                              │
│  model_loader → core / navigator / cipher / broker（4 模型）       │
└───────────────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────────┐
│  F:\agent-teams-sdk（AgentTeams 协同框架 · 已 pip install -e）      │
│  CuratorAgent / WorkerAgent / ValidatorAgent / BaseSkill /        │
│  TeamRoom（黑板）· 源码零修改                                       │
└───────────────────────────────────────────────────────────────────┘
```

### 2.2 架构 Mermaid 图（建议放 PPT / 提交文档附图）

```mermaid
graph TB
    subgraph GOAI[F:\SelfBrain-GOAI 参赛业务层]
        DEMO[demo.py 端到端演示]
        subgraph AGENTS[7 Agents · 黑板模式]
            G[Guardian<br/>总调度·完整度评估]
            W1[Navigator] --- W2[Cipher]
            W2 --- W3[Coordinator]
            W3 --- W4[Policy]
            W4 --- W5[Audit]
            G --- W1
            G --- V[Validator 6维核查]
        end
        subgraph SKILLS[6 Skills · JSON Schema]
            S1[privacy_shield] S2[memory_probe] S3[data_fusion]
            S4[access_control] S5[audit_trail] S6[result_verify]
        end
        subgraph BRIDGE[src/sb_api 桥接层]
            L[loader 惰性加载] E[SBEngine 统一 envelope]
        end
        DEMO --> AGENTS
        AGENTS --> SKILLS
        AGENTS --> BRIDGE
    end
    subgraph ENGINE[F:\SelfBrain 主项目引擎 · 黑盒 · 零修改]
        ML[model_loader] --> CORE[core] & NAV[navigator] & CIP[cipher] & BRO[broker]
    end
    subgraph SDK[F:\agent-teams-sdk 框架 · 零修改]
        BB[(TeamRoom 黑板)] BA[BaseAgent 基类] BS[BaseSkill 基类]
    end
    BRIDGE -->|只读加载 4 模型| ENGINE
    AGENTS -->|继承| SDK
```

### 2.3 分层职责

| 层 | 位置 | 职责 | 边界 |
|----|------|------|------|
| **业务层** | `F:\SelfBrain-GOAI\src` | Agents/Skills/Demo，参赛全部创新逻辑 | 独立仓库，可独立评审、独立测试 |
| **桥接层** | `src/sb_api/` | 只读加载主项目 4 模型，统一 envelope（`ok/pending/error`） | **零修改主项目**，惰性导入（import 不加载模型） |
| **引擎黑盒** | `F:\SelfBrain\src` | core/navigator/cipher/broker 4 模型 | 只读引用，git diff 为空 |
| **框架层** | `F:\agent-teams-sdk` | TeamRoom 黑板、Agent/Skill 基类 | 只安装不改源码 |

> **黑盒保证**：`sb_api/loader.py` 是唯一 import `model_loader` 的入口，`SRC_PATH` 支持环境变量
> `SB_SELFBRAIN_SRC` 覆盖；grep 审计确认所有对 F:\SelfBrain 的引用均为只读路径或文档注释。

---

## 3. 核心亮点（对照参赛评审点）

### 3.1 隐私保护多 Agent 协同（7 Agent 黑板模式）

- **Privacy Guardian（Leader）**：任务分析 → 黑板发布 → Worker 调度 → 完整度评估（阈值 0.8 停止调度）→ 结果融合
- **5 个 Worker**：Memory Navigator（检索）/ Cipher Generator（加密分析）/ Data Coordinator（数据融合）/
  Policy Enforcer（权限校验）/ Audit Logger（审计日志）
- **Validator**：最终结果 **6 维核查**（完整性/正确性/隐私/一致性/时效性/安全性）
- 所有 Agent 通过 **TeamRoom 共享黑板** 松耦合交互，零直接调用；Guardian 是唯一调度入口，职责链清晰

### 3.2 6 Skill 规则驱动 + JSON Schema 校验

| Skill | 职责 | 校验方式 |
|-------|------|---------|
| `privacy_shield` | PII 检测脱敏（手机/身份证/银行卡/地址/key） | BaseSkill schema 约束 + jsonschema 双轨 |
| `memory_probe` | 查询扩展/分解（同义词 12 + 关键词 20 + 复合词） | jsonschema 严格校验 |
| `data_fusion` | 多源数据合并去重（归一化 + SequenceMatcher/Jaccard） | jsonschema 校验 |
| `access_control` | RBAC 角色权限（admin/owner/user/guest，fail-closed） | jsonschema 严格校验 |
| `audit_trail` | 审计条目生成 + 汇总报告 | jsonschema 严格校验 |
| `result_verify` | 完整性/格式/一致性检查 + 加权评分 | BaseSkill schema + jsonschema |

所有 Skill 继承 SDK `BaseSkill`，均实现 `name/version/schema/execute` 抽象契约，输入输出 JSON Schema（Draft 2020-12）校验，参数错误统一抛 `ValueError`（可预期、可测试）。

### 3.3 引擎桥接黑盒设计（主项目零修改）

- `sb_api/loader.py`：惰性加载 `model_loader`，包装 4 个加载函数（core/navigator/cipher/broker）+ unload，`_LOADED` 注册表避免重复加载占显存
- `sb_api/engine.py`：`SBEngine` 统一 envelope（`{status, data, component, action}`），8 个方法 stub 覆盖检索/加密/融合/策略/审计全流程
- `sb_api/__init__.py`：导出 + `create_engine()` 统一工厂
- **红线验证**：主项目 F:\SelfBrain 与框架 F:\agent-teams-sdk `git diff` 均为空

### 3.4 可观测 + 审计追踪

- **可观测（Tracer 概念）**：SBEngine 统一 envelope 贯穿全链路，每个组件返回 `status/data/component/action`，错误显式降级（error envelope），黑板状态实时可读
- **审计追踪**：AuditLogger 每次执行生成审计条目（时间戳/Agent/动作/结果），本地 JSONL 留档 + `audit_result` 写回黑板；AuditTrail Skill 提供格式化 entries/summary/report
- **验证闭环**：Validator 6 维核查 + ResultVerify 加权评分，结果可复现、可回查

---

## 4. 关键技术指标

| 指标 | 数值 | 依据 |
|------|------|------|
| 测试通过 | **195 passed / 0 failed / 0 errors** | `.specs/02-goai-adapt/TEST.md` |
| 覆盖率 | **88%**（1623 stmts / 199 miss，目标 >80%） | 同上，pytest --cov |
| 测试耗时 | ~1.8s | 同上 |
| Demo 完整度 | **0.95（封顶）** | `guardian.evaluate_completeness` |
| 完整度评估机制 | 加权：navigator 0.35 + cipher 0.30 + coordinator 0.20 + policy 0.15，user_query 存在 +0.05，封顶 0.95 | `src/agents/guardian.py` |
| 测试模块覆盖 | conftest / sb_api / guardian / agents / skills / demo 6 个测试文件 | tests/ |

### 完整度评估机制（核心创新点）

```
score = 0.35 * (navigator_result 存在)
      + 0.30 * (cipher_result 存在)
      + 0.20 * (coordinator_result 存在)
      + 0.15 * (policy_result 存在)
      + 0.05 * (user_query 存在且 score>0)     # 额外加权
score = min(score, 0.95)                        # 封顶，杜绝"满分幻觉"
Guardian 在 score >= 0.80 时停止调度（达标即止，节省资源）
```

> 设计意图：**完整度是"驱动调度的活信号"**而非一次性打分——Guardian 每调度一个 Worker 后重算完整度，
> 缺什么补什么，形成"评估 → 补派 → 再评估"的自主闭环；0.95 封顶避免数据造假式满分。

---

## 5. 快速复现

```bash
# 0. 前置：主项目引擎（只读）与 SDK 框架（只装不改）
#    F:\SelfBrain\src          → 主项目（model_loader + 4 模型）
#    F:\agent-teams-sdk        → pip install -e . 已安装

# 1. 安装参赛业务层
cd F:\SelfBrain-GOAI
pip install -e .

# 2. 端到端 demo（stub 模式，不加载真实模型，全流程可跑）
python src/demo.py "我的隐私数据存储在什么地方"
#    真实模式（需主项目依赖 + 模型就绪）：
#    python src/demo.py "我的账号密码存在哪？" --real

# 3. 测试（195 passed / 88% 覆盖）
python -m pytest tests/ -q
python -m pytest tests/ --cov=src --cov-report=term-missing

# 4. 桥接层冒烟（验证对主项目只读加载能力）
python -c "from sb_api import create_engine; e = create_engine(); print(e)"
```

**预期输出**：demo 打印 7 Agent 协同全流程（检索→加密→融合→策略→审计→核查），
最终输出 `完整度: 0.95`、`validator_passed=True`，耗时毫秒级（stub 模式）。

---

## 6. 提交材料清单

> 建议按以下结构打包提交（zip，保留相对路径），评审者按 README 复现。

```
GOAI-SelfBrain-2026/
├── README.md                        ← 本说明的精简版（1 页）
├── GOAI-COMPETITION-PACK.md         ← 本文档（详细说明）
├── GOAI-PPT-SLIDES.md               ← PPT 大纲素材（12-15 页）
├── docs/                            ← 15 章技术文档
├── .specs/02-goai-adapt/
│   ├── CHANGE.md                    ← 变更范围与验收标准
│   ├── REVIEW-arch.md               ← 架构评审（3.7/5，P0 已修）
│   ├── REVIEW-bug.md                ← Bug 评审（3 P0 已修）
│   └── TEST.md                      ← 测试报告（195/88%）
├── src/
│   ├── sb_api/                      ← 桥接层
│   ├── agents/                      ← 7 Agent
│   ├── skills/                      ← 6 Skill
│   └── demo.py                      ← 端到端演示
├── tests/                           ← 6 个测试文件
├── pyproject.toml                   ← 可安装工程
└── 参赛PPT/                         ← 历史 PPT 素材（full-content-v3-final.md 等）
```

### 提交前自检清单

- [ ] `pip install -e .` 成功，`import sb_api / agents / skills` 可用
- [ ] `pytest tests/ -q` 全绿（195 passed）
- [ ] `pytest --cov=src` 覆盖率 ≥ 80%（当前 88%）
- [ ] `python src/demo.py "查询"` 端到端跑通（完整度 0.95）
- [ ] 主项目 F:\SelfBrain 与框架 F:\agent-teams-sdk 零修改（git diff 为空）
- [ ] 全部文件带 `@agent:` 身份指纹
- [ ] PPT 大纲 12-15 页完整（见 GOAI-PPT-SLIDES.md）

---

*SelfBrain-GOAI · GOAI 2026 赛道一 · 初赛提交包 · 2026-08-09*
