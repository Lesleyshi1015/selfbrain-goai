# SelfBrain-GOAI 架构文档

**最后更新**: 2026-08-03

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    外部模型 (GPT-5, DeepSeek, Qwen)          │
│                         ↓ MCP 协议                           │
├─────────────────────────────────────────────────────────────┤
│  Privacy Guardian (Team Leader)                              │
│  ├─ 任务拆解 → 共享黑板                                      │
│  ├─ 调度 6 个 Worker Agent                                   │
│  └─ 完整度评估 + 结果整合                                     │
├─────────────────────────────────────────────────────────────┤
│  Worker Agent 层                                             │
│  ├─ Memory Navigator ─→ MemoryAdapter ─→ 记忆系统            │
│  ├─ Cipher Generator ─→ PrivacyShield Skill ─→ 加密          │
│  ├─ Data Coordinator ─→ DataFusion Skill ─→ 多源融合         │
│  ├─ Policy Enforcer  ─→ AccessControl Skill ─→ 权限验证      │
│  ├─ Audit Logger     ─→ AuditTrail Skill ─→ 审计日志         │
│  └─ Validator        ─→ ResultVerify Skill ─→ 6维核查        │
├─────────────────────────────────────────────────────────────┤
│  Skill 体系（三层）                                           │
│  ├─ Schema (JSON, 开源)                                      │
│  ├─ Wrapper (Python, 开源)                                   │
│  └─ SDK (.so/.dll, 闭源)                                     │
├─────────────────────────────────────────────────────────────┤
│  Memory Adapter 层（开源）                                    │
│  ├─ SimpleFileAdapter ✅  本地文件                            │
│  ├─ VectorDBAdapter   ✅  ChromaDB/Milvus                    │
│  ├─ MemoryPalaceAdapter 🔒 五层架构（付费增值）               │
│  └─ CustomAdapter     ✅  用户自定义                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 模块依赖

```
Privacy Guardian
    ├── Memory Navigator → MemoryAdapter → 记忆系统后端
    ├── Cipher Generator → PrivacyShield → 加密引擎
    ├── Data Coordinator → DataFusion → 数据源连接器
    ├── Policy Enforcer  → AccessControl → 权限数据库
    ├── Audit Logger     → AuditTrail → 日志存储
    └── Validator        → ResultVerify → 验证规则

共享黑板 (Team Room)
    └─ 所有 Agent 通过黑板通信，黑板字段包含 adapter_type
```

---

## 跨模块契约

### 黑板通信协议

```json
{
  "task_id": "task_xxx",
  "task_type": "retrieve | write | verify",
  "user_query": "用户查询",
  "adapter_type": "simple_file | vector_db | memory_palace | custom",
  "required_layers": ["L1", "L2"],
  "navigator_status": "pending | in_progress | completed | failed",
  "retrieval_results": [],
  "adapter_used": "vector_db",
  "completeness_score": 0.95
}
```

### Skill 调用协议

```json
{
  "skill": "MemoryProbe",
  "input": {
    "query": "...",
    "adapter_type": "vector_db",
    "top_k": 5
  }
}
```

---

## ADR（架构决策记录）

### ADR-001: MemoryAdapter 适配器层

- **决策**: 引入通用 MemoryAdapter 接口，解耦 Navigator 与 Memory Palace
- **原因**: 两个项目独立参赛 + 支持任意记忆系统 + 商业分层
- **替代方案**: 直接绑定 Memory Palace（被否决：强耦合）

### ADR-002: 开源/闭源边界

- **决策**: Agent 调用逻辑 + Skill Schema + Wrapper 开源，Core SDK 闭源
- **原因**: 满足比赛开源要求，同时保护核心竞争力
- **替代方案**: 全部开源 / 全部闭源（均被否决）

### ADR-003: 7-Agent 黑板模式

- **决策**: Privacy Guardian 作为 Team Leader，6 个 Worker 通过共享黑板通信
- **原因**: 可观测性、可扩展性、符合 AgentInfra 定位
- **替代方案**: 直接调用链（被否决：不透明）
