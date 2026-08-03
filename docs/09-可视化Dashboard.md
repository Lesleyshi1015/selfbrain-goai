# 第9章：可视化Dashboard — Audit Logger Agent 可视化前端

**版本**: v2.0  
**更新日期**: 2026-08-03  
**架构定位**: 7-Agent 协同体系 → Audit Logger Worker → AuditTrail Skill → **Dashboard（可视化层）**

---

## 目录

- [9.0 架构定位：Dashboard 在 7-Agent 体系中的角色](#90-架构定位dashboard-在-7-agent-体系中的角色)
- [9.1 四层安全监控](#91-四层安全监控)
- [9.2 实时密码本状态展示](#92-实时密码本状态展示)
- [9.3 权限矩阵可视化](#93-权限矩阵可视化)
- [9.4 审计日志查看器](#94-审计日志查看器)
- [9.5 攻击模拟器（7种场景）](#95-攻击模拟器7种场景)
- [9.6 导出安全报告（PDF）](#96-导出安全报告pdf)
- [9.7 UI/UX设计规范](#97-uiux设计规范)
- [9.8 前端代码示例](#98-前端代码示例)
- [9.9 开源/闭源边界矩阵](#99-开源闭源边界矩阵)
- [9.10 黑板数据流转模型](#910-黑板数据流转模型)

---

## 9.0 架构定位：Dashboard 在 7-Agent 体系中的角色

### 9.0.1 AgentTeams 全景

```mermaid
graph TB
    subgraph "用户 / 外部系统"
        U[用户请求]
    end

    subgraph "AgentTeams 协同层"
        PG[Privacy Guardian<br/>Team Leader]
        MN[Memory Navigator<br/>Worker L1-L3]
        CG[Cipher Generator<br/>Worker]
        DC[Data Coordinator<br/>Worker]
        PE[Policy Enforcer<br/>Worker]
        AL[Audit Logger<br/>Worker ⭐本章主角]
        VD[Validator<br/>Worker]
    end

    subgraph "共享黑板 Blackboard"
        BB[Team Room + 共享数据]
    end

    subgraph "Skill 层 Schema+Wrapper+SDK"
        MP[MemoryProbe]
        PS[PrivacyShield]
        DF[DataFusion]
        AC[AccessControl]
        AT[AuditTrail ⭐]
        RV[ResultVerify]
    end

    subgraph "Dashboard 可视化层 本章"
        DASH[SelfBrain Dashboard<br/>四层安全监控 + 攻击模拟器]
    end

    U --> PG
    PG --> BB
    BB --> MN
    BB --> CG
    BB --> DC
    BB --> PE
    BB --> AL
    BB --> VD
    AL --> AT
    AT --> DASH
    MN --> MP
    CG --> PS
    DC --> DF
    PE --> AC
    VD --> RV
```

### 9.0.2 Audit Logger Agent 职责

| 属性 | 说明 |
|------|------|
| **Agent 名称** | Audit Logger |
| **角色** | Worker（7-Agent 中的第 5 个 Worker） |
| **核心职责** | 审计日志记录 + 证据链生成 + 安全合规报告 |
| **使用的 Skill** | AuditTrail（Schema + Wrapper + SDK 三层） |
| **输出产物** | 结构化审计日志 JSON → 由 Dashboard 可视化渲染 |
| **黑板交互** | 从黑板读取其他 Agent 的操作事件，将审计结果写回黑板 |

### 9.0.3 AuditTrail Skill 三层架构

AuditTrail Skill 采用 **Schema → Wrapper → SDK** 三层设计，是 Dashboard 的数据来源：

```
┌─────────────────────────────────────────────────────────────────┐
│                      AuditTrail Skill                            │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ 📗 Schema (开源)  │  │ 📙 Wrapper (开源) │  │ 🔒 SDK (闭源) │ │
│  │                  │  │                  │  │               │ │
│  │ AuditEntry.json  │  │ audit_trail.py   │  │ audit_core.so │ │
│  │  - id            │  │  - validate()    │  │  - 审计规则引擎│ │
│  │  - timestamp     │  │  - write_log()   │  │  - 异常检测算法│ │
│  │  - actor         │  │  - query()       │  │  - 合规评分算法│ │
│  │  - action        │  │  - export()      │  │  - 证据链校验  │ │
│  │  - result        │  │  - 参数验证       │  │  - 风险评估    │ │
│  │  - context       │  │  - 错误处理       │  │               │ │
│  │  - evidence      │  │  - 类型检查       │  │ 以 .so/.dll   │ │
│  │                  │  │                  │  │ 二进制发布     │ │
│  │ 格式规范          │  │ 薄封装层          │  │ 核心算法不可见 │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│         │                       │                     │          │
│         ▼                       ▼                     ▼          │
│    定义日志格式           验证+调用SDK           执行核心逻辑      │
│    (JSON Schema)         (Python薄层)           (闭源黑盒)       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Dashboard 可视化 │  ← 本章内容
                    │  (前端渲染层)     │
                    └──────────────────┘
```

**关键设计决策**：

| 决策 | 选择 | 理由 |
|------|------|------|
| Schema 开源 | ✅ AuditEntry JSON Schema | 社区可复用审计日志格式 |
| Wrapper 开源 | ✅ audit_trail.py 薄封装 | 透明调用逻辑，便于集成 |
| SDK 闭源 | ✅ audit_core.so | 保护审计规则引擎和异常检测算法 |
| Dashboard 开源 | ✅ React 前端 | UI 层不含核心算法，可开源 |

### 9.0.4 数据流：从 Agent 操作到 Dashboard 可视化

```mermaid
sequenceDiagram
    participant U as 用户
    participant PG as Privacy Guardian
    participant BB as 共享黑板
    participant AL as Audit Logger
    participant AT as AuditTrail Skill
    participant SDK as Core SDK 闭源
    participant DB as Dashboard

    U->>PG: 发起请求
    PG->>BB: 写入任务 task_type + user_query
    BB->>AL: 读取其他Agent操作事件
    AL->>AT: 调用 AuditTrail.write(event)
    AT->>AT: Wrapper 验证参数 开源
    AT->>SDK: 调用审计规则引擎 闭源
    SDK-->>AT: 返回审计结果 + 证据链
    AT-->>AL: 返回 AuditEntry JSON
    AL->>BB: 写回审计结果到黑板
    BB-->>DB: WebSocket 推送审计事件
    DB->>DB: 四层Dashboard渲染
    DB-->>U: 实时可视化展示
```

---

---

## 9.1 四层安全监控

### 9.1.1 概述

Dashboard采用**四层安全监控架构**，每一层对应一个独立的安全维度，每层的数据源来自不同的 Agent Worker。这是Dashboard的核心设计，将安全监控分解为四个可独立查看、交叉关联的维度：

| 层次 | 名称 | 核心指标 | 更新频率 | 数据来源 Agent |
|------|------|----------|----------|----------------|
| **Layer 1** | 密码状态层 | 活跃密码、过期倒计时 | 实时 | **Cipher Generator** Worker |
| **Layer 2** | 权限矩阵层 | 五层访问热力图 | 每次操作后 | **Policy Enforcer** Worker |
| **Layer 3** | 数据保存层 | 加密状态、存储分布 | 每日汇总 | **Data Coordinator** Worker |
| **Layer 4** | 审计日志层 | 完整操作记录 | 实时 | **Audit Logger** Worker |

```mermaid
graph TB
    subgraph "四层安全监控架构"
        L1["Layer 1: 密码状态<br/>Cipher Generator Agent"]
        L2["Layer 2: 权限矩阵<br/>Policy Enforcer Agent"]
        L3["Layer 3: 数据保存<br/>Data Coordinator Agent"]
        L4["Layer 4: 审计日志<br/>Audit Logger Agent"]
    end

    SK["AuditTrail Skill<br/>Schema + Wrapper + SDK"] --> L4
    L1 --> DASH["Dashboard 前端"]
    L2 --> DASH
    L3 --> DASH
    L4 --> DASH
    WS["WebSocket Server"] --> DASH
    L1 --> WS
    L2 --> WS
    L3 --> WS
    L4 --> WS
```

### 9.1.2 Layer 1: 密码状态监控（Cipher Generator Agent 输出）

**功能**：实时显示密码本中所有密码的状态，包括生命周期、使用状态和访问统计。

**数据来源**：Cipher Generator Agent 生成密码后，通过黑板模式将密码事件写入共享黑板，Audit Logger Agent 读取并通过 AuditTrail Skill 的 Schema 层输出结构化数据。

**UI设计**：

```
┌──────────────────────────────────────────────────────────────┐
│ 🔑 Layer 1: 密码状态监控                          [自动刷新] │
│ 数据源: Cipher Generator Agent → Blackboard → AuditTrail     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  活跃密码列表 (卡片布局):                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ L1_USER_B5E8│  │ L1_USER_C3D9│  │ L2_USER_A1F2│         │
│  │ ████████░░  │  │ ██████░░░░  │  │ ████░░░░░░  │         │
│  │ 剩余: 3m28s │  │ 剩余: 2m15s │  │ 剩余: 1m02s │         │
│  │ 状态: 使用中│  │ 状态: 待使用│  │ 状态: 使用中│         │
│  │ Agent: CG   │  │ Agent: CG   │  │ Agent: CG   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
│  统计摘要:                                                   │
│  活跃: 12    今日过期: 47    总生成: 1,847    平均寿命: 4m32s│
└──────────────────────────────────────────────────────────────┘
```

### 9.1.3 Layer 2: 权限矩阵监控（Policy Enforcer Agent 输出）

**功能**：以热力图形式展示五个存储层（L1/L2/L2.5/L2.7/L3）对各AI模型的访问情况。

**数据来源**：Policy Enforcer Agent 在每次权限验证后，将结果写入黑板，Audit Logger Agent 通过 AuditTrail Schema 层记录。

**热力图数据结构**（AuditTrail Schema 定义，开源）：

```typescript
interface HeatmapCell {
  layer: string;        // L1, L2, L2.5, L2.7, L3
  model: string;        // GPT-4, Claude, Gemini, SelfBrain
  accessCount: number;
  percentage: number;
  intensity: number;    // 0-1 热力强度
  color: string;
  sourceAgent: string;  // 数据来源Agent标识
}
```

### 9.1.4 Layer 3: 数据保存监控（Data Coordinator Agent 输出）

**功能**：展示各层数据的加密状态、存储分布和完整性校验结果。

**数据来源**：Data Coordinator Agent 执行数据操作后，将存储事件写入黑板。

**加密状态矩阵**：

```
┌──────────────────────────────────────────────────────┐
│ 🔒 Layer 3: 数据保存状态监控                         │
│ 数据源: Data Coordinator Agent → Blackboard → AuditTrail│
├──────────────────────────────────────────────────────┤
│                                                      │
│  加密覆盖: ██████████████████████████████ 100%       │
│                                                      │
│  存储分布:                                          │
│  L1 (明文+加密):   ████████████░░░░░░░░  12,847条   │
│  L2 (加密):        ████████░░░░░░░░░░░░   8,234条   │
│  L2.5 (加密):      ████░░░░░░░░░░░░░░░░   4,127条   │
│  L2.7 (加密):      ██░░░░░░░░░░░░░░░░░░   2,048条   │
│  L3 (加密):        █░░░░░░░░░░░░░░░░░░░░   1,024条   │
│                                                      │
│  完整性校验: ✅ 全部通过 (最近: 10分钟前)           │
└──────────────────────────────────────────────────────┘
```

### 9.1.5 Layer 4: 审计日志监控（Audit Logger Agent + AuditTrail Skill 输出）

**功能**：显示审计事件流，包括实时滚动的审计日志、合规检查和异常告警。

**数据来源**：Audit Logger Agent 通过 AuditTrail Skill（三层架构：Schema → Wrapper → SDK）处理后输出。

**三层处理流水线**：

```mermaid
graph LR
    EVENT["Agent 操作事件"] --> SCHEMA["Schema 层<br/>✅ 开源<br/>JSON格式验证"]
    SCHEMA --> WRAPPER["Wrapper 层<br/>✅ 开源<br/>参数校验+错误处理"]
    WRAPPER --> SDK["SDK 层<br/>🔒 闭源<br/>审计规则+异常检测"]
    SDK --> OUTPUT["结构化审计数据"]
    OUTPUT --> BB["写入黑板"]
    BB --> DASH["Dashboard 展示"]
```

**审计日志实时视图**：

```
┌──────────────────────────────────────────────────────────────┐
│ 📋 Layer 4: 审计日志实时流                   [过滤] [导出]  │
│ Audit Logger Agent → AuditTrail Skill (Schema+Wrapper+SDK)   │
├──────────────────────────────────────────────────────────────┤
│ 14:23:15.342 │ GPT-4    │ read  │ L1 │ allowed │ 45ms       │
│ 14:23:15.388 │ Claude   │ read  │ L1 │ allowed │ 52ms       │
│ 14:23:16.001 │ System   │ write │ L3 │ allowed │ 12ms       │
│ 14:23:16.045 │ Gemini   │ read  │ L2.7│ denied │ 38ms       │
│ 14:23:16.102 │ System   │ read  │ L3 │ allowed │ 8ms        │
│ 14:23:16.156 │ GPT-4    │ read  │ L2 │ allowed │ 67ms       │
└──────────────────────────────────────────────────────────────┘
```

---

---

## 9.2 实时密码本状态展示

### 9.2.1 活跃密码列表

密码状态是Layer 1的核心展示。Dashboard以**卡片式布局**展示密码本中每个活跃密码的详细状态。**数据由 Cipher Generator Agent 生成，通过黑板传递给 Audit Logger Agent，再经 AuditTrail Skill Schema 层输出。**

**密码卡片组件设计**：

每个密码卡片包含以下信息：

| 字段 | 说明 | 来源 |
|------|------|------|
| 密码标识 | 如 `L1_USER_B5E8_T1722240900_S7A3B` | Cipher Generator |
| 层级前缀 | `L1` / `L2` / `L2.5` / `L2.7` / `L3` | Cipher Generator |
| 生成时间 | Unix时间戳（嵌入密码中） | Cipher Generator |
| 会话ID | `S7A3B` 等5字符会话标识 | Cipher Generator |
| 剩余寿命 | 进度条 + 倒计时（秒级） | Dashboard 计算 |
| 状态 | 活跃 / 已使用 / 已过期 / 已销毁 | Audit Logger |
| 使用记录 | 访问次数、最近访问Agent | Audit Logger |

### 9.2.2 密码到期倒计时

**倒计时实现**（前端计算，无需 Agent 参与）：

```typescript
interface PasswordCountdown {
  passwordId: string;
  createdAt: number;    // Unix timestamp
  expiresAt: number;    // createdAt + 300s (5min)
  remaining: number;    // 剩余秒数
  percentage: number;   // 剩余百分比
  status: 'active' | 'expiring' | 'expired';
}

// 倒计时颜色方案
function getCountdownColor(remaining: number): string {
  if (remaining > 240) return '#4CAF50';  // 绿色: >4分钟
  if (remaining > 120) return '#FF9800';  // 橙色: >2分钟
  if (remaining > 60)  return '#FF5722';  // 深橙: >1分钟
  return '#D32F2F';                       // 红色: <1分钟
}
```

### 9.2.3 密码使用状态图（状态机）

```mermaid
stateDiagram-v2
    [*] --> 活跃: Cipher Generator 生成
    活跃 --> 使用中: Agent 首次使用
    使用中 --> 使用中: 后续使用
    活跃 --> 已过期: 超过5分钟
    使用中 --> 已过期: 超过5分钟
    活跃 --> 已销毁: 用户手动销毁
    使用中 --> 已销毁: 用户手动销毁
    已过期 --> [*]: 自动清理
    已销毁 --> [*]: 立即清理
```

### 9.2.4 WebSocket实时推送机制

**服务端推送**（Python，Audit Logger Agent 调用）：

```python
import asyncio
import websockets
import json

class DashboardWebSocketServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.channels = {
            'passwords': set(),
            'permissions': set(),
            'audit': set(),
            'alerts': set(),
        }

    async def handler(self, websocket):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                if data.get('type') == 'subscribe':
                    for ch in data.get('channels', []):
                        if ch in self.channels:
                            self.channels[ch].add(websocket)
                elif data.get('type') == 'heartbeat':
                    await websocket.send(json.dumps({'type': 'heartbeat', 'ts': __import__('time').time()}))
        finally:
            self.clients.discard(websocket)
            for ch_set in self.channels.values():
                ch_set.discard(websocket)

    async def broadcast(self, channel, event, data):
        message = json.dumps({
            'type': 'event',
            'channel': channel,
            'event': event,
            'data': data,
            'timestamp': __import__('time').time(),
        })
        targets = self.channels.get(channel, set())
        if targets:
            await asyncio.gather(
                *[client.send(message) for client in targets],
                return_exceptions=True,
            )

    async def start(self):
        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()
```

---

## 9.3 权限矩阵可视化

### 9.3.1 Memory Palace五层访问热力图

热力图是权限可视化的核心组件，直观展示各层级的访问频率和分布。**数据源为 Policy Enforcer Agent 通过 AccessControl Skill 输出的权限验证结果**。

**热力图配色方案**：

| 访问频率 | 颜色 | Hex值 | 说明 |
|----------|------|-------|------|
| 0% (无访问) | 浅灰 | `#F5F5F5` | 无数据 |
| 1-20% | 浅绿 | `#C8E6C9` | 低频 |
| 21-40% | 绿色 | `#81C784` | 正常 |
| 41-60% | 黄色 | `#FFF176` | 中频 |
| 61-80% | 橙色 | `#FFB74D` | 高频 |
| 81-100% | 红色 | `#EF5350` | 极高频 |

**热力图矩阵示例**：

```
              GPT-4     Claude    Gemini    SelfBrain
         +----------+----------+----------+----------+
    L1   | 高频87%  | 中频45%  | 正常32%  | 极高频95%|
         +----------+----------+----------+----------+
    L2   | 正常     | 高频     | 低频     | 中频     |
         +----------+----------+----------+----------+
    L2.5 | 低频     | 正常     | 低频     | 中频     |
         +----------+----------+----------+----------+
    L2.7 | 禁止     | 禁止     | 禁止     | 正常     |
         +----------+----------+----------+----------+
    L3   | 禁止     | 禁止     | 禁止     | 低频     |
         +----------+----------+----------+----------+
```

### 9.3.2 各模型的访问记录时间线

```mermaid
gantt
    title 模型访问记录时间线（今日）
    dateFormat HH:mm
    axisFormat %H:%M

    section GPT-4
    L1 查询批次1      :active, g1, 09:00, 09:45
    L1 查询批次2      :active, g2, 10:30, 11:00

    section Claude
    L1 查询           :active, c1, 09:15, 09:30
    L1+L2 对比分析    :active, c2, 11:00, 11:45

    section SelfBrain
    L1-L3 完整访问    :crit, s1, 08:00, 18:00
    L2.7 预测分析     :crit, s2, 10:00, 10:30
```

### 9.3.3 权限分配历史图表

| 图表 | X轴 | Y轴 | 用途 | 数据Agent |
|------|-----|-----|------|-----------|
| 令牌签发趋势 | 时间（小时） | 签发数量 | 监控令牌生成速率 | Cipher Generator |
| 层级分布饼图 | - | 各层级占比 | 了解权限使用偏好 | Policy Enforcer |
| 模型权限分布 | 模型名称 | 平均授权层级 | 评估各模型权限需求 | Policy Enforcer |
| 令牌过期率 | 时间（天） | 过期/总签发 | 评估令牌有效期合理性 | Audit Logger |

### 9.3.4 异常访问告警

**告警级别定义**（异常检测规则来自 SDK 闭源层，告警记录由 Audit Logger Agent 生成）：

| 级别 | 颜色 | 触发条件 | 响应要求 | 记录Agent |
|------|------|----------|----------|-----------|
| Critical | 红色 | 外部模型尝试访问L2.7/L3 | 立即阻止 | Audit Logger |
| High | 橙色 | 同一模型短时间内大量请求 | 5分钟内处理 | Audit Logger |
| Medium | 黄色 | 非典型访问模式 | 30分钟内查看 | Audit Logger |
| Low | 蓝色 | 令牌接近过期仍在使用 | 仅记录 | Audit Logger |

---


---

## 9.4 审计日志查看器

> **Agent**: Audit Logger | **Skill**: AuditTrail (Schema + Wrapper + SDK)
> **开源边界**: 日志格式 Schema 开源，审计规则引擎 SDK 闭源

### 9.4.1 完整操作日志表格

审计日志记录SelfBrain系统的每一次安全相关操作，是合规审计的基础数据。**所有审计记录由 Audit Logger Agent 通过 AuditTrail Skill 生成**。

**日志条目数据结构**（AuditTrail Schema - 开源）：

```typescript
interface AuditLogEntry {
  id: string;                // 唯一标识 UUID
  timestamp: number;         // Unix timestamp (ms)
  formattedTime: string;     // "2026-08-03 14:23:15.342"

  actor: {
    type: 'model' | 'user' | 'system' | 'agent';
    id: string;              // "GPT-4" / "user_123" / "scheduler"
    agentRole?: string;      // Agent 角色标识
    sessionId?: string;
    ipAddress?: string;
  };

  action: {
    type: 'read' | 'write' | 'search' | 'generate_password' | 'validate_token' | 'revoke_token';
    target: string;
    layer?: string;          // "L1" / "L2" / "L2.5" / "L2.7" / "L3"
    dataType?: string;       // "AMOUNT" / "PII" / "MEDICAL"
    skillUsed?: string;      // 使用的 Skill 标识
  };

  result: {
    status: 'allowed' | 'denied' | 'error';
    reason?: string;
    duration_ms?: number;
  };

  context: {
    taskId?: string;
    tokenId?: string;
    passwordId?: string;
    correlationId?: string;
    blackboardState?: string;
  };

  evidence: {
    hash: string;            // 证据哈希（SDK 生成 - 闭源）
    chainId: string;         // 证据链ID（SDK 生成 - 闭源）
    integrity: boolean;      // 完整性校验（SDK 验证 - 闭源）
  };
}
```

**日志表格列定义**：

| 列名 | 字段 | 宽度 | 可排序 | 可过滤 |
|------|------|------|--------|--------|
| 时间 | timestamp | 180px | Yes | 时间范围 |
| 操作者 | actor.id | 120px | Yes | 多选 |
| 类型 | actor.type | 80px | Yes | 下拉 |
| 操作 | action.type | 100px | Yes | 多选 |
| 层级 | action.layer | 60px | Yes | 多选 |
| 目标 | action.target | 200px | No | 搜索 |
| 结果 | result.status | 80px | Yes | 下拉 |
| 原因 | result.reason | 200px | No | 搜索 |
| 耗时 | result.duration_ms | 80px | Yes | 范围 |
| Agent | actor.agentRole | 100px | Yes | 多选 |

### 9.4.2 高级过滤和搜索

```typescript
interface AuditFilter {
  timeRange?: {
    start: string;
    end: string;
    preset?: 'last_hour' | 'today' | 'yesterday' | 'last_7_days' | 'last_30_days' | 'custom';
  };
  actors?: {
    ids?: string[];
    types?: ('model' | 'user' | 'system' | 'agent')[];
    agentRoles?: string[];
  };
  actions?: {
    types?: string[];
    layers?: string[];
    dataTypes?: string[];
    skills?: string[];
  };
  results?: {
    statuses?: ('allowed' | 'denied' | 'error')[];
  };
  search?: string;
  sort?: { field: string; order: 'asc' | 'desc' };
  pagination?: { page: number; pageSize: number };
}
```

### 9.4.3 导出功能

| 格式 | 文件类型 | 用途 | 包含内容 |
|------|----------|------|----------|
| CSV | `.csv` | 数据分析/导入Excel | 日志明细 |
| JSON | `.json` | 程序化处理/API集成 | 完整结构化数据 |
| Excel | `.xlsx` | 管理层报告 | 日志 + 统计图表 |
| PDF | `.pdf` | 正式合规报告 | 日志 + 图表 + 摘要 |

### 9.4.4 合规报告自动生成

```python
class ComplianceReportGenerator:
    """合规报告生成器（SDK 闭源算法，此处为接口定义）"""

    def generate_report(self, entries, standard='GDPR'):
        return {
            'report_info': {
                'standard': standard,
                'total_entries': len(entries),
                'architecture': '7-Agent AgentTeams',
                'audit_skill': 'AuditTrail (Schema+Wrapper+SDK)',
            },
            'executive_summary': {
                'total_operations': len(entries),
                'allowed_operations': self._count_status(entries, 'allowed'),
                'denied_operations': self._count_status(entries, 'denied'),
                'compliance_score': self._calculate_score(entries),
                'agents_involved': self._get_agents(entries),
            },
            'access_statistics': {
                'by_layer': self._group_by_field(entries, 'layer'),
                'by_model': self._group_by_field(entries, 'model'),
                'by_agent': self._group_by_agent(entries),
                'by_skill': self._group_by_skill(entries),
            },
            'security_events': {
                'unauthorized_attempts': [
                    e for e in entries
                    if e.get('result', {}).get('status') == 'denied'
                ],
            },
            'data_protection': {
                'encryption_coverage': '100%',
                'l3_exclusivity': self._verify_l3_exclusivity(entries),
            },
            'recommendations': self._generate_recommendations(entries),
        }
```

---

## 9.5 攻击模拟器（7种场景）

> **Agent**: Audit Logger + Validator | **Skill**: AuditTrail + ResultVerify
> **说明**: 攻击模拟结果由 Audit Logger 记录，Validator 核查一致性

### 9.5.1 攻击模拟器总体设计

攻击模拟器允许管理员在安全环境中模拟7种攻击场景，验证SelfBrain防御机制的有效性。所有攻击结果由 Audit Logger Agent 记录，Validator Agent 核查一致性。

### 9.5.2 场景1：密码截获攻击

**攻击描述**：攻击者在网络传输中截获动态密码，尝试使用该密码访问数据。

**防御机制**：会话级隔离 + 5分钟过期

```mermaid
sequenceDiagram
    participant Att as Attacker
    participant SB as SelfBrain
    participant CB as PasswordBook

    SB->>CB: Store L1_C3D9_T..._S7A3B
    SB-->>Att: Password in transit
    Att->>SB: Use intercepted password
    SB->>CB: Verify: session mismatch
    SB-->>Att: Denied: session mismatch
```

### 9.5.3 场景2：重放攻击

**防御机制**：一次一密 + 5分钟自动过期

### 9.5.4 场景3：权限越界攻击

**防御机制**：分层前缀验证 + SelfBrain独占访问

### 9.5.5 场景4：多模型联合攻击

**防御机制**：会话隔离 + 密码不可组合

### 9.5.6 场景5：暴力破解攻击

**防御机制**：5分钟自动过期 + 会话绑定 + 速率限制

### 9.5.7 场景6：侧信道攻击

**防御机制**：恒定时间验证 + 统一错误消息

### 9.5.8 场景7：时序攻击

**防御机制**：恒定时间字符串比较 + 随机延迟

### 9.5.9 攻击模拟结果汇总

| 场景 | 攻击类型 | 结果 | 防御机制 | 评分 |
|------|----------|------|----------|------|
| 1 | 密码截获 | BLOCKED | 会话级隔离 | 100 |
| 2 | 重放攻击 | BLOCKED | 一次一密 + 过期 | 100 |
| 3 | 权限越界 | BLOCKED | 分层前缀 + L3独占 | 100 |
| 4 | 联合攻击 | BLOCKED | 会话隔离 + 不可组合 | 100 |
| 5 | 暴力破解 | BLOCKED | 过期 + 速率限制 | 100 |
| 6 | 侧信道攻击 | BLOCKED | 恒定时间 + 统一消息 | 100 |
| 7 | 时序攻击 | BLOCKED | 恒定比较 + 随机延迟 | 100 |
| **合计** | **7种** | **7/7** | - | **99/100** |

---

## 9.6 导出安全报告（PDF）

> **Agent**: Audit Logger | **Skill**: AuditTrail
> **说明**: PDF报告由 Audit Logger Agent 调用 AuditTrail Skill 的 export() 方法生成

### 9.6.1 自动生成PDF报告

| 触发方式 | 说明 | 场景 |
|----------|------|------|
| 手动触发 | Dashboard点击"生成报告" | 临时审计 |
| 定时触发 | Cron定时任务 | 例行合规 |
| 事件触发 | 安全事件后自动生成 | 事故响应 |
| API触发 | REST API调用 | 自动化流水线 |

### 9.6.2 报告内容结构（8个章节）

1. 执行摘要 (Executive Summary)
2. 安全评分概览 (Security Score Overview)
3. 密码系统统计 (Password System Statistics)
4. 权限访问分析 (Permission Access Analysis)
5. 安全事件清单 (Security Incidents)
6. 攻击模拟结果 (Attack Simulation Results)
7. 合规检查清单 (Compliance Checklist)
8. 改进建议 (Recommendations)

### 9.6.3 合规审计材料格式（GDPR）

| 检查项 | 要求 | SelfBrain状态 | 证据 |
|--------|------|---------------|------|
| 数据加密 | 静态数据加密 | AES-256 | 加密状态矩阵 |
| 传输安全 | TLS加密传输 | TLS 1.3 | 网络配置记录 |
| 访问控制 | 最小权限原则 | 动态令牌 | 权限分配日志 |
| 数据隔离 | 第三方数据隔离 | L3独占 | 访问记录 |
| 审计日志 | 完整操作记录 | 全量日志 | AuditTrail Schema |
| 数据删除 | 右被遗忘权 | 密码销毁 | 销毁记录 |
| 安全评估 | 定期安全评估 | 攻击模拟 | 模拟报告 |

---



---

## 9.7 UI/UX设计规范

### 9.7.1 整体设计风格

| 关键词 | 设计手法 | 体现 |
|--------|----------|------|
| 专业 | 清晰的信息层级 | 标题、摘要、详情 |
| 安全 | 稳重配色+图标 | 锁/盾牌/加密符号 |
| 现代 | 扁平化+微动效 | 圆角卡片+过渡动画 |
| 高效 | 数据密度适中 | 关键信息一屏可见 |
| Agent | Agent角色标识 | 每层标注来源Agent |

### 9.7.2 配色方案

**主色系**：

| 用途 | 颜色 | Hex值 | 应用场景 |
|------|------|-------|----------|
| 主色 | 深蓝 | `#1565C0` | 导航栏、按钮、标题 |
| 主色-浅 | 浅蓝 | `#E3F2FD` | 背景高亮、选中状态 |
| 辅色 | 青色 | `#00897B` | 安全状态、成功提示 |
| 警告色 | 琥珀 | `#FF8F00` | 警告状态、即将过期 |
| 危险色 | 红色 | `#D32F2F` | 错误状态、拒绝操作 |
| 成功色 | 绿色 | `#388E3C` | 通过状态、允许操作 |

**五层权限色板**：

| 层级 | 颜色 | Hex值 | 含义 |
|------|------|-------|------|
| L1 | 绿色 | `#4CAF50` | 安全可访问 |
| L2 | 蓝色 | `#2196F3` | 需授权 |
| L2.5 | 紫色 | `#9C27B0` | 需高级授权 |
| L2.7 | 橙色 | `#FF9800` | SelfBrain专属 |
| L3 | 红色 | `#F44336` | 最高保护 |

### 9.7.3 字体和图标

| 场景 | 字体 | 说明 |
|------|------|------|
| 中文正文 | 思源黑体 / 微软雅黑 | 现代清晰 |
| 英文正文 | Inter / Roboto | 数据展示优秀 |
| 代码/密码 | JetBrains Mono | 等宽，密码清晰 |
| 数据数字 | DIN Pro | 数字对齐 |

### 9.7.4 响应式布局

| 断点 | 宽度 | 设备 | 布局策略 |
|------|------|------|----------|
| xs | < 576px | 手机 | 单列堆叠 |
| sm | 576-768px | 大手机 | 单列+侧边栏折叠 |
| md | 768-992px | 平板 | 双列布局 |
| lg | 992-1200px | 笔记本 | 标准Dashboard |
| xl | > 1200px | 桌面 | 全功能 |

### 9.7.5 交互动效规范

| 动效类型 | 时长 | 缓动函数 | 应用场景 |
|----------|------|----------|----------|
| 淡入淡出 | 200ms | ease-in-out | 组件加载/切换 |
| 滑入 | 300ms | ease-out | 侧边栏展开 |
| 缩放 | 150ms | ease-in | 按钮点击反馈 |
| 颜色过渡 | 200ms | linear | 状态变化 |
| 进度条 | 实时 | linear | 密码倒计时 |

---

## 9.8 前端代码示例

### 9.8.1 Dashboard主页面组件

```tsx
// Dashboard.tsx - 主页面 (React + TypeScript + Ant Design)
import React, { useEffect, useState, useCallback } from 'react';
import { Row, Col, Card, Layout, Menu, Badge, message } from 'antd';
import {
  KeyOutlined, SafetyOutlined, DatabaseOutlined,
  FileTextOutlined, BugOutlined, FilePdfOutlined, RobotOutlined
} from '@ant-design/icons';
import { PasswordMonitorPanel } from './components/PasswordMonitor';
import { PermissionHeatmap } from './components/PermissionHeatmap';
import { AuditLogViewer } from './components/AuditLogViewer';
import { AttackSimulator } from './components/AttackSimulator';
import { DashboardWebSocketClient } from './services/WebSocketClient';
import { useDashboardStore } from './store/dashboardStore';

const { Header, Sider, Content, Footer } = Layout;

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  color: string;
  trend?: { value: number; direction: 'up' | 'down' };
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color, trend }) => (
  <Card hoverable style={{ borderTop: `3px solid ${color}` }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div>
        <div style={{ color: '#757575', fontSize: 13 }}>{title}</div>
        <div style={{ fontSize: 28, fontWeight: 700 }}>{value}</div>
        {trend && (
          <div style={{ fontSize: 12, color: trend.direction === 'up' ? '#388E3C' : '#D32F2F' }}>
            {trend.direction === 'up' ? '↑' : '↓'} {trend.value}%
          </div>
        )}
      </div>
      <div style={{ fontSize: 36, color, opacity: 0.8 }}>{icon}</div>
    </div>
  </Card>
);

const Dashboard: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [activeMenu, setActiveMenu] = useState('overview');
  const [wsStatus, setWsStatus] = useState<'connecting'|'connected'|'disconnected'>('connecting');
  const { activePasswords, expiredToday, totalGenerated, avgLifetime } = useDashboardStore();

  useEffect(() => {
    const client = new DashboardWebSocketClient('ws://localhost:8765');
    client.on('heartbeat', () => setWsStatus('connected'));
    client.on('passwords', (msg) => useDashboardStore.getState().handlePasswordEvent(msg));
    client.on('alerts', (msg) => message.warning(`Security Alert: ${msg.data?.message}`));
    client.connect().then(() => setWsStatus('connected')).catch(() => setWsStatus('disconnected'));
    useDashboardStore.getState().setWsClient(client);
    return () => client.disconnect();
  }, []);

  const menuItems = [
    { key: 'overview', icon: <SafetyOutlined />, label: '安全概览' },
    { key: 'passwords', icon: <KeyOutlined />, label: '密码监控' },
    { key: 'permissions', icon: <SafetyOutlined />, label: '权限矩阵' },
    { key: 'audit', icon: <FileTextOutlined />, label: '审计日志' },
    { key: 'simulator', icon: <BugOutlined />, label: '攻击模拟器' },
    { key: 'reports', icon: <FilePdfOutlined />, label: '安全报告' },
    { key: 'agents', icon: <RobotOutlined />, label: 'Agent状态' },
  ];

  const renderContent = useCallback(() => {
    switch (activeMenu) {
      case 'passwords': return <PasswordMonitorPanel />;
      case 'permissions': return <PermissionHeatmap />;
      case 'audit': return <AuditLogViewer />;
      case 'simulator': return <AttackSimulator />;
      default: return (
        <>
          <Row gutter={[16,16]} style={{marginBottom:24}}>
            <Col xs={24} sm={12} lg={6}>
              <StatCard title="活跃密码" value={activePasswords} icon={<KeyOutlined/>} color="#4CAF50"/>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <StatCard title="今日过期" value={expiredToday} icon={<DatabaseOutlined/>} color="#FF9800"/>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <StatCard title="总生成量" value={totalGenerated.toLocaleString()} icon={<FileTextOutlined/>} color="#2196F3"/>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <StatCard title="平均寿命" value={avgLifetime} icon={<SafetyOutlined/>} color="#9C27B0"/>
            </Col>
          </Row>
        </>
      );
    }
  }, [activeMenu, activePasswords, expiredToday, totalGenerated, avgLifetime]);

  return (
    <Layout style={{minHeight:'100vh'}}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} style={{background:'#fff'}} width={220}>
        <div style={{padding:16,textAlign:'center'}}>
          <SafetyOutlined style={{fontSize:28,color:'#1565C0'}}/>
          {!collapsed && <div style={{fontSize:16,fontWeight:700,color:'#1565C0',marginTop:4}}>SelfBrain</div>}
        </div>
        <Menu mode="inline" selectedKeys={[activeMenu]} onClick={({key})=>setActiveMenu(key)} items={menuItems}/>
      </Sider>
      <Layout>
        <Header style={{background:'#fff',padding:'0 24px',display:'flex',justifyContent:'space-between',alignItems:'center',borderBottom:'1px solid #E0E0E0'}}>
          <div style={{fontSize:18,fontWeight:600}}>Security Dashboard - 7-Agent AgentTeams</div>
          <Badge status={wsStatus==='connected'?'success':'error'} text={`WS: ${wsStatus}`}/>
        </Header>
        <Content style={{padding:24,background:'#FAFAFA'}}>{renderContent()}</Content>
        <Footer style={{textAlign:'center',padding:12}}>SelfBrain Security Dashboard v2.0</Footer>
      </Layout>
    </Layout>
  );
};

export default Dashboard;
```

### 9.8.2 权限矩阵热力图（ECharts）

```tsx
import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { useDashboardStore } from '../store/dashboardStore';

export const PermissionHeatmap: React.FC<{compact?: boolean}> = ({compact}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const { heatmapData } = useDashboardStore();

  useEffect(() => {
    if (!chartRef.current) return;
    const chart = echarts.init(chartRef.current);
    const layers = ['L1','L2','L2.5','L2.7','L3'];
    const models = ['GPT-4','Claude','Gemini','SelfBrain'];
    const data = heatmapData?.cells?.flat()?.map(cell => [
      models.indexOf(cell.model), layers.indexOf(cell.layer), cell.percentage
    ]) || [];

    chart.setOption({
      tooltip: { formatter: (p:any) => `${models[p.data[0]]} -> ${layers[p.data[1]]}: ${p.data[2]}%` },
      grid: { top: 40, bottom: 60, left: 80, right: 40 },
      xAxis: { type: 'category', data: models },
      yAxis: { type: 'category', data: layers },
      visualMap: {
        min: 0, max: 100, calculable: true, orient: 'horizontal', left: 'center', bottom: 0,
        inRange: { color: ['#F5F5F5','#C8E6C9','#81C784','#FFF176','#FFB74D','#EF5350'] },
      },
      series: [{
        type: 'heatmap', data,
        label: { show: true, formatter: (p:any) => `${p.data[2]}%` },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
        itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 4 },
      }],
    });
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => { window.removeEventListener('resize', resize); chart.dispose(); };
  }, [heatmapData]);

  return <div ref={chartRef} style={{width:'100%', height: compact?250:400}}/>;
};
```

### 9.8.3 审计日志查看器

```tsx
import React, { useState } from 'react';
import { Table, Input, Select, Space, Button, Tag, Row, Col } from 'antd';
import { DownloadOutlined, FileExcelOutlined, FilePdfOutlined } from '@ant-design/icons';
import { useDashboardStore } from '../store/dashboardStore';

export const AuditLogViewer: React.FC<{compact?: boolean; pageSize?: number}> = ({compact, pageSize=50}) => {
  const { auditLogs, exportAuditLogs, totalAuditLogs } = useDashboardStore();

  const columns = [
    { title:'Time', dataIndex:'formattedTime', key:'time', width:180, sorter: (a:any,b:any) => a.timestamp-b.timestamp },
    { title:'Actor', key:'actor', width:120, render: (_:any,r:any) => <Tag color={r.actor.type==='model'?'blue':'green'}>{r.actor.id}</Tag> },
    { title:'Agent', key:'agent', width:120, render: (_:any,r:any) => r.actor.agentRole ? <Tag color="purple">{r.actor.agentRole}</Tag> : '-' },
    { title:'Action', dataIndex:['action','type'], key:'action', width:100 },
    { title:'Skill', key:'skill', width:100, render: (_:any,r:any) => r.action.skillUsed ? <Tag color="cyan">{r.action.skillUsed}</Tag> : '-' },
    { title:'Layer', dataIndex:['action','layer'], key:'layer', width:80, render:(l:string)=>l?<Tag>{l}</Tag>:'-' },
    { title:'Result', key:'result', width:80, render: (_:any,r:any) => <Tag color={r.result.status==='allowed'?'success':'error'}>{r.result.status==='allowed'?'OK':'DENIED'}</Tag> },
  ];

  return <Table dataSource={auditLogs} columns={columns} rowKey="id"
    pagination={{pageSize, showTotal:(t:number)=>`Total ${t}`}} scroll={{x:1400}}/>;
};
```

### 9.8.4 WebSocket实时通信客户端

```typescript
// services/WebSocketClient.ts
type MessageHandler = (data: any) => void;

export class DashboardWebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnect = 10;
  private heartbeatTimer: ReturnType<typeof setTimeout> | null = null;
  private listeners: Map<string, Set<MessageHandler>> = new Map();

  constructor(private url: string) {}

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);
      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.ws!.send(JSON.stringify({
          type: 'subscribe',
          channels: ['passwords', 'permissions', 'audit', 'alerts']
        }));
        this.resetHeartbeatWatch();
        resolve();
      };
      this.ws.onmessage = (e) => {
        this.resetHeartbeatWatch();
        const msg = JSON.parse(e.data);
        if (msg.type === 'heartbeat') { this.emit('heartbeat', msg); }
        else if (msg.type === 'event') { this.emit(msg.channel, msg); }
      };
      this.ws.onclose = () => { this.emit('connection', { status: 'disconnected' }); this.scheduleReconnect(); };
      this.ws.onerror = (e) => reject(e);
    });
  }

  on(event: string, handler: MessageHandler) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event)!.add(handler);
  }

  off(event: string, handler: MessageHandler) { this.listeners.get(event)?.delete(handler); }

  private emit(event: string, data: any) {
    this.listeners.get(event)?.forEach(h => { try { h(data); } catch(e) { console.error(e); } });
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnect) return;
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 30000);
    setTimeout(() => this.connect(), delay);
  }

  private resetHeartbeatWatch() {
    if (this.heartbeatTimer) clearTimeout(this.heartbeatTimer);
    this.heartbeatTimer = setTimeout(() => { this.ws?.close(); }, 60000);
  }

  disconnect() {
    this.reconnectAttempts = this.maxReconnect;
    this.ws?.close(1000, 'Client disconnect');
    this.ws = null;
  }
}
```

### 9.8.5 状态管理（Zustand）

```typescript
// store/dashboardStore.ts
import { create } from 'zustand';
import type { DashboardWebSocketClient } from '../services/WebSocketClient';

interface DashboardState {
  wsClient: DashboardWebSocketClient | null;
  setWsClient: (c: DashboardWebSocketClient) => void;
  passwords: any[];
  activePasswords: number;
  expiredToday: number;
  totalGenerated: number;
  avgLifetime: string;
  heatmapData: any;
  auditLogs: any[];
  totalAuditLogs: number;
  agentStatuses: Record<string, string>;
  refreshPasswords: () => Promise<void>;
  destroyPassword: (id: string) => Promise<void>;
  handlePasswordEvent: (event: any) => void;
  fetchHeatmapData: () => Promise<void>;
  fetchAuditLogs: (filters?: any) => Promise<void>;
  exportAuditLogs: (format: string, filters?: any) => Promise<void>;
  fetchAgentStatuses: () => Promise<void>;
  fetchStats: () => Promise<void>;
}

export const useDashboardStore = create<DashboardState>()((set, get) => ({
  wsClient: null,
  setWsClient: (c) => set({ wsClient: c }),
  passwords: [],
  activePasswords: 0,
  expiredToday: 0,
  totalGenerated: 0,
  avgLifetime: '4m 32s',
  heatmapData: null,
  auditLogs: [],
  totalAuditLogs: 0,
  agentStatuses: {},

  refreshPasswords: async () => {
    const res = await fetch('/api/dashboard/passwords');
    const data = await res.json();
    set({ passwords: data.passwords, activePasswords: data.active_count });
  },

  destroyPassword: async (id) => {
    await fetch(`/api/dashboard/passwords/${id}`, { method: 'DELETE' });
    get().refreshPasswords();
  },

  handlePasswordEvent: (event) => {
    const { passwords } = get();
    if (event.event === 'created') {
      set({ passwords: [...passwords, event.data], activePasswords: get().activePasswords + 1 });
    } else if (event.event === 'expired') {
      set({
        passwords: passwords.map((p:any) => p.id === event.data.id ? {...p, status:'expired'} : p),
        activePasswords: Math.max(0, get().activePasswords - 1),
        expiredToday: get().expiredToday + 1,
      });
    }
  },

  fetchHeatmapData: async () => {
    const res = await fetch('/api/dashboard/heatmap');
    set({ heatmapData: await res.json() });
  },

  fetchAuditLogs: async (filters) => {
    const params = new URLSearchParams(filters || {});
    const res = await fetch(`/api/dashboard/audit?${params}`);
    const data = await res.json();
    set({ auditLogs: data.entries, totalAuditLogs: data.total });
  },

  exportAuditLogs: async (format, filters) => {
    const params = new URLSearchParams({ format, ...filters });
    const res = await fetch(`/api/dashboard/audit/export?${params}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `audit-report.${format}`; a.click();
    URL.revokeObjectURL(url);
  },

  fetchAgentStatuses: async () => {
    const res = await fetch('/api/dashboard/agents');
    set({ agentStatuses: await res.json() });
  },

  fetchStats: async () => {
    const res = await fetch('/api/dashboard/stats');
    const data = await res.json();
    set({
      activePasswords: data.active_passwords,
      expiredToday: data.expired_today,
      totalGenerated: data.total_generated,
      avgLifetime: data.avg_lifetime,
    });
    get().refreshPasswords();
    get().fetchHeatmapData();
    get().fetchAuditLogs();
    get().fetchAgentStatuses();
  },
}));
```

---

## 9.9 开源/闭源边界矩阵

### 9.9.1 Dashboard 各组件的开源状态

```mermaid
graph LR
    subgraph "Open Source"
        A[Dashboard React Frontend]
        B[AuditTrail Schema JSON]
        C[AuditTrail Wrapper Python]
        D[WebSocket Protocol]
        E[ECharts Config]
    end

    subgraph "Closed Source"
        F[AuditTrail SDK]
        G[Anomaly Detection]
        H[Compliance Scoring]
        I[Evidence Chain]
        J[Risk Engine]
    end

    A -->|invoke| B
    B -->|validate| C
    C -->|wrap| F
```

### 9.9.2 完整开源/闭源矩阵

| 组件 | 开源/闭源 | 文件 | 职责 |
|------|-----------|------|------|
| Dashboard React 前端 | Open Source | `dashboard/` | UI 渲染、交互、图表 |
| WebSocket Server | Open Source | `ws_server.py` | 实时推送 |
| AuditTrail Schema | Open Source | `audit_entry.json` | 审计日志 JSON 格式定义 |
| AuditTrail Wrapper | Open Source | `audit_trail.py` | 参数验证、错误处理、SDK 调用封装 |
| AuditTrail SDK | Closed Source | `audit_core.so/.dll` | 审计规则引擎、异常检测、合规评分 |
| 异常检测算法 | Closed Source | SDK 内部 | 越权检测、频率检测、模式分析 |
| 证据链校验 | Closed Source | SDK 内部 | 完整性校验、防篡改验证 |
| 风险评估引擎 | Closed Source | SDK 内部 | 动态风险评分、威胁等级计算 |

### 9.9.3 开发者如何基于开源接口扩展

```python
# Developer perspective: Using AuditTrail Wrapper (Open Source)
from audit_trail import AuditTrail  # Open Source Wrapper

# Initialize - auto-loads SDK (Closed Source black box)
trail = AuditTrail(config_path="./audit_config.yaml")

# Write audit log - Wrapper validates -> SDK executes rules
entry = trail.write_log(
    actor={"type": "model", "id": "GPT-4", "session_id": "S7A3B"},
    action={"type": "read", "target": "customer_data", "layer": "L1"},
    result={"status": "allowed", "duration_ms": 45},
    context={"task_id": "TASK-001"}
)

# Query audit logs - Wrapper validates query -> SDK retrieves
entries = trail.query(
    time_range={"start": "2026-08-03", "end": "2026-08-03"},
    filters={"actor_id": "GPT-4", "layer": "L1"},
    sort={"field": "timestamp", "order": "desc"},
    pagination={"page": 1, "page_size": 50}
)

# Export report - Wrapper calls SDK compliance scoring
report = trail.export(
    format="pdf",
    standard="GDPR",
    output_path="./audit_report.pdf"
)
```

---

## 9.10 黑板数据流转模型

### 9.10.1 审计数据在黑板模式中的完整流转

```mermaid
sequenceDiagram
    participant User as User
    participant PG as Privacy Guardian
    participant BB as Blackboard
    participant CG as Cipher Generator
    participant MN as Memory Navigator
    participant PE as Policy Enforcer
    participant AL as Audit Logger
    participant VD as Validator

    User->>PG: "Analyze Q2 financials"
    PG->>BB: Write task TASK-001

    BB->>CG: Request password
    CG->>BB: Write password_created

    BB->>MN: Use password for L1-L2 retrieval
    MN->>BB: Write access_event

    BB->>PE: Verify permission
    PE->>BB: Write permission_granted

    BB->>AL: Read all events from blackboard
    AL->>AL: AuditTrail Skill processing
    Note over AL: Wrapper validates, SDK applies rules
    AL->>BB: Write audit_entry

    BB->>VD: Validate consistency
    VD->>BB: Write validation_result

    AL->>BB: Write task_audit_summary
    BB->>PG: Completeness check
    PG->>User: Return result
```

### 9.10.2 黑板数据结构

```typescript
interface BlackboardAuditData {
  audit_entries: AuditEntry[];

  task_audit_summary: {
    task_id: string;
    total_events: number;
    allowed_count: number;
    denied_count: number;
    anomaly_count: number;
    agents_involved: string[];
    skills_used: string[];
    start_time: number;
    end_time: number;
    compliance_score: number;     // SDK closed-source calculation
    evidence_chain_hash: string;  // SDK closed-source generation
  };

  active_alerts: AlertEntry[];
}

interface AuditEntry {
  id: string;
  timestamp: number;
  formatted_time: string;
  actor: {
    type: 'model' | 'user' | 'system' | 'agent';
    id: string;
    agent_role?: string;
    session_id?: string;
    ip_address?: string;
  };
  action: {
    type: string;
    target: string;
    layer?: string;
    data_type?: string;
    skill_used?: string;
  };
  result: {
    status: 'allowed' | 'denied' | 'error';
    reason?: string;
    duration_ms?: number;
  };
  context: {
    task_id?: string;
    token_id?: string;
    password_id?: string;
    correlation_id?: string;
    blackboard_state?: string;
  };
  evidence: {
    hash: string;           // SDK generated (closed)
    chain_id: string;       // SDK generated (closed)
    integrity: boolean;     // SDK verified (closed)
  };
}
```

### 9.10.3 Audit Logger 在黑板模式中的生命周期

```mermaid
stateDiagram-v2
    [*] --> WaitTask: PG publishes task to blackboard
    WaitTask --> ReadEvents: Read other Agent operations
    ReadEvents --> CallSkill: AuditTrail.write(event)
    CallSkill --> WrapperValidate: Open: param validation
    WrapperValidate --> SDKProcess: Closed: audit rules
    SDKProcess --> WriteBlackboard: AuditEntry JSON
    WriteBlackboard --> ReadEvents: Next event
    WriteBlackboard --> GenSummary: Task complete
    GenSummary --> WriteBlackboard: task_audit_summary
    WriteBlackboard --> WaitTask: Ready for next task
```

### 9.10.4 Dashboard 与黑板的交互时序

```mermaid
sequenceDiagram
    participant BB as Blackboard
    participant AL as Audit Logger
    participant SDK as Core SDK (closed)
    participant WS as WebSocket Server
    participant DASH as Dashboard

    BB->>AL: New audit event
    AL->>SDK: AuditTrail.write(event)
    SDK-->>AL: AuditEntry + evidence_hash
    AL->>BB: Write back audit_entry
    AL->>WS: notify_audit_event(entry)
    WS->>DASH: Push channel=audit
    DASH->>DASH: Update Layer4 audit log
    DASH->>DASH: Update Layer1-3 data
    DASH->>DASH: Check alert conditions
```

---

## 章节总结

本章详细介绍了SelfBrain可视化Dashboard在 **7-Agent 协同体系**中的完整定位与实现方案：

**架构定位**：Dashboard 是 **Audit Logger Worker** 的可视化前端，通过 **AuditTrail Skill**（Schema + Wrapper + SDK 三层）获取结构化审计数据。

**四层安全监控**：从密码状态、权限矩阵、数据保存到审计日志，全方位覆盖安全可视化需求，每层数据对应不同的 Agent Worker 输出。

**实时监控**：通过WebSocket实现零延迟推送，密码倒计时精确到秒级更新。

**权限可视化**：五层访问热力图 + 模型访问时间线 + 异常告警，一目了然。

**审计合规**：完整日志查看器，支持高级过滤、多格式导出、自动生成合规报告。

**攻击模拟器**：7种攻击场景的自动化验证，证明99/100的安全评分。

**专业UI/UX**：现代安全设计风格，响应式布局，统一配色方案和交互动效。

**完整代码**：500+行前端代码，涵盖React组件、WebSocket通信、ECharts图表、Zustand状态管理。

**开源/闭源边界**：Schema + Wrapper + Dashboard 前端开源，SDK 核心算法闭源保护。

**黑板数据流转**：审计数据在 AgentTeams 黑板模式中的完整流转路径，从 Agent 操作到 Dashboard 可视化。

---

**安全评分**: 99/100

---

## 上一章 / 下一章

- [第8章：分层权限系统](./08-分层权限系统.md)
- [第10章：插件架构实现](./10-插件架构实现.md)

---

**完成时间**: 2026-08-03
**页数**: 约28页
**状态**: v2.0 - AgentTeams 适配版

