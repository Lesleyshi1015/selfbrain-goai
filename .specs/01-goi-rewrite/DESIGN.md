# DESIGN-001: SelfBrain-GOAI AgentTeams 架构适配设计

## 1. 技术选型

| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 协同框架 | AgentTeams（黑板模式）| GOAI 赛道强制要求 |
| Agent 数量 | 7（1 Leader + 5 Workers + 1 Validator）| 满足 ≥3 要求，对标 Memory Palace |
| Skill 体系 | 6-Skill（Schema + Wrapper + SDK 三层）| 可复用能力沉淀 |
| 黑盒保护 | 开源接口 + 闭源 SDK（.so/.dll）| 保护核心算法，满足赛道开源要求 |
| 通信机制 | Team Room + 共享黑板 | AgentTeams 标准模式 |

## 2. 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    用户 / 外部系统                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               Privacy Guardian (Team Leader)                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  接收请求 → 发布任务到黑板 → 轮番喊 Workers →        │    │
│  │  评估黑板完整度 → 主动重建答案 → 返回用户             │    │
│  └─────────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │ Team Room
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                        共享黑板 (Blackboard)                   │
│  { task_type, user_query, results, completeness, validation } │
└─────┬──────┬──────┬──────┬──────┬──────┬─────────────────────┘
      │      │      │      │      │      │
      ▼      ▼      ▼      ▼      ▼      ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐
│Memory│ │Cipher│ │Data  │ │Policy│ │Audit │ │Validator │
│Navi. │ │Gen.  │ │Coord.│ │Enf.  │ │Logger│ │          │
│(L1-3)│ │      │ │      │ │      │ │      │ │(6维核查) │
└──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └────┬─────┘
   │        │        │        │        │          │
   ▼        ▼        ▼        ▼        ▼          ▼
┌─────────────────────────────────────────────────────────────┐
│              Core SDK (闭源黑盒 .so/.dll)                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│
│  │ 动态加密引擎  │ │ 检索引擎     │ │ 权限/审计引擎        ││
│  │ 5分钟过期     │ │ HNSW+BM25   │ │ 权限矩阵/审计日志     ││
│  │ 会话隔离     │ │ RRF融合     │ │ 6维核查规则          ││
│  └──────────────┘ └──────────────┘ └──────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 3. 7-Agent 清单

| Agent | 角色 | 职责 | 映射原组件 |
|-------|------|------|-----------|
| Privacy Guardian | Team Leader | 总调度、黑板发布、完整度评估 | Core |
| Memory Navigator | Worker | Memory Palace 五层检索 | Navigator |
| Cipher Generator | Worker | 动态密码生成+加密 | Cipher |
| Data Coordinator | Worker | 多源数据融合 | Data Broker |
| Policy Enforcer | Worker | 分层权限验证 | 权限系统 |
| Audit Logger | Worker | 审计日志+证据链 | Dashboard |
| Validator | Worker | 结果一致性6维核查 | 新增 |

## 4. 6-Skill 体系

| Skill | 功能 | 开源层 | 闭源层 |
|-------|------|--------|--------|
| PrivacyShield | 银行级动态加密 | Schema+Wrapper | 加密算法 |
| MemoryProbe | 五层检索 | Schema+Wrapper | HNSW+BM25+RRF |
| DataFusion | 多源数据融合 | Schema+Wrapper | 融合算法 |
| AccessControl | 分层权限验证 | Schema+Wrapper | 权限策略 |
| AuditTrail | 审计日志+证据链 | Schema+Wrapper | 审计规则 |
| ResultVerify | 结果一致性检查 | Schema+Wrapper | 核查规则 |

## 5. ADR 列表

- ADR-001: 采用 AgentTeams 黑板模式（替代原有消息队列模式）
- ADR-002: 黑盒保护策略（开源接口 + 闭源 SDK）
- ADR-003: 6-Skill 体系设计（Schema+Wrapper+SDK 三层）
- ADR-004: 项目重新定位为"隐私保护的多Agent协同系统"