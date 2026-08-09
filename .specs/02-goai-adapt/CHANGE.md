<!-- @agent: session-260809-mild-seal | module: skeleton | ts: 2026-08-09T12:47+08:00 -->
# CHANGE-002: SelfBrain → GOAI 参赛代码适配（AgentTeams 框架落地）

**日期**: 2026-08-09
**状态**: planning → in_progress
**发起人**: Lesley（总调度规划）

## 变更标题

在 SelfBrain-GOAI 独立仓库（F:\SelfBrain-GOAI）中搭建可运行的参赛业务层：
通过 src/sb_api 桥接层黑盒引用主项目引擎，7 个 Agent 继承 agent-teams-sdk 基类，
6 个 Skill 以 JSON Schema 校验约束，交付端到端 demo 与 >80% 覆盖率的测试套件。

## 变更背景

- 参赛背景：GOAI（阿里巴巴全球AI大赛）赛道一「新智基座 | AgentInfra」，8.16 初赛提交
- 架构形态：**独立代码 + 桥接引用**
  - F:\SelfBrain-GOAI：参赛业务层（独立 git 仓库，本变更的目标）
  - F:\SelfBrain\src：主项目引擎（只读黑盒，零修改）
  - F:\agent-teams-sdk：通用 AgentTeams 协同框架（已 `pip install -e`，import 验证 OK，只安装不改源码）
- 现有基础：.specs/01-goi-rewrite 已完成全文档改写（7-Agent + 6-Skill + 黑板模式），
  docs/ 15 章文档就绪，本变更将其落为真实可运行代码

## 变更目标

1. 建立 src 布局 Python 工程（pyproject.toml，`pip install -e .` 可安装）
2. 桥接层 sb_api 真实加载主项目 4 个模型（不 mock），对外提供黑盒接口
3. 7 个 Agent（guardian/navigator/cipher/coordinator/policy/audit/validator）继承 SDK 基类
4. 6 个 Skill（privacy_shield/memory_probe/data_fusion/access_control/audit_trail/result_verify）通过 JSON Schema 校验
5. 端到端 demo（src/demo.py）跑通完整流程
6. pytest 覆盖率 >80%
7. 主项目 F:\SelfBrain 零修改、框架零修改

## 变更范围

**新增文件清单**（全部为新增，不改动任何既有文件）：

| 类别 | 文件 | 归属 Agent |
|------|------|-----------|
| 工程骨架 | `pyproject.toml` | G1-skeleton（本次） |
| 变更文档 | `.specs/02-goai-adapt/CHANGE.md` | G1-skeleton（本次） |
| 桥接层 | `src/sb_api/*`（engine loader、model facade、bridge 接口） | G2-sbapi |
| 桥接层 | `src/sb_api/__init__.py` | G2-sbapi |
| Agents | `src/agents/guardian.py` | G3-guardian |
| Agents | `src/agents/navigator.py` | G4-navigator |
| Agents | `src/agents/cipher.py` | G5-cipher |
| Agents | `src/agents/coordinator.py` | G6-coordinator |
| Agents | `src/agents/policy.py` | G7-policy |
| Agents | `src/agents/audit.py` | G8-audit |
| Agents | `src/agents/validator.py` | G9-validator |
| Agents | `src/agents/__init__.py` | G1-skeleton（本次占位） |
| Skills | `src/skills/privacy_shield.py` | G10-shield |
| Skills | `src/skills/memory_probe.py` | G11-probe |
| Skills | `src/skills/data_fusion.py` | G12-fusion |
| Skills | `src/skills/access_control.py` | G13-access |
| Skills | `src/skills/audit_trail.py` | G14-audit |
| Skills | `src/skills/result_verify.py` | G15-verify |
| Skills | `src/skills/__init__.py` | G1-skeleton（本次占位） |
| Demo | `src/demo.py` | G16-demo |
| 测试 | `tests/*`（各模块测试 + conftest） | G17-test |
| 测试 | `tests/__init__.py` | G1-skeleton（本次占位） |

**不影响的（红线）**：
- F:\SelfBrain\src 主项目引擎 —— 零修改，只读
- F:\agent-teams-sdk —— 只安装，不改源码
- 既有 .specs/01-goi-rewrite、docs/、research/、参赛PPT/ 等文档

## 架构约束

1. **主项目零修改**：F:\SelfBrain 任何文件不得写入，只允许运行时读取加载
2. **引擎黑盒只读**：sb_api 只通过公开接口/加载路径引用主项目，不依赖其内部实现细节，不反向修改
3. **框架只装不改**：agent-teams-sdk 依赖版本与 F:\agent-teams-sdk\pyproject.toml 保持一致
   （jsonschema>=4.0、PyYAML>=6.0、pytest>=7.0 dev），源码零修改
4. **分层执行**：G1 骨架 → G2 桥接（依赖 G1）→ Wave 2/3 Agents/Skills（依赖 G2）→ G16 demo（依赖全部）→ G17 test
5. **src 布局**：所有业务代码位于 src/ 下，包发现限定 sb_api/agents/skills
6. **身份指纹**：所有写入文件头携带 `@agent: session-<id> | module: <模块> | ts: <时间戳>`

## 验收标准（对应执行方案验收清单）

- [ ] `pip install -e .` 安装成功，`import sb_api / agents / skills` 可用
- [ ] sb_api 真实加载主项目 4 个模型（无 mock），加载失败有明确诊断
- [ ] 7 个 Agent 均继承 agent-teams-sdk 的 BaseAgent 基类，具备黑板读写能力
- [ ] 6 个 Skill 输入输出均通过 JSON Schema 校验（jsonschema 验证）
- [ ] src/demo.py 跑通端到端完整流程（Agent 协作 + Skill 校验 + 结果输出）
- [ ] pytest 全部通过且覆盖率 >80%（`coverage` 报告留档 .specs/02-goai-adapt/）
- [ ] 主项目 F:\SelfBrain 与框架 F:\agent-teams-sdk 零修改（git diff 为空）
- [ ] 所有文件带 @agent 身份指纹

## 时间线

- Wave 0（8.09）：骨架 + 规范文档（本变更）
- Wave 1（8.09）：sb_api 桥接层真实加载 4 模型
- Wave 2/3（8.10）：7 Agents + 6 Skills 实现
- Wave 4（8.11）：demo 完整流程
- Wave 5（8.11-12）：测试套件 >80% + Review/Audit
- Wave 6（8.13）：集成验收、PPT、提交准备
