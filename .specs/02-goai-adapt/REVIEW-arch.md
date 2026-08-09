# @agent: session-smart-copper | module: review/architecture | ts: 2026-08-09T13:06+08:00

# SelfBrain-GOAI 架构审查报告（R1-arch-review）

**审查时间**: 2026-08-09 13:06 CST
**审查范围**: Wave 1–4 产物（sb_api 桥接层 + 7 Agents + 6 Skills + demo）
**审查员**: R1-arch-review（session-260809-smart-copper）
**对照基线**: F:\agent-teams-sdk（agent_teams_sdk v0.1.0）、CHANGE-002 约束

---

## 总体结论：有条件通过

架构在分层方向、黑盒边界、框架继承三个核心维度上基本合规，可以支撑当前 Wave 5 测试与 Wave 6 提交。但存在 **1 个 P0 级问题**（双重黑板写入导致键名分裂）和 **5 个 P1 级问题**，需在测试阶段前修复 P0，P1 建议在 Wave 5 期间修复。

---

## 架构维度逐项评分

### 1. 分层边界 — 评分：4/5

**发现**：

| 层 | 依赖方向 | 状态 |
|---|---|---|
| `src/demo.py` | → agents, skills, sb_api, agent_teams_sdk | ✅ 合规 |
| `src/agents/*` | → sb_api, agent_teams_sdk | ✅ 合规 |
| `src/skills/*` | → agent_teams_sdk | ✅ 合规（零 sb_api 依赖） |
| `src/sb_api/*` | → model_loader（主项目）, Python stdlib | ✅ 合规 |

- agents 不直接 import model_loader ✅
- skills 不 import sb_api ✅
- agents 之间无互相 import ✅（docstring 中的用法示例不算运行时依赖）
- 依赖链严格单向：demo → agents/skills → sb_api → engine ✅

**扣分点**：

- `PolicyEnforcer.__init__` 通过参数注入 `engine`（SBEngine），而 `MemoryNavigator` 和 `CipherGenerator` 在内部自建 engine——同一层内存在两种获取引擎的模式，削弱了分层一致性。
- `guardian.py:_fuse_results` 在方法体内做 `from sb_api import create_engine`（late import），虽然不影响分层方向，但与 navigator/cipher/policy 的模块级 import 风格不一致。

**建议**：统一 Worker 获取 SBEngine 的方式——要么全部构造函数注入，要么全部内部惰性创建。推荐构造函数注入（更易测试）。

---

### 2. 接口一致性 — 评分：2/5

**发现**：

#### 2a. Worker3构造函数签名不统一

| Agent | 签名 | name 参数 | engine 来源 |
|---|---|---|---|
| PrivacyGuardian | `(name, team_room, workers)` | ✅ 可传 | 内部 fuse 时 late import |
| MemoryNavigator | `(name, team_room)` | ✅ 可传 | `__init__` 内 `create_engine()` |
| CipherGenerator | `(team_room)` | ❌ 硬编码 `_AGENT_ID` | 惰性属性 `self.engine` |
| DataCoordinator | `(team_room)` | ❌ 硬编码 `"G6-coordinator"` | 无（纯黑板操作） |
| PolicyEnforcer | `(team_room, engine, ...)` | ❌ 硬编码 `"G7-policy"` | 构造函数注入 |
| AuditLogger | `(name, team_room, ...)` | ✅ 可传 | 无（纯黑板操作） |
| Validator | `(name, team_room)` | ✅ 可传 | 无（纯黑板操作） |

#### 2b. 黑板键名分裂（**P0**）

SDK `WorkerAgent.execute()` 基类行为：

```python
def execute(self, task):
    result = self.do_work(task)
    self.team_room.write(f"{self.name}_result", result, updated_by=self.name)  # ← 自动写入
    return result
```

各 Worker 在 `do_work()` 中**手动**写入语义键（如 `navigator_result`），基类 `execute()` 又**自动**写入 `{name}_result`（如 `G4-navigator_result`）。

**结果**：每个 Worker 结果在黑板上存在**两份**，键名不同：

| Worker | do_work 手写键 | 基类自动写入键 | Guardian 读取键 |
|---|---|---|---|
| Navigator | `navigator_result` | `G4-navigator_result` | `navigator_result` |
| Cipher | `cipher_result` | `G5-cipher_result` | `cipher_result` |
| Coordinator | `coordinator_result` | `G6-coordinator_result` | `coordinator_result` |
| Policy | `policy_result` | `G7-policy_result` | `policy_result` |
| Audit | `audit_result` | `G8-audit_result` | `audit_result` |

两份写入可能导致数据不一致（如一方更新另一方未更新），且 Validator 的 `_EXPECTED_WORKER_KEYS` 列表包含 `guardian_result`（无 Worker 以此键写入），导致完整性核查永远报缺。

#### 2c. Envelope 结构不完全贯穿

| 组件 | 返回 status 值 | 符合约定？ |
|---|---|---|
| sb_api.engine | `"ok"` / `"pending"` / `"error"` | ✅ 基准 |
| Navigator do_work | 透传 engine.search → `"ok"` / `"error"` | ✅ |
| Cipher do_work | 透传 engine.cipher_analyze → `"pending"` / `"error"` | ✅ |
| **Coordinator do_work** | **`"coordinated"`** | ❌ 不符合约定 |
| **AuditLogger do_work** | **`"completed"`** / `"error"` | ❌ `"completed"` 不符合约定 |
| Policy do_work | `"ok"` / `"pending"` / `"error"` | ✅ |

**建议**：
1. **P0**：统一黑板键名约定。要么让 Guardian/Validator 读 `{name}_result`（基类约定），要么覆写 `execute()` 取消基类自动写入、统一使用语义键名。**推荐后者**——在 Worker 基类或各 Worker 中覆写 execute()，不调用 `super().execute()`，只保留 `do_work` 中的手写键。
2. P1：DataCoordinator 和 AuditLogger 的 `status` 值改为 `"ok"`。
3. P1：统一 Worker 构造函数签名 `(name, team_room, engine=None)`，engine 可选注入、缺省则内部创建。

---

### 3. 框架集成正确性 — 评分：3/5

**发现**：

#### 3a. CuratorAgent 继承

- ✅ `PrivacyGuardian(CuratorAgent)` 继承正确
- ✅ `evaluate_completeness` 抽象方法已实现
- ✅ `reconstruct_result` 已覆写（基类提供默认实现，覆写合理）
- ⚠️ Guardian 覆写了 `execute()`，但未调用 `super().execute()`——**丢失了基类的状态机管理**（`IDLE → RUNNING → COMPLETED`）。当前 Guardian 没有显式管理 `self.state`。
- ⚠️ Guardian 覆写了 `on_message()`，签名与基类一致 ✅

#### 3b. WorkerAgent 继承

- ✅ 所有 Worker 均继承 `WorkerAgent`，均实现了 `do_work`
- ⚠️ `CipherGenerator` 额外覆写了 `execute()`——注释说明是为了同时写入 `cipher_result` 和 `G5-cipher_result`，属于对 P0 问题的临时 workaround
- ⚠️ `DataCoordinator` 和 `AuditLogger` 覆写了 `on_message()`——但基类 `WorkerAgent.on_message()` 已有相同实现（`@{name}` 触发），**覆写是多余的**
- ⚠️ PolicyEnforcer 的 `do_work` 中 `raise ValueError(...)`——基类 execute 会捕获后写入黑板，但 error 传播路径不清晰

#### 3c. ValidatorAgent 继承

- ✅ `Validator(ValidatorAgent)` 继承正确
- ✅ `validate` 抽象方法已实现，返回 `ValidationResult` ✅
- ✅ 不调用 `super().execute()`，直接调用 `validate(blackboard)`，合理

#### 3d. BaseSkill 继承

- ✅ 6 个 Skill 均继承 `BaseSkill`，均有 `name`/`version`/`schema`
- ✅ 均实现了 `execute` 抽象方法
- ⚠️ `validate_input` 调用情况不一致：
  - PrivacyShield：**未调用** `validate_input`，手动做 `isinstance` 检查
  - MemoryProbe：调用了 ✅
  - DataFusion：调用了 ✅
  - AccessControl：调用了 ✅
  - AuditTrail：调用了 ✅
  - ResultVerify：调用了 ✅
- ⚠️ Skill execute 签名不一致（详见 §2）

**建议**：
1. P1：Guardian `execute()` 应调用 `super().execute()` 或手动管理 `self.state`。
2. P1：DataCoordinator/AuditLogger 删除多余的 `on_message` 覆写。
3. P1：PrivacyShield 应调用 `self.validate_input(text=text)` 做基类契约校验。

---

### 4. 依赖方向 — 评分：5/5

**发现**：

- 依赖链严格单向 ✅：`demo → agents/skills → sb_api → engine`
- 无循环依赖 ✅
- 无跨层直接引用 ✅
- `pyproject.toml` 的 `[tool.setuptools.packages.find]` 正确限定 `sb_api*`, `agents*`, `skills*` ✅

**唯一=唯一关注点（P2）**：`pyproject.toml` 将 `torch>=2.0` 和 `transformers>=4.30` 声明为**运行时**依赖。当前 stub 代码从未 import 这两个包（sb_api 使用惰性加载）。对于Docker/CI 环境这会导致不必要的安装时间和镜像体积。

**建议**：P2：将 `torch`/`transformers` 移入 `[project.optional-dependencies]` 的 `ml` 组，运行时由 sb_api 在真实模式下提示安装。

---

### 5. 可扩展性 — 评分：3/5

**发现**：

- 新增 Worker：创建文件 → 继承 WorkerAgent → 实现 do_work ✅ 流程清晰
- 新增 Skill：创建文件 → 继承 BaseSkill → 实现 execute ✅ 流程清晰
- **P1**：`agents/__init__.py` 和 `skills/__init__.py` 仅为占位 docstring，无注册/发现机制——新增 Agent/Skill 后需手动修改 `demo.py` 和 `guardian.py` 的 `DEFAULT_WORKERS`
- **P2**：SDK 提供 `PluginManager`（自动发现 + entry_points），但当前未使用
- **P1**：`DEFAULT_WORKERS` 硬编码在 Guardian 中——新增 Worker 需改 Guardian 代码，违反开闭原则

**建议**：
1. P1：在 `agents/__init__.py` 中建立 `WORKER_REGISTRY: Dict[str, Type[WorkerAgent]]`，Guardian 从注册表读取 workers 列表而非硬编码。
2. P2：考虑使用 SDK 的 PluginManager 做 Skill 自动发现。

---

### 6. 黑盒边界 — 评分：5/5

**发现**：

- `sb_api/loader.py`：唯一 import model_loader 的入口 ✅，且为惰性导入
- **零写入 F:\SelfBrain**：grep 检查确认所有对 `F:\SelfBrain` 的引用均为只读路径或文档注释 ✅
- `SRC_PATH` 可通过环境变量 `SB_SELFBRAIN_SRC` 覆盖 ✅
- 框架源码零修改 ✅
- 主项目零修改 ✅

**唯一关注点（P2）**：`loader.py`7通过 `sys.path.insert(0, ...)` 注入主项目源码路径。这种全局副作用在多实例/测试隔离场景下可能产生干扰。

**建议**：P2：考虑在 `ensure_src_path()` 中增加幂等校验注释和测试夹具清理逻辑，或在 SBEngine 级别用 `importlib` 替代 `sys.path` 注入。

---

## 问题清单

### P0（必须修）

| # | 问题 | 位置 | 影响 | 修复转派 |
|---|---|---|---|---|
| P0-1 | **双重黑板写入导致键名分裂**：Worker do_work 写语义键（`navigator_result`），基类 execute 写 `{name}_result`（`G4-navigator_result`），两份数据可能不一致；Validator `_EXPECTED_WORKER_KEYS` 包含 `guardian_result` 但无人写入 | `src/agents/*.py` 全部 Worker + `src/agents/validator.py:22-28` | 黑板数据冗余、完整性核查误报、后续维护者困惑 | 转 G3-G9 各 Worker Agent（统一覆写 execute 或统一键名策略）+ G9-validator（更新 _EXPECTED_WORKER_KEYS） |

### P1（建议修）

| # | 问题 | 位置 | 影响 | 修复转派 |
|---|---|---|---|---|
| P1-1 | **Worker 构造函数签名不一致**：有的取 name 有的硬编码，engine 获取方式不统一 | `cipher.py:63`, `coordinator.py:29`, `policy.py:45-55` | 新增 Worker 时无范式可循，测试夹具编写困难 | 转 G5-cipher, G6-coordinator, G7-policy |
| P1-2 | **CipherGenerator 覆写 execute 为临时 workaround**：同时写 `cipher_result` 和 `G5-cipher_result` | `cipher.py:155-170` | P0-1 修复后此 workaround 应同步清理 | 转 G5-cipher |
| P1-3 | **envelope status 值不统一**：Coordinator 用 `"coordinated"`，AuditLogger 用 `"completed"`，不符合 `"ok"/"pending"/"error"` 约定 | `coordinator.py:87`, `audit.py:195` | 下游消费方（Validator/Skill）对 status 判断逻辑可能遗漏 | 转 G6-coordinator, G8-audit |
| P1-4 | **Skill execute 签名不一致**：PrivacyShield 取 `text` 位置参数，其余取 `input` dict | `privacy_shield.py:188` | 无法用统一接口调用所有 Skill | 转 G10-shield |
| P1-5 | **Guardian DEFAULT_WORKERS 硬编码** + agents/skills 无注册/发现 | `guardian.py:33-38`, `agents/__init__.py`, `skills/__init__.py` | 新增 Worker 需改 Guardian 代码，违反开闭原则 | 转 G3-guardian + G1-skeleton |

### P2（可选）

| # | 问题 | 位置 | 影响 | 修复转派 |
|---|---|---|---|---|
| P2-1 | torch/transformers 声明为运行时依赖（~4GB），但 stub 阶段无需安装 | `pyproject.toml:13-14` | CI/CD 镜像体积和安装时间浪费 | 转 G1-skeleton |
| P2-2 | Guardian._fuse_results 方法体内 late import sb_api | `guardian.py:322` | 风格不一致（其余 Worker 模块级 import） | 转 G3-guardian |
| P2-3 | sys.path 注入方式在多实例/测试隔离下可能干扰 | `sb_api/loader.py:89-92` | 测试夹具清理复杂度 | 转 G2-sbapi |
| P2-4 | DataCoordinator/AuditLogger 多余覆写 on_message（基类已有相同行为） | `coordinator.py:36-39`, `audit.py:227-232` | 代码冗余 | 转 G6-coordinator, G8-audit |
| P2-5 | Guardian execute 未调用 super().execute()，丢失基类状态机管理 | `guardian.py:261-268` | self.state 始终 IDLE，get_state() 不准确 | 转 G3-guardian |
| P2-6 | PrivacyShield 未调用基类 validate_input | `privacy_shield.py:188-210` | 基类契约未完全履行 | 转 G10-shield |
| P2-7 | Validator._EXPECTED_WORKER_KEYS 包含 guardian_result 但无 Worker 以此键写入 | `validator.py:23-29` | 完整性核查永远报缺 | 转 G9-validator |

---

## 修复优先级建议

1. **P0-1**（本审查最关键发现）：建议总调度在 Wave 5 测试开始前统一修复。策略选择：
   - **方案 A**（推荐）：各 Worker 覆写 `execute()`，只保留 `do_work` 中的语义键写入，取消基类自动写入。修改量：5 个 Worker 各加 3 行。
   - **方案 B**：Guardian/Validator 统一读取 `{name}_result` 格式的键。修改量：Guardian evaluate_completeness + Validator _EXPECTED_WORKER_KEYS。
   - **方案 A 优势**：语义键名（`navigator_result`）比实例键名（`G4-navigator_result`）更稳定、更可读。

2. **P1-1~P1-5**：建议在 Wave 5 期间由各归属 Agent 修复，可在测试编写过程中顺带处理。

3. **P2-1**（torch 依赖）：建议在 Wave 6 打包提交前处理，避免 Docker 镜像过大。

---

## 架构健康度雷达

```
        分层边界 ●●●●○ 4/5
            ╱         ╲
  依赖方向 ●●●●● 5/5     接口一致 ●●○○○ 2/5
            ╲         ╱
        黑盒边界 ●●●●● 5/5

     框架集成 ●●●○○ 3/5     可扩展性 ●●●○○ 3/5
```

**综合评分**：3.7 / 5（加权：分层 20% + 接口 25% + 框架 20% + 依赖 15% + 扩展 10% + 黑盒 10%）

---

*报告结束 · R1-arch-review · session-260809-smart-copper · 2026-08-09T13:06+08:00*
