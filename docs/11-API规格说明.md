# 第11章：API规格说明

**版本**: v2.0  
**更新日期**: 2026-08-03  
**变更摘要**: 适配 AgentTeams 架构，新增黑盒保护策略、MCP 接口、Agent 间通信 API、6-Skill 调用接口

---

## 概述

SelfBrain 对外提供统一的 RESTful API 接口，支持查询、插件管理、配置、监控以及多 Agent 协同等核心功能。所有 API 遵循 OpenAPI 3.0 规范，提供完整的类型定义和错误处理。

**基础 URL**: `http://localhost:8080/api/v1`

**认证方式**: Bearer Token（通过 Authorization header 传递）

### 开源/闭源分层总览

> **设计原则**：开源接口保证社区可集成、可二次开发；闭源 SDK 保护核心算法知识产权，提供 6–24 个月追赶窗口。

| 层级 | 状态 | 包含内容 |
|------|------|---------|
| **开源 API** | 🟢 开源 | Agent 调用接口、Skill Schema（JSON）、Skill Wrapper（Python）、MCP 工具接口、黑板读写接口、Team Room 消息接口 |
| **闭源 SDK** | 🔒 闭源 | Core SDK（.so/.dll）、加密算法、HNSW+BM25 检索引擎、权限策略引擎、审计规则引擎、6 维核查规则 |
| **公开协议** | 🟢 开源 | RESTful 接口定义、MCP 工具描述（JSON Schema）、错误码规范、流式协议 |

---

## 11.1 统一查询接口

### POST /api/v1/query

**功能**：统一的 AI 查询入口，自动处理隐私保护、Memory Palace 访问和模型选择。  
**开源状态**：🟢 开源

#### 请求参数

```json
{
  "query": "string",
  "session_id": "string",
  "model": "string",
  "privacy_level": "string",
  "max_tokens": 2000,
  "temperature": 0.7,
  "stream": false,
  "metadata": { "user_id": "string", "tags": ["string"] }
}
```

#### 响应格式（200 OK）

```json
{
  "status": "success",
  "data": {
    "query_id": "q_1234567890",
    "session_id": "sess_abcdef123",
    "response": "string",
    "model_used": "gpt-4",
    "tokens_used": { "input": 150, "output": 350, "total": 500 },
    "memory_layers_accessed": ["L1", "L2"],
    "encrypted_data_count": 3,
    "processing_time_ms": 180,
    "timestamp": "2026-08-03T03:32:00Z"
  }
}
```

**流式响应（stream=true）**：

```
data: {"type":"start","query_id":"q_1234567890"}
data: {"type":"chunk","content":"Hello"}
data: {"type":"chunk","content":" world"}
data: {"type":"end","tokens_used":500}
```

#### 使用示例

**Python SDK**：

```python
from selfbrain import Client
client = Client(api_key="sb_your_api_key")

# 基础查询
response = client.query("分析Q3营收")
print(response.data.response)

# 流式查询
for chunk in client.query("解释区块链技术", stream=True):
    print(chunk.content, end="")

# 自定义参数
response = client.query(query="敏感财务分析", privacy_level="high", model="claude-3-opus", max_tokens=3000)
```

**JavaScript SDK**：

```javascript
import { SelfBrainClient } from '@selfbrain/sdk';
const client = new SelfBrainClient({ apiKey: 'sb_your_api_key' });
const response = await client.query({ query: '分析Q3营收' });
console.log(response.data.response);
```

**cURL**：

```bash
curl -X POST http://localhost:8080/api/v1/query   -H "Authorization: Bearer sb_your_api_key"   -H "Content-Type: application/json"   -d '{"query":"分析Q3营收","privacy_level":"high","max_tokens":2000}'
```

---

## 11.2 插件管理接口

### POST /api/v1/plugins/load

**功能**：加载自定义 MEMO 插件。  
**开源状态**：🟢 开源（接口）/ 🔒 闭源（插件二进制）

```json
// 请求
{ "plugin_type": "navigator", "plugin_path": "/path/to/plugin.pth", "config": { "quantization": "int4" } }
// 响应
{ "status": "success", "data": { "plugin_id": "plugin_1234", "status": "active", "memory_usage_mb": 1800 } }
```

```python
response = client.plugins.load(plugin_type="navigator", plugin_path="/path/to/custom_navigator.pth", config={"quantization": "int4"})
```

### DELETE /api/v1/plugins/unload

**功能**：卸载插件。 **开源状态**：🟢 开源  
```json
// 请求: { "plugin_id": "string" }
// 响应: { "status": "success", "data": { "plugin_id": "plugin_1234", "unloaded_at": "..." } }
```

### GET /api/v1/plugins/list

**功能**：列出所有已加载插件。 **开源状态**：🟢 开源  
```json
{ "status": "success", "data": { "plugins": [...], "total_memory_usage_mb": 3550 } }
```

---

## 11.3 配置接口

**开源状态**：🟢 开源

### GET /api/v1/config

```json
{
  "status": "success",
  "data": {
    "privacy": { "default_level": "high", "cipher_expiry_minutes": 5, "session_isolation": true },
    "memory_palace": { "layers_enabled": ["L1","L2","L2.5","L2.7","L3"], "l3_exclusive": true },
    "models": { "default_model": "gpt-4", "fallback_model": "claude-3-opus" },
    "performance": { "max_concurrent_queries": 10, "timeout_seconds": 30 }
  }
}
```

### PUT /api/v1/config

```json
// 请求: { "privacy": { "default_level": "high" }, "models": { "default_model": "claude-3-opus" } }
// 响应: { "status": "success", "data": { "updated_fields": ["privacy.default_level"] } }
```

---

## 11.4 监控接口

**开源状态**：🟢 开源

### GET /api/v1/metrics

```json
{
  "status": "success",
  "data": {
    "system": { "cpu_usage_percent": 35.2, "memory_usage_mb": 6800, "gpu_usage_percent": 78.5 },
    "queries": { "total_queries": 1523, "avg_response_time_ms": 185, "error_rate_percent": 0.3 },
    "tokens": { "tokens_saved_percent": 72.5, "cost_saved_usd": 750.0 },
    "memory_palace": { "l1_hit_rate_percent": 82.0, "l2_hit_rate_percent": 15.0 },
    "encryption": { "active_ciphers": 12, "encryption_overhead_ms": 8 }
  }
}
```

### GET /api/v1/health

```json
{ "status": "healthy", "data": { "components": { "selfbrain_core": "healthy", "memo_navigator": "healthy", "memo_cipher": "healthy" }, "uptime_seconds": 86400, "version": "2.0.0" } }
```

#### 监控指标说明

| 指标类别 | 指标名称 | 说明 | 健康阈值 |
|---------|---------|------|---------|
| **系统资源** | cpu_usage_percent | CPU使用率 | < 80% |
| | memory_usage_mb | 内存使用量 | < 7000MB |
| | gpu_usage_percent | GPU使用率 | < 90% |
| **查询性能** | avg_response_time_ms | 平均响应时间 | < 200ms |
| | error_rate_percent | 错误率 | < 1% |
| **Token优化** | tokens_saved_percent | Token节约率 | > 70% |
| **Memory Palace** | l1_hit_rate_percent | L1缓存命中率 | > 80% |
| **加密** | encryption_overhead_ms | 加密开销 | < 10ms |


---

## 11.5 导师模型接口

### POST /api/v1/mentor/consult

**功能**：咨询导师模型，获取方法论/策略指导。  
**开源状态**：🟢 开源（接口定义）/ 🔒 闭源（安全检测算法）

```json
// 请求
{
  "question": "string",           // 必填：抽象化后的问题描述
  "context": "string",            // 可选：问题背景
  "domain": "string",             // 必填：问题所属领域
  "constraints": ["string"],      // 可选：约束条件
  "expected_output": "string",    // 可选：steps/advice/analysis
  "session_id": "string"          // 可选：会话ID
}

// 成功响应 200 OK
{
  "status": "success",
  "data": {
    "consult_id": "con_abc123",
    "strategy": "方法论建议",
    "steps": ["步骤1", "步骤2", "步骤3"],
    "confidence": 0.92,
    "reasoning": "推理过程",
    "processing_time_ms": 1500
  }
}

// 拒绝响应 400 Bad Request
{
  "status": "rejected",
  "error": { "code": "MENTOR_001", "message": "检测到敏感数据，请抽象化后重试" }
}
```

#### 使用示例

```python
response = client.mentor.consult(
    question="如何设计支持多租户的实时数据分析架构？",
    context="规模：中大型SaaS平台，核心需求：数据隔离、实时分析、成本优化",
    domain="system_architecture",
    constraints=["数据隔离要求高", "需要实时处理能力", "成本敏感"]
)
```

#### 安全检测

| 检测项 | 说明 | 处理 |
|--------|------|------|
| **具体数值** | 金额、数量、百分比等 | 拒绝并提示抽象化 |
| **实体名称** | 公司名、人名、产品名 | 拒绝并提示抽象化 |
| **时间范围** | 具体日期、季度 | 允许 |
| **技术领域** | 架构模式、技术栈 | 允许 |

---

## 11.6 Agent 调用接口（黑盒保护架构）

> 本节描述 AgentTeams 架构下 Agent 的调用接口。所有接口均为 **🟢 开源**，底层 Core SDK 为 **🔒 闭源**。

### 11.6.1 黑盒保护分层模型

```
┌─────────────────────────────────────────────────┐
│              开源层（社区可集成）                   │
│  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ REST API     │  │ MCP 工具接口              │ │
│  │ 接口定义      │  │ （JSON Schema 描述）      │ │
│  └──────┬───────┘  └────────────┬─────────────┘ │
│  ┌──────┴───────────────────────┴──────────────┐ │
│  │ Skill Wrapper（Python 薄层）                  │ │
│  │ 参数验证 + 序列化 + 调用转发                   │ │
│  └──────────────────────┬──────────────────────┘ │
├─────────────────────────┼────────────────────────┤
│              闭源层（知识产权保护）                 │
│  ┌──────────────────────┴──────────────────────┐ │
│  │ Core SDK（.so/.dll 二进制）                   │ │
│  │ 加密引擎 │ 检索引擎 │ 权限引擎 │ 审计引擎    │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 11.6.2 Agent 调用

#### POST /api/v1/agents/invoke

**开源状态**：🟢 开源

```json
// 请求
{
  "agent_id": "memory_navigator",
  "skill": "MemoryProbe",
  "input": { "query": "string", "layers": ["L1", "L2"], "privacy_level": "high" },
  "session_id": "string",
  "timeout_ms": 5000
}

// 响应 200 OK
{
  "status": "success",
  "data": {
    "invocation_id": "inv_xyz789",
    "agent_id": "memory_navigator",
    "skill": "MemoryProbe",
    "output": { "results": ["..."], "layers_used": ["L1", "L2"], "confidence": 0.95 },
    "processing_time_ms": 320
  }
}
```

### 11.6.3 Agent 列表

#### GET /api/v1/agents

```json
{
  "status": "success",
  "data": {
    "agents": [
      { "agent_id": "privacy_guardian", "role": "leader", "skills": ["PrivacyShield", "ResultVerify"] },
      { "agent_id": "memory_navigator", "role": "worker", "skills": ["MemoryProbe"] },
      { "agent_id": "cipher_generator", "role": "worker", "skills": ["PrivacyShield"] },
      { "agent_id": "data_coordinator", "role": "worker", "skills": ["DataFusion"] },
      { "agent_id": "policy_enforcer", "role": "worker", "skills": ["AccessControl"] },
      { "agent_id": "audit_logger", "role": "worker", "skills": ["AuditTrail"] },
      { "agent_id": "validator", "role": "worker", "skills": ["ResultVerify"] }
    ],
    "total": 7
  }
}
```

---

## 11.7 Skill Schema 定义

> 所有 Skill 的 JSON Schema 均为 **🟢 开源**。

### Skill 三层架构

| 层级 | 状态 | 语言 | 职责 |
|------|------|------|------|
| **Schema** | 🟢 开源 | JSON | 定义输入输出格式、参数约束 |
| **Wrapper** | 🟢 开源 | Python | 参数验证 + 序列化 + 调用转发 |
| **SDK** | 🔒 闭源 | .so/.dll | 核心算法实现 |

### 6-Skill 一览

| Skill | 功能 | 闭源算法 |
|-------|------|---------|
| PrivacyShield | 银行级动态加密 | 加密引擎（5分钟过期、会话隔离） |
| MemoryProbe | 五层知识检索 | HNSW + BM25 + RRF 融合 |
| DataFusion | 多源数据融合 | 融合算法 |
| AccessControl | 分层权限验证 | 权限策略矩阵 |
| AuditTrail | 审计日志 + 证据链 | 审计规则引擎 |
| ResultVerify | 结果一致性 6 维核查 | 核查规则引擎 |

---

## 11.8 MCP（Model Context Protocol）工具接口

> 每个 Skill 暴露标准 MCP 工具接口，支持被任意 MCP 兼容客户端直接调用。  
> **开源状态**：🟢 开源（工具描述 + 协议）/ 🔒 闭源（底层实现）

### 11.8.1 privacy-shield

```json
{
  "name": "privacy_shield",
  "description": "银行级动态加密工具：对敏感数据执行会话级动态加密，密码5分钟自动过期",
  "inputSchema": {
    "type": "object",
    "properties": {
      "data": { "type": "string", "description": "待加密的明文数据" },
      "privacy_level": { "type": "string", "enum": ["high","medium","low"], "default": "high" },
      "session_id": { "type": "string" }
    },
    "required": ["data"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "encrypted_data": { "type": "string" },
      "cipher_id": { "type": "string" },
      "expires_at": { "type": "string", "format": "date-time" }
    }
  }
}
```

### 11.8.2 memory-probe

```json
{
  "name": "memory_probe",
  "description": "五层Memory Palace检索：L1缓存→L2向量→L2.5混合→L2.7知识图谱→L3独占",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string" },
      "layers": { "type": "array", "items": { "type": "string", "enum": ["L1","L2","L2.5","L2.7","L3"] } },
      "top_k": { "type": "integer", "default": 5 },
      "privacy_level": { "type": "string", "enum": ["high","medium","low"], "default": "high" }
    },
    "required": ["query"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "results": { "type": "array", "items": { "type": "object", "properties": { "content": {"type":"string"}, "layer": {"type":"string"}, "score": {"type":"number"} } } },
      "layers_accessed": { "type": "array", "items": { "type": "string" } },
      "total_results": { "type": "integer" }
    }
  }
}
```

### 11.8.3 data-fusion

```json
{
  "name": "data_fusion",
  "description": "多源数据融合工具：整合多个数据源结果，执行去重、排序和一致性校验",
  "inputSchema": {
    "type": "object",
    "properties": {
      "sources": { "type": "array", "items": { "type": "object", "properties": { "source_id": {"type":"string"}, "data": {"type":"object"}, "confidence": {"type":"number"} } } },
      "fusion_strategy": { "type": "string", "enum": ["weighted","priority","consensus"], "default": "weighted" }
    },
    "required": ["sources"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "fused_result": { "type": "object" },
      "confidence": { "type": "number" },
      "sources_used": { "type": "integer" },
      "conflicts_resolved": { "type": "integer" }
    }
  }
}
```

### 11.8.4 access-control

```json
{
  "name": "access_control",
  "description": "分层权限验证工具：基于角色和数据敏感度执行多层权限检查",
  "inputSchema": {
    "type": "object",
    "properties": {
      "user_id": { "type": "string" },
      "resource": { "type": "string" },
      "action": { "type": "string", "enum": ["read","write","execute","admin"] },
      "data_classification": { "type": "string", "enum": ["public","internal","confidential","secret"] }
    },
    "required": ["user_id", "resource", "action"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "allowed": { "type": "boolean" },
      "reason": { "type": "string" },
      "applied_policies": { "type": "array", "items": { "type": "string" } },
      "audit_id": { "type": "string" }
    }
  }
}
```

### 11.8.5 audit-trail

```json
{
  "name": "audit_trail",
  "description": "审计日志工具：记录完整操作证据链，支持追溯和合规审查",
  "inputSchema": {
    "type": "object",
    "properties": {
      "event_type": { "type": "string", "enum": ["query","access","modify","export","admin"] },
      "actor": { "type": "string" },
      "resource": { "type": "string" },
      "detail": { "type": "object" },
      "result": { "type": "string", "enum": ["success","denied","error"] }
    },
    "required": ["event_type", "actor", "result"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "audit_id": { "type": "string" },
      "timestamp": { "type": "string", "format": "date-time" },
      "chain_hash": { "type": "string" }
    }
  }
}
```

### 11.8.6 result-verify

```json
{
  "name": "result_verify",
  "description": "结果一致性6维核查：完整性、准确性、一致性、时效性、权限性、隐私性",
  "inputSchema": {
    "type": "object",
    "properties": {
      "result": { "type": "object" },
      "original_query": { "type": "string" },
      "context": { "type": "object" },
      "dimensions": { "type": "array", "items": { "type": "string", "enum": ["completeness","accuracy","consistency","timeliness","authorization","privacy"] } }
    },
    "required": ["result", "original_query"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "passed": { "type": "boolean" },
      "scores": { "type": "object", "properties": { "completeness": {"type":"number"}, "accuracy": {"type":"number"}, "consistency": {"type":"number"}, "timeliness": {"type":"number"}, "authorization": {"type":"number"}, "privacy": {"type":"number"} } },
      "overall_score": { "type": "number" },
      "issues": { "type": "array", "items": { "type": "string" } },
      "recommendation": { "type": "string" }
    }
  }
}
```

### 11.8.7 MCP 调用示例

```python
# 通过 MCP 协议调用（任何 MCP 客户端均可）
mcp_request = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 1,
    "params": {
        "name": "memory_probe",
        "arguments": { "query": "Q3 营收分析", "layers": ["L1", "L2"], "top_k": 5 }
    }
}
```

```bash
# MCP 工具发现
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```


---

## 11.9 Agent 间通信接口

> 7-Agent 协同的核心通信机制：共享黑板 + Team Room 消息。  
> **开源状态**：🟢 开源（接口定义 + 黑板数据结构）

### 11.9.1 黑板（Blackboard）读写接口

黑板是 AgentTeams 架构中的共享状态空间，所有 Agent 通过读写黑板协同工作。

#### POST /api/v1/blackboard/write

**功能**：向黑板写入数据。

```json
// 请求
{
  "agent_id": "memory_navigator",
  "key": "search_results",
  "value": { "query": "Q3营收分析", "results": ["..."], "confidence": 0.95 },
  "ttl_seconds": 300,
  "session_id": "string"
}

// 响应 200 OK
{
  "status": "success",
  "data": { "write_id": "wrt_001", "key": "search_results", "agent_id": "memory_navigator", "written_at": "2026-08-03T03:32:00Z", "expires_at": "2026-08-03T03:37:00Z" }
}
```

#### GET /api/v1/blackboard/read

**功能**：从黑板读取数据。

```
GET /api/v1/blackboard/read?key=search_results&session_id=sess_001
```

```json
// 响应 200 OK
{
  "status": "success",
  "data": {
    "key": "search_results",
    "value": { "query": "Q3营收分析", "results": ["..."], "confidence": 0.95 },
    "written_by": "memory_navigator",
    "written_at": "2026-08-03T03:32:00Z",
    "ttl_remaining_seconds": 240
  }
}
```

#### GET /api/v1/blackboard/snapshot

**功能**：获取当前黑板完整快照（供 Leader 评估完整度）。

```json
{
  "status": "success",
  "data": {
    "session_id": "sess_001",
    "entries": {
      "task_type": { "value": "query", "written_by": "privacy_guardian" },
      "user_query": { "value": "分析Q3营收", "written_by": "privacy_guardian" },
      "search_results": { "value": { "results": ["..."], "confidence": 0.95 }, "written_by": "memory_navigator" },
      "cipher_id": { "value": "cph_abc", "written_by": "cipher_generator" },
      "permissions_ok": { "value": true, "written_by": "policy_enforcer" },
      "audit_id": { "value": "aud_001", "written_by": "audit_logger" },
      "validation": { "value": { "passed": true, "overall_score": 0.93 }, "written_by": "validator" }
    },
    "completeness": 0.85,
    "snapshot_at": "2026-08-03T03:32:05Z"
  }
}
```

#### DELETE /api/v1/blackboard/clear

**功能**：清空当前会话黑板。

```
DELETE /api/v1/blackboard/clear?session_id=sess_001
// 响应: { "status": "success", "data": { "cleared_keys": 7 } }
```

### 11.9.2 Team Room 消息接口

Team Room 是 Agent 间的异步消息通道，支持 Leader 发布任务、Worker 汇报结果。

#### POST /api/v1/team-room/send

**功能**：向 Team Room 发送消息。

```json
// 请求
{
  "from_agent": "privacy_guardian",
  "to_agent": "memory_navigator",
  "message_type": "task_assignment",
  "payload": { "task": "search_memory", "query": "Q3营收数据", "layers": ["L1", "L2"], "priority": "high" },
  "session_id": "sess_001"
}

// 响应 200 OK
{ "status": "success", "data": { "message_id": "msg_001", "delivered_at": "2026-08-03T03:32:00Z" } }
```

#### GET /api/v1/team-room/messages

**功能**：获取 Agent 的待处理消息。

```
GET /api/v1/team-room/messages?agent_id=memory_navigator&session_id=sess_001&limit=10
```

```json
{
  "status": "success",
  "data": {
    "messages": [
      {
        "message_id": "msg_001",
        "from_agent": "privacy_guardian",
        "message_type": "task_assignment",
        "payload": { "task": "search_memory", "query": "Q3营收数据" },
        "sent_at": "2026-08-03T03:32:00Z",
        "status": "pending"
      }
    ],
    "total_pending": 1
  }
}
```

#### POST /api/v1/team-room/ack

**功能**：确认消息已处理。

```json
// 请求: { "message_id": "msg_001", "agent_id": "memory_navigator", "result": "success" }
// 响应: { "status": "success", "data": { "message_id": "msg_001", "acked_at": "..." } }
```

---

## 11.10 Skill 调用 API 示例

> 以下展示 6 个 Skill 各自的完整调用流程。

### 11.10.1 PrivacyShield — 动态加密

```python
# REST API 调用
response = client.agents.invoke(
    agent_id="cipher_generator",
    skill="PrivacyShield",
    input={
        "data": "公司Q3营收420万美元",
        "privacy_level": "high",
        "session_id": "sess_001"
    }
)
# 返回: encrypted_data, cipher_id, expires_at

# MCP 调用
mcp_request = {"jsonrpc":"2.0","method":"tools/call","id":1,
    "params":{"name":"privacy_shield","arguments":{"data":"公司Q3营收420万美元","privacy_level":"high"}}}
```

### 11.10.2 MemoryProbe — 五层检索

```python
response = client.agents.invoke(
    agent_id="memory_navigator",
    skill="MemoryProbe",
    input={
        "query": "Q3营收趋势分析",
        "layers": ["L1", "L2", "L2.5"],
        "top_k": 10,
        "privacy_level": "high"
    }
)
# 返回: results[{content, layer, score}], layers_accessed, total_results

# MCP 调用
mcp_request = {"jsonrpc":"2.0","method":"tools/call","id":1,
    "params":{"name":"memory_probe","arguments":{"query":"Q3营收趋势分析","layers":["L1","L2","L2.5"]}}}
```

### 11.10.3 DataFusion — 多源融合

```python
response = client.agents.invoke(
    agent_id="data_coordinator",
    skill="DataFusion",
    input={
        "sources": [
            {"source_id": "memory_search", "data": {"results": ["..."]}, "confidence": 0.95},
            {"source_id": "external_api", "data": {"results": ["..."]}, "confidence": 0.80}
        ],
        "fusion_strategy": "weighted"
    }
)
# 返回: fused_result, confidence, sources_used, conflicts_resolved
```

### 11.10.4 AccessControl — 权限验证

```python
response = client.agents.invoke(
    agent_id="policy_enforcer",
    skill="AccessControl",
    input={
        "user_id": "user_001",
        "resource": "/api/v1/query",
        "action": "read",
        "data_classification": "confidential"
    }
)
# 返回: allowed(bool), reason, applied_policies, audit_id
```

### 11.10.5 AuditTrail — 审计日志

```python
response = client.agents.invoke(
    agent_id="audit_logger",
    skill="AuditTrail",
    input={
        "event_type": "query",
        "actor": "user_001",
        "resource": "/api/v1/query",
        "detail": {"query": "Q3营收分析", "privacy_level": "high"},
        "result": "success"
    }
)
# 返回: audit_id, timestamp, chain_hash
```

### 11.10.6 ResultVerify — 6维核查

```python
response = client.agents.invoke(
    agent_id="validator",
    skill="ResultVerify",
    input={
        "result": {
            "response": "Q3营收分析结果...",
            "sources": ["L1", "L2"],
            "tokens_used": 500
        },
        "original_query": "分析Q3营收趋势",
        "context": {"blackboard_state": {...}},
        "dimensions": ["completeness","accuracy","consistency","timeliness","authorization","privacy"]
    }
)
# 返回: passed(bool), scores{6维}, overall_score, issues, recommendation
```

---

## 11.11 RESTful API 设计原则

### 标准HTTP方法

| 方法 | 用途 | 幂等性 | 示例 |
|-----|------|--------|------|
| **GET** | 获取资源 | ✅ | GET /api/v1/config |
| **POST** | 创建资源/执行操作 | ❌ | POST /api/v1/query |
| **PUT** | 更新资源（完整） | ✅ | PUT /api/v1/config |
| **PATCH** | 更新资源（部分） | ❌ | PATCH /api/v1/plugins/{id} |
| **DELETE** | 删除资源 | ✅ | DELETE /api/v1/plugins/unload |

### URL设计规范

1. 使用小写字母和连字符（kebab-case）
2. 资源名使用复数形式
3. 层级不超过3层
4. 版本号放在路径开头（/api/v1）

```
✅ GET  /api/v1/plugins
✅ POST /api/v1/plugins/load
✅ GET  /api/v1/metrics/summary
❌ GET  /api/v1/Plugin          // 应使用小写
❌ POST /api/v1/loadPlugin      // 应使用名词+动词
```

### 版本控制

**策略**：URL路径版本控制（/api/v1, /api/v2）

- **小版本更新**（v1.0 → v1.1）：向后兼容，只增加新字段
- **大版本更新**（v1 → v2）：可能不兼容，保留旧版本API 6个月

---

## 11.12 错误码规范

### 错误响应格式

```json
{
  "status": "error",
  "error": {
    "code": "AUTH_001",
    "message": "Invalid API key",
    "details": "The provided API key is expired or invalid",
    "timestamp": "2026-08-03T03:32:00Z",
    "request_id": "req_abc123"
  }
}
```

### 错误码列表

#### 认证错误（AUTH_xxx）

| 错误码 | HTTP状态码 | 说明 | 解决方案 |
|--------|----------|------|---------|
| AUTH_001 | 401 | API key无效 | 检查API key是否正确 |
| AUTH_002 | 401 | API key过期 | 重新生成API key |
| AUTH_003 | 403 | 权限不足 | 升级账户或联系管理员 |
| AUTH_004 | 429 | 请求频率超限 | 降低请求频率或升级套餐 |

#### 请求错误（REQ_xxx）

| 错误码 | HTTP状态码 | 说明 | 解决方案 |
|--------|----------|------|---------|
| REQ_001 | 400 | 请求参数缺失 | 检查必填参数 |
| REQ_002 | 400 | 参数类型错误 | 检查参数类型 |
| REQ_003 | 400 | 参数值超出范围 | 调整参数值 |
| REQ_004 | 413 | 请求体过大 | 减少请求内容 |

#### 资源错误（RES_xxx）

| 错误码 | HTTP状态码 | 说明 | 解决方案 |
|--------|----------|------|---------|
| RES_001 | 404 | 资源不存在 | 检查资源ID |
| RES_002 | 409 | 资源冲突 | 删除旧资源或使用新ID |
| RES_003 | 410 | 资源已删除 | 创建新资源 |

#### 系统错误（SYS_xxx）

| 错误码 | HTTP状态码 | 说明 | 解决方案 |
|--------|----------|------|---------|
| SYS_001 | 500 | 内部服务器错误 | 联系技术支持 |
| SYS_002 | 503 | 服务暂时不可用 | 稍后重试 |
| SYS_003 | 504 | 请求超时 | 减少max_tokens或重试 |
| SYS_004 | 507 | 内存不足 | 等待系统恢复或联系支持 |

#### 插件错误（PLG_xxx）

| 错误码 | HTTP状态码 | 说明 | 解决方案 |
|--------|----------|------|---------|
| PLG_001 | 400 | 插件文件无效 | 检查插件文件格式 |
| PLG_002 | 409 | 插件已加载 | 先卸载旧插件 |
| PLG_003 | 500 | 插件加载失败 | 检查插件兼容性 |
| PLG_004 | 404 | 插件不存在 | 检查plugin_id |

#### 隐私错误（PRI_xxx）

| 错误码 | HTTP状态码 | 说明 | 解决方案 |
|--------|----------|------|---------|
| PRI_001 | 403 | 密码已过期 | 系统自动重新生成 |
| PRI_002 | 403 | 会话验证失败 | 检查session_id |
| PRI_003 | 500 | 加密失败 | 联系技术支持 |

#### 导师模型错误（MENTOR_xxx）

| 错误码 | HTTP状态码 | 说明 | 解决方案 |
|--------|----------|------|---------|
| MENTOR_001 | 400 | 检测到敏感数据 | 抽象化后重试 |
| MENTOR_002 | 429 | 咨询频率超限 | 降低咨询频率 |
| MENTOR_003 | 500 | 导师模型不可用 | 稍后重试 |
| MENTOR_004 | 408 | 导师推理超时 | 简化问题或重试 |

#### Agent 通信错误（AGENT_xxx）

| 错误码 | HTTP状态码 | 说明 | 解决方案 |
|--------|----------|------|---------|
| AGENT_001 | 404 | Agent不存在 | 检查agent_id |
| AGENT_002 | 409 | Agent不可用 | 检查Agent状态 |
| AGENT_003 | 400 | Skill不匹配 | 检查Skill名称 |
| AGENT_004 | 504 | Agent调用超时 | 增加timeout_ms或重试 |
| AGENT_005 | 400 | 黑板键不存在 | 检查key名称 |
| AGENT_006 | 408 | Team Room消息超时 | 重试或检查目标Agent |

### 错误处理最佳实践

#### 1. 客户端重试策略

```python
import time

def query_with_retry(client, query, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.query(query)
        except client.errors.RateLimitError:
            wait_time = 2 ** attempt
            time.sleep(wait_time)
        except client.errors.ServerError:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise
        except client.errors.ClientError:
            raise  # 4xx 错误不重试
```

#### 2. 优雅降级

```python
try:
    response = client.query(query="敏感分析", privacy_level="high")
except client.errors.ResourceError:
    response = client.query(query="敏感分析", privacy_level="medium")
```

---

## 11.13 完整 API 使用示例

### Python SDK 完整示例

```python
from selfbrain import Client
import logging

client = Client(api_key="sb_your_api_key", base_url="http://localhost:8080/api/v1", timeout=30)
logger = logging.getLogger(__name__)

def main():
    # 1. 健康检查
    health = client.health.check()
    if health.status != "healthy":
        logger.error("System not healthy")
        return

    # 2. 执行查询
    response = client.query(query="分析2026年Q3营收趋势", privacy_level="high", max_tokens=2000)
    logger.info(f"Response: {response.data.response}")
    logger.info(f"Tokens used: {response.data.tokens_used.total}")

    # 3. 调用 Agent（AgentTeams 模式）
    result = client.agents.invoke(
        agent_id="privacy_guardian",
        skill="PrivacyShield",
        input={"data": "敏感数据", "privacy_level": "high"}
    )
    logger.info(f"Encrypted: {result.data.output['cipher_id']}")

    # 4. 黑板读写
    client.blackboard.write(key="analysis_result", value={"data": response.data.response}, agent_id="privacy_guardian")
    snapshot = client.blackboard.snapshot(session_id="sess_001")
    logger.info(f"Blackboard completeness: {snapshot.data.completeness}")

    # 5. Team Room 消息
    client.team_room.send(
        from_agent="privacy_guardian",
        to_agent="memory_navigator",
        message_type="task_assignment",
        payload={"task": "deep_search", "query": "Q3详情"}
    )

    # 6. 加载插件
    plugin = client.plugins.load(plugin_type="navigator", plugin_path="./custom_navigator.pth")
    logger.info(f"Plugin loaded: {plugin.data.plugin_id}")

    # 7. 查询指标
    metrics = client.metrics.get()
    logger.info(f"Token saved: {metrics.data.tokens.tokens_saved_percent}%")

    # 8. 卸载插件
    client.plugins.unload(plugin_id=plugin.data.plugin_id)

if __name__ == "__main__":
    main()
```

### cURL 完整示例

```bash
#!/bin/bash
API_KEY="sb_your_api_key"
BASE_URL="http://localhost:8080/api/v1"

# 1. 健康检查
curl -s "${BASE_URL}/health" | jq '.'

# 2. 执行查询
curl -s -X POST "${BASE_URL}/query" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"query":"分析Q3营收","privacy_level":"high"}' | jq '.'

# 3. 调用 Agent
curl -s -X POST "${BASE_URL}/agents/invoke" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"memory_navigator","skill":"MemoryProbe","input":{"query":"Q3营收","layers":["L1","L2"]}}' | jq '.'

# 4. 黑板快照
curl -s -H "Authorization: Bearer ${API_KEY}" \
  "${BASE_URL}/blackboard/snapshot?session_id=sess_001" | jq '.'

# 5. Team Room 消息
curl -s -X POST "${BASE_URL}/team-room/send" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"from_agent":"privacy_guardian","to_agent":"memory_navigator","message_type":"task_assignment","payload":{"task":"search","query":"Q3"}}' | jq '.'

# 6. MCP 工具发现
curl -s -X POST "http://localhost:8080/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' | jq '.'
```

---

## 总结

本章详细说明了 SelfBrain v2.0 的完整 API 规格，包括：

### 原有功能（v1.0 继承）

✅ **统一查询接口**：支持同步/流式查询  
✅ **插件管理接口**：热加载自定义 MEMO  
✅ **配置接口**：灵活的系统配置  
✅ **监控接口**：完整的性能指标  
✅ **RESTful 设计**：标准化的 API 规范  
✅ **错误处理**：完善的错误码体系  
✅ **SDK 示例**：Python/JavaScript/cURL 全覆盖

### 新增功能（v2.0 AgentTeams 适配）

✅ **黑盒保护架构**：开源接口 + 闭源 SDK 三层分离  
✅ **Agent 调用接口**：7-Agent 注册、调用、查询  
✅ **Skill Schema 定义**：6-Skill 的 JSON Schema（全部开源）  
✅ **MCP 工具接口**：6 个 Skill 全部暴露 MCP 标准接口  
✅ **黑板读写接口**：write/read/snapshot/clear 完整 CRUD  
✅ **Team Room 消息接口**：send/messages/ack 异步通信  
✅ **Skill 调用示例**：6 个 Skill 各自的 REST + MCP 调用示例  
✅ **新增错误码**：AGENT_xxx 系列覆盖 Agent 通信场景

### API 开源/闭源状态汇总

| API 类别 | 开源状态 | 说明 |
|---------|---------|------|
| 统一查询 / 插件管理 / 配置 / 监控 | 🟢 开源 | 接口定义完全开放 |
| 导师模型接口 | 🟢 开源 / 🔒 闭源 | 接口开放，安全检测算法闭源 |
| Agent 调用接口 | 🟢 开源 | invoke / list 完全开放 |
| Skill Schema（JSON） | 🟢 开源 | 6 个 Skill Schema 全部开源 |
| Skill Wrapper（Python） | 🟢 开源 | 薄层验证代码开源 |
| MCP 工具接口 | 🟢 开源 | JSON Schema 描述完全开放 |
| 黑板 / Team Room 接口 | 🟢 开源 | 通信协议完全开放 |
| Core SDK（.so/.dll） | 🔒 闭源 | 加密/检索/权限/审计引擎不暴露 |

**关键特性**：
- 🔒 银行级隐私保护（动态加密）
- 💰 70-80% Token 节约
- ⚡ <200ms 响应时间
- 🔌 热插拔插件系统
- 📊 实时性能监控
- 🤖 7-Agent 协同（AgentTeams 黑板模式）
- 🛡️ 黑盒保护（6-24 个月追赶窗口）
- 🔗 MCP 标准协议支持

---

## 上一章 / 下一章

← [第10章：插件架构实现](./10-插件架构实现.md)  
→ [第12章：性能优化](./12-性能优化.md)
