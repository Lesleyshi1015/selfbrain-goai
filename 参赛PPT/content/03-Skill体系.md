# SelfBrain GOAI 参赛PPT — 第10-14页：Skill工程体系与生态复用

**文档版本**: v1.0  
**生成日期**: 2026-08-03  
**对应评审维度**: Skill工程体系与生态复用（25%权重）

---

## 第10页：6-Skill 体系总览

### 页面标题
**6个可复用Skill — 沉淀核心能力，构建生态基石**

### 核心内容

SelfBrain 将7-Agent协同系统的核心能力沉淀为 **6个可复用Skill**，每个Skill对应一个Worker Agent，采用统一的 **Schema + Wrapper + SDK** 三层架构设计。

#### Skill 清单总览

| Skill 名称 | 核心功能 | 对应 Agent | 安全等级 |
|-----------|---------|-----------|---------|
| **PrivacyShield** | 银行级动态加密 | Cipher Generator | ⭐⭐⭐⭐⭐ |
| **MemoryProbe** | 通用记忆检索（Memory Adapter） | Memory Navigator | ⭐⭐⭐⭐ |
| **DataFusion** | 多源数据融合 | Data Coordinator | ⭐⭐⭐ |
| **AccessControl** | 分层权限验证 | Policy Enforcer | ⭐⭐⭐⭐⭐ |
| **AuditTrail** | 审计日志+证据链 | Audit Logger | ⭐⭐⭐⭐ |
| **ResultVerify** | 结果一致性6维核查 | Validator | ⭐⭐⭐ |

#### MemoryProbe Skill 特别说明

MemoryProbe 是 SelfBrain **通用AgentInfra定位**的核心体现：

```
MemoryProbe Skill 特点：
├─ 通用接口：支持任意记忆系统后端
├─ 适配器路由：SimpleFile / VectorDB / MemoryPalace
├─ 开源接口：Schema + Wrapper 开源
└─ 增值选项：Memory Palace 五层架构（闭源SDK）
```

#### 核心价值主张

```
✅ 跨项目复用 — 一次开发，多处使用
✅ 标准化接口 — JSON Schema 定义清晰边界
✅ 社区可贡献 — 开源层完全透明可审计
✅ 企业可定制 — Wrapper层可替换实现
✅ 零门槛入门 — SimpleFileAdapter 开箱即用
```

### 视觉设计建议

- **布局**: 6宫格卡片布局，每个Skill一个卡片
- **配色**: 每个Skill使用不同主题色（蓝/绿/橙/紫/青/红）
- **图标**: 每个Skill配专属图标（盾牌/放大镜/融合/锁/日志/勾选）
- **突出**: MemoryProbe 卡片加粗边框，标注"通用适配器核心"
- **底部**: 核心价值5条用绿色✅图标横向排列

---

## 第11页：三层架构设计

### 页面标题
**Schema + Wrapper + SDK — 开源接口与闭源核心的清晰边界**

### 核心内容

每个Skill采用 **三层架构**，实现开源与闭源的清晰分离，既满足GOAI赛道开源要求，又保护核心竞争力。

#### 架构分层详解

```
┌─────────────────────────────────────────────────────────────┐
│  第1层：Schema层（开源 · JSON）                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ├─ 定义输入/输出格式                                       │
│  ├─ 定义能力边界和约束                                      │
│  ├─ 版本管理（v1.0, v2.0...）                              │
│  └─ 供外部开发者了解和对接                                  │
│  🟢 开源状态：完全开源，社区可贡献                          │
├─────────────────────────────────────────────────────────────┤
│  第2层：Wrapper层（开源 · Python）                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ├─ 参数验证（类型检查、范围校验）                          │
│  ├─ 错误处理（异常捕获、重试逻辑）                          │
│  ├─ 调用SDK API（FFI/IPC）                                 │
│  └─ 可替换实现（企业可自定义Wrapper）                       │
│  🟢 开源状态：完全开源，可替换扩展                          │
├─────────────────────────────────────────────────────────────┤
│  第3层：SDK层（闭源 · .so/.dll）                            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ├─ 核心算法实现（加密、检索、融合）                        │
│  ├─ 模型权重（Navigator/Cipher/Coordinator）               │
│  ├─ 性能优化参数                                            │
│  └─ 商业增值逻辑（Memory Palace五层引擎）                   │
│  🔴 闭源状态：二进制保护，6-24个月追赶窗口                  │
└─────────────────────────────────────────────────────────────┘
```

#### 调用流程示意

```
开发者调用 → Schema验证 → Wrapper封装 → SDK执行 → 返回结果
              (开源)        (开源)       (闭源)
```

#### 开源/闭源边界对照表

| 层级 | 内容 | 语言/格式 | 开源状态 | 社区价值 |
|------|------|----------|---------|---------|
| **Schema** | 输入输出规范 | JSON Schema | 🟢 开源 | 可审计、可对接 |
| **Wrapper** | 参数验证+调用 | Python | 🟢 开源 | 可替换、可扩展 |
| **SDK** | 核心算法 | .so/.dll | 🔴 闭源 | 黑盒保护 |

### 视觉设计建议

- **布局**: 三层堆叠图，从上到下依次排列
- **配色**: 
  - Schema层：绿色背景（#4CAF50）标注"开源"
  - Wrapper层：蓝色背景（#2196F3）标注"开源"
  - SDK层：红色背景（#F44336）标注"闭源"
- **箭头**: 从上到下的调用箭头，标注"FFI/IPC"
- **右侧**: 开源/闭源边界对照表
- **底部**: 技术护城河说明："6-24个月追赶窗口"

---

## 第12页：Skill 调用示例

### 页面标题
**Skill 调用实战 — PrivacyShield 与 MemoryProbe 示例**

### 核心内容

#### 示例一：PrivacyShield Skill 调用

**Schema 定义（PrivacyShield.schema.json）**

```json
{
  "name": "PrivacyShield",
  "version": "1.0.0",
  "description": "银行级动态加密Skill",
  "input": {
    "type": "object",
    "required": ["data", "layer", "session_id"],
    "properties": {
      "data": {
        "type": "string",
        "description": "原始敏感数据"
      },
      "layer": {
        "type": "string",
        "enum": ["L1", "L2", "L2.5", "L2.7", "L3"],
        "description": "数据所在层级"
      },
      "session_id": {
        "type": "string",
        "description": "会话ID，用于密码隔离"
      }
    }
  },
  "output": {
    "type": "object",
    "properties": {
      "encrypted": {
        "type": "string",
        "description": "加密后的数据"
      },
      "token": {
        "type": "string",
        "description": "解密令牌，5分钟TTL"
      },
      "expires_at": {
        "type": "string",
        "format": "date-time"
      }
    }
  }
}
```

**Python 调用代码**

```python
from selfbrain.skills.privacy_shield import PrivacyShieldWrapper

# 初始化Wrapper
shield = PrivacyShieldWrapper()

# 执行加密
result = shield.execute(
    data="2026年Q3营收: 420万元",
    layer="L2",
    session_id="session_abc123"
)

# 输出结果
print(f"加密后: {result['encrypted']}")
# → L2_AMOUNT_C3D9F2_T1722240900_SABC

print(f"令牌: {result['token']}")
# → tok_x7y8z9_5min_ttl

print(f"过期时间: {result['expires_at']}")
# → 2026-08-03T09:15:00Z
```

**密码结构解析**

```
标准格式：{TYPE}_{RANDOM}_{TIMESTAMP}_{SESSION}
示例：    AMOUNT_C3D9F2_T1722240900_S7A4B

分层格式：{LAYER}_{TYPE}_{RANDOM}_{TIMESTAMP}_{SESSION}
示例：    L2_REVENUE_8E2F91_T1722240905_S7A4B
```

---

#### 示例二：MemoryProbe Skill 调用（适配器切换）

**Schema 定义（MemoryProbe.schema.json）**

```json
{
  "name": "MemoryProbe",
  "version": "2.1",
  "description": "通用记忆检索Skill（支持任意记忆系统后端）",
  "input": {
    "type": "object",
    "required": ["query", "adapter_type"],
    "properties": {
      "query": {
        "type": "string",
        "description": "语义搜索查询"
      },
      "adapter_type": {
        "type": "string",
        "enum": ["simple_file", "vector_db", "memory_palace", "custom"],
        "description": "适配器类型"
      },
      "layers": {
        "type": "array",
        "items": {"type": "string"},
        "description": "检索层级（MemoryPalace专用）"
      },
      "top_k": {
        "type": "integer",
        "default": 5,
        "description": "返回结果数量"
      },
      "min_score": {
        "type": "number",
        "default": 0.3,
        "description": "最低相似度阈值"
      }
    }
  },
  "output": {
    "type": "object",
    "properties": {
      "results": {"type": "array"},
      "adapter_used": {"type": "string"},
      "latency_ms": {"type": "number"},
      "total_found": {"type": "integer"}
    }
  }
}
```

**Python 调用代码（适配器切换演示）**

```python
from selfbrain.skills.memory_probe import MemoryProbeWrapper
from selfbrain.adapters.router import AdapterRouter

# 初始化适配器路由器
router = AdapterRouter("config/adapters.yaml")
probe = MemoryProbeWrapper(router)

# ===== 场景1：个人开发者 — SimpleFileAdapter =====
result = probe.probe(
    query="2026年Q3营收",
    adapter_type="simple_file",
    top_k=5
)
print(f"本地文件搜索: 找到 {result['total_found']} 条结果")
# 延迟: <10ms，零依赖

# ===== 场景2：技术团队 — VectorDBAdapter =====
router.set_active("vector_db")  # 热切换，无需重启
result = probe.probe(
    query="上季度财务表现",  # 语义搜索
    adapter_type="vector_db",
    top_k=5
)
print(f"向量数据库搜索: 延迟 {result['latency_ms']}ms")
# 延迟: <30ms

# ===== 场景3：企业用户 — MemoryPalaceAdapter =====
router.set_active("memory_palace")
result = probe.probe(
    query="分析2026年Q3营收趋势并预测Q4",
    adapter_type="memory_palace",
    layers=["L1", "L2", "L2.5", "L2.7"],  # 五层检索
    top_k=10
)
print(f"Memory Palace搜索: 找到 {result['total_found']} 条结果")
# 延迟: <50ms，含趋势预测

# ===== 黑板任务发布示例 =====
from selfbrain.teamroom.protocol import TeamRoomProtocol
protocol = TeamRoomProtocol(blackboard)

task_id = protocol.publish_task(
    task_type="retrieve",
    user_query="查找最近的会议记录",
    adapter_type="vector_db",
    layers=["L1", "L2"]
)
print(f"任务已发布到黑板: {task_id}")
```

**适配器性能对比**

| 适配器 | 延迟 | 依赖 | 开源状态 | 适用场景 |
|-------|------|------|---------|---------|
| SimpleFileAdapter | <10ms | 无 | ✅ 开源 | 个人开发者、快速验证 |
| VectorDBAdapter | <30ms | ChromaDB | ✅ 开源 | 技术团队、语义搜索 |
| MemoryPalaceAdapter | <50ms | SDK | 🔒 闭源 | 企业用户、五层架构 |

### 视觉设计建议

- **布局**: 左右分栏，左侧PrivacyShield，右侧MemoryProbe
- **代码块**: 使用深色背景 + 语法高亮（JetBrains Mono字体）
- **标注**: 关键代码行用箭头标注说明
- **底部**: 适配器性能对比表（三列）
- **动画**: 代码逐行高亮执行流程

---

## 第13页：开源策略与社区价值

### 页面标题
**开源接口 + 闭源核心 — 构建可持续的技术护城河**

### 核心内容

#### 开源范围（社区可复用）

```
🟢 开源内容（MIT / Apache 2.0 协议）

├─ Agent 调用逻辑
│  └─ 7个Agent的定义、调度流程、黑板交互协议
│
├─ Skill Schema（JSON格式）
│  └─ 6个Skill的输入输出规范、版本管理
│
├─ Skill Wrapper（Python薄层）
│  ├─ SimpleFileAdapter ✅
│  ├─ VectorDBAdapter ✅
│  ├─ CustomAdapter 模板 ✅
│  └─ 参数验证、错误处理、SDK调用封装
│
├─ API 接口定义
│  └─ RESTful API、WebSocket协议
│
└─ Team Room 通信协议
   └─ 黑板数据结构、状态流转、Task协议
```

#### 闭源保护（核心竞争力）

```
🔴 闭源内容（商业许可保护）

├─ Core SDK（.so/.dll 二进制）
│  ├─ 动态加密引擎（PrivacyShield核心）
│  ├─ 检索引擎 HNSW+BM25+RRF（MemoryProbe核心）
│  ├─ 融合算法核心（DataFusion核心）
│  ├─ 权限策略引擎（AccessControl核心）
│  ├─ 审计规则引擎（AuditTrail核心）
│  └─ 6维核查规则（ResultVerify核心）
│
├─ 模型权重
│  ├─ Privacy Guardian（3B参数）
│  ├─ Memory Navigator（1.5B参数）
│  ├─ Cipher Generator（1.5B参数）
│  └─ Data Coordinator（VibeThinker 3B）
│
├─ MemoryPalaceAdapter
│  └─ 五层检索引擎（L1→L2→L2.5→L2.7→L3）
│
└─ 性能优化参数
   └─ 量化配置、缓存策略、路由规则
```

#### 社区贡献路径

```
社区开发者贡献流程：

1. 阅读开源 Schema
   └─ 了解Skill输入输出规范

2. 开发自定义 Wrapper
   ├─ 替换现有Wrapper实现
   └─ 或开发新的适配器

3. 提交到社区仓库
   ├─ GitHub Pull Request
   └─ 通过CI/CD自动化测试

4. 成为认证Skill
   └─ 进入Skill市场，供他人使用
```

#### 技术护城河分析

| 维度 | 开源层 | 闭源层 | 追赶难度 |
|------|-------|-------|---------|
| **代码量** | ~5,000行 | ~50,000行 | 高 |
| **算法复杂度** | 参数验证 | 核心加密/检索 | 极高 |
| **模型训练** | 无 | 6B+参数微调 | 极高 |
| **数据积累** | 无 | 五层架构数据 | 高 |
| **时间窗口** | 即时可用 | **6-24个月** | - |

#### 开源协议矩阵

| 组件 | 协议 | 商业使用 | 修改分发 | 专利授权 |
|------|------|---------|---------|---------|
| Agent逻辑 | MIT | ✅ | ✅ | ✅ |
| Skill Schema | Apache 2.0 | ✅ | ✅ | ✅ |
| Wrapper层 | MIT | ✅ | ✅ | ✅ |
| Memory Adapter | MIT | ✅ | ✅ | ✅ |
| Core SDK | 商业许可 | ❌ | ❌ | ❌ |
| 模型权重 | 商业许可 | ❌ | ❌ | ❌ |

### 视觉设计建议

- **布局**: 左右对比图，左侧绿色"开源"，右侧红色"闭源"
- **开源侧**: 展开的文件夹图标，列出开源内容
- **闭源侧**: 锁住的保险箱图标，列出闭源内容
- **底部**: 社区贡献路径流程图（4步）
- **右下角**: 技术护城河表格，突出"6-24个月追赶窗口"

---

## 第14页：生态复用场景

### 页面标题
**Skill 跨场景复用 + Memory Adapter 灵活配置**

### 核心内容

SelfBrain 的6-Skill体系支持 **四种典型用户场景**，从个人开发者到企业客户，从零基础到专业部署，实现平滑升级路径。

---

#### 场景一：个人开发者 — 零门槛启动

```
┌─────────────────────────────────────────────────────────┐
│  👤 用户画像：独立开发者、学生、AI爱好者                 │
│  💰 成本：$0（完全免费）                                 │
│  ⏱️ 启动时间：<5分钟                                     │
└─────────────────────────────────────────────────────────┘

技术栈：
├─ SimpleFileAdapter（本地文件，开箱即用）
├─ PrivacyShield（基础加密保护）
├─ MemoryProbe（本地文件搜索）
└─ 3个外部AI API（免费额度）

使用示例：
$ pip install selfbrain
$ selfbrain init --adapter simple_file
$ selfbrain start

# 自动创建本地记忆目录
# ./memory/
#   ├── L1/
#   ├── L2/
#   └── config.yaml

核心价值：
✅ 零成本启动，无需任何外部依赖
✅ 5分钟完成环境配置
✅ 适合快速验证想法
```

---

#### 场景二：技术团队 — 复用已有基础设施

```
┌─────────────────────────────────────────────────────────┐
│  👥 用户画像：技术团队、创业公司、研发团队               │
│  💰 成本：$99/月（Pro版）                               │
│  ⏱️ 启动时间：<1小时                                    │
└─────────────────────────────────────────────────────────┘

技术栈：
├─ VectorDBAdapter（ChromaDB/Milvus）
├─ MemoryProbe（语义搜索）
├─ DataFusion（多源融合）
├─ 10+ AI API（GPT-4, Claude等）
└─ 高级加密（PrivacyShield Pro）

配置文件（adapter_config.yaml）：
adapters:
  vector_db:
    type: chromadb
    persist_directory: ./chroma_db
    collection: team_memories
    embedding_model: all-MiniLM-L6-v2

使用示例：
from selfbrain.adapters.router import AdapterRouter
router = AdapterRouter("adapter_config.yaml")
router.set_active("vector_db")

# 复用团队已有的ChromaDB基础设施
# 无需迁移数据，直接对接

核心价值：
✅ 复用已有向量数据库
✅ 语义搜索能力提升10倍
✅ 团队协作，共享记忆库
```

---

#### 场景三：金融风控 — 企业级合规部署

```
┌─────────────────────────────────────────────────────────┐
│  🏦 用户画像：金融机构、风控团队、合规部门               │
│  💰 成本：$499/月（企业版）                             │
│  ⏱️ 启动时间：1-2周（含合规审计）                        │
└─────────────────────────────────────────────────────────┘

技术栈：
├─ MemoryPalaceAdapter（五层架构）
├─ AccessControl（验证风控权限）
├─ PolicyEnforcer（分层权限）
├─ ResultVerify（核查风控结果）
├─ AuditTrail（完整证据链）
└─ 企业级权限管理（RBAC）

权限矩阵示例：
| 角色 | L1 | L2 | L2.5 | L2.7 | L3 |
|------|----|----|------|------|----|
| 分析师 | ✅ | ✅ | ✅ | ❌ | ❌ |
| 风控经理 | ✅ | ✅ | ✅ | ✅ | ❌ |
| 系统管理员 | ✅ | ✅ | ✅ | ✅ | ✅ |

合规特性：
├─ SOC 2 Type II 兼容
├─ GDPR/CCPA 数据保护
├─ 完整审计日志（不可篡改）
└─ 数据驻留控制（本地部署）

核心价值：
✅ 满足金融合规要求
✅ 五层权限精细控制
✅ 完整审计证据链
```

---

#### 场景四：医疗诊断 — 隐私保护与合规审计

```
┌─────────────────────────────────────────────────────────┐
│  🏥 用户画像：医疗机构、诊断系统、病历管理               │
│  💰 成本：$499/月（企业版）+ 定制开发                   │
│  ⏱️ 启动时间：2-4周（含HIPAA合规认证）                  │
└─────────────────────────────────────────────────────────┘

技术栈：
├─ MemoryPalaceAdapter（病历历史存储）
├─ CipherGenerator（加密敏感病历）
├─ AuditTrail（记录诊断过程）
├─ AccessControl（医生权限管理）
└─ ResultVerify（诊断结果核查）

诊断流程示例：
1. 医生查询："患者张三的既往病史"
2. MemoryProbe → 检索病历（L1/L2层）
3. CipherGenerator → 加密敏感信息
4. PolicyEnforcer → 验证医生权限
5. GPT-4 → 辅助诊断分析（仅看到加密数据）
6. Validator → 6维核查诊断建议
7. AuditTrail → 记录完整诊断过程

合规审计证据链：
├─ 谁（医生ID）在何时（时间戳）访问了哪些数据
├─ 使用了什么权限令牌（5分钟TTL）
├─ 诊断建议的6维核查评分
└─ 数据加密/解密完整记录

核心价值：
✅ HIPAA合规，病历数据不出院
✅ 完整诊断过程审计
✅ 6维核查保障诊断质量
```

---

#### Memory Adapter 核心价值总结

```
┌─────────────────────────────────────────────────────────┐
│  Memory Adapter 四大核心价值                            │
├─────────────────────────────────────────────────────────┤
│  ✅ 零门槛                                               │
│     SimpleFileAdapter 开箱即用，无需任何依赖             │
│                                                         │
│  ✅ 灵活切换                                             │
│     仅修改配置即可切换后端，无需改动业务代码             │
│                                                         │
│  ✅ 可扩展                                               │
│     社区可贡献新适配器，丰富生态                         │
│                                                         │
│  ✅ 平滑升级                                             │
│     从SimpleFile → VectorDB → MemoryPalace              │
│     数据无缝迁移，业务无感知                             │
└─────────────────────────────────────────────────────────┘
```

#### 场景对比矩阵

| 维度 | 个人开发者 | 技术团队 | 金融风控 | 医疗诊断 |
|------|-----------|---------|---------|---------|
| **适配器** | SimpleFile | VectorDB | MemoryPalace | MemoryPalace |
| **成本** | $0 | $99/月 | $499/月 | $499/月+ |
| **启动时间** | <5分钟 | <1小时 | 1-2周 | 2-4周 |
| **核心Skill** | PrivacyShield | MemoryProbe | AccessControl | AuditTrail |
| **合规等级** | 基础 | 标准 | 企业级 | HIPAA |
| **数据规模** | <1GB | <100GB | <10TB | <50TB |

### 视觉设计建议

- **布局**: 四象限布局，每个场景一个象限
- **配色**: 
  - 个人开发者：绿色（#4CAF50）
  - 技术团队：蓝色（#2196F3）
  - 金融风控：橙色（#FF9800）
  - 医疗诊断：紫色（#9C27B0）
- **图标**: 每个场景配专属图标（人/团队/银行/医院）
- **底部**: Memory Adapter四大核心价值（横向排列）
- **右下角**: 场景对比矩阵表格

---

## 附录：页面设计统一规范

### 字体规范
- **标题**: 思源黑体 Bold / Inter Bold，36-48px
- **副标题**: 思源黑体 Medium / Inter Medium，24-28px
- **正文**: 思源黑体 Regular / Inter Regular，16-18px
- **代码**: JetBrains Mono，14px

### 配色方案
- **主色**: 科技蓝 #2196F3
- **辅助色**: 
  - 安全绿 #4CAF50
  - 警告橙 #FF9800
  - 风险红 #F44336
  - 专业紫 #9C27B0
- **背景**: 深色渐变 #0A1628 → #1A2744

### 动画建议
- **页面切换**: 淡入淡出（300ms）
- **内容出现**: 从下往上滑入（400ms）
- **代码高亮**: 逐行点亮（200ms间隔）
- **数据强调**: 数字放大弹跳（500ms）

### 图标风格
- **类型**: 扁平化科技风
- **线条**: 2px描边
- **填充**: 单色填充，无渐变
- **来源**: Lucide Icons / Heroicons

---

**文档结束**

*本内容对应SelfBrain GOAI参赛PPT第10-14页，覆盖Skill工程体系与生态复用（评审权重25%）。*
