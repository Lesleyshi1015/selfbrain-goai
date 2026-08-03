# SelfBrain × AgentTeams 黑盒适配方案（续）

**版本**: v1.0  
**日期**: 2026-08-03  
**评估Agent**: Craft Agent

---

## 5. 13天行动计划（续）

### 5.4 风险缓解（续）

```
风险2: Skill 设计不合理
├─ 概率：30%
├─ 影响：中
└─ 缓解：
    ├─ 参考 Memory Palace 的 6-Skill 设计
    ├─ 复用 SelfBrain 已有能力
    └─ 如果时间不够，减少 Skill 数量（最少 3 个）

风险3: PPT 质量不高
├─ 概率：20%
├─ 影响：中
└─ 缓解：
    ├─ 参考 Memory Palace 的 PPT 结构
    ├─ 突出差异化优势（隐私保护+Token优化）
    └─ 使用专业设计模板
```

---

## 6. 最终建议（更新版）

### 6.1 决策矩阵（更新）

| 方案 | 参赛概率 | 进入复赛概率 | 获奖概率 | 风险 | 建议 |
|------|---------|------------|---------|------|------|
| **A: 不参赛** | 0% | 0% | 0% | 低 | ⭐⭐⭐ 保守但安全 |
| **B: 激进调整** | 100% | 40% | 15% | 高 | ⭐⭐ 高风险高回报 |
| **C: 务实参赛（推荐）** | 100% | **60%** | **25%** | 中 | ⭐⭐⭐⭐⭐ 推荐 |

### 6.2 最终建议：推荐参赛（方案C升级版）

```
核心策略：借鉴 Memory Palace 成熟模板，快速适配 SelfBrain

1. 项目重新定位：
   ├─ 从"AI隐私保护中间层"
   └─ 到"隐私保护的多Agent协同系统"

2. Agent 架构设计：
   ├─ 从"4组件"
   └─ 到"7-Agent"（Privacy Guardian + 5 Workers + Validator）

3. Skill 体系设计：
   ├─ 从"插件系统"
   └─ 到"6-Skill"（PrivacyShield + MemoryProbe + DataFusion + AccessControl + AuditTrail + ResultVerify）

4. 黑盒保护策略：
   ├─ 开源：Agent 调用逻辑 + Skill Schema + Skill Wrapper + API 接口
   └─ 闭源：Core SDK + 核心算法 + 模型权重 + 性能优化

5. 差异化优势：
   ├─ 银行级动态加密（行业领先）
   ├─ Token 优化（70-80% 节约）
   ├─ 本地运行（数据不出本地）
   └─ 黑盒保护（6-24 个月追赶时间）
```

### 6.3 预期结果

```
最佳情况（20%概率）：
├─ 进入复赛（Top30）
├─ 获得赛道奖项
└─ 项目知名度大幅提升

中性情况（50%概率）：
├─ 参与奖或开源影响力奖
├─ 获得评委反馈
└─ 项目改进方向明确

最差情况（30%概率）：
├─ 未进入复赛
├─ 但获得宝贵经验
└─ 为下次参赛积累基础
```

### 6.4 长期价值

```
无论是否获奖，参赛都有以下价值：

1. 项目重新定位：
   ├─ 从"隐私保护中间层"到"隐私保护的Agent基础设施"
   └─ 打开新的市场机会

2. 技术架构升级：
   ├─ 从"4组件"到"7-Agent"
   └─ 更符合行业趋势

3. 商业模式完善：
   ├─ 从"单点产品"到"平台生态"
   └─ 更有商业价值

4. 团队能力提升：
   ├─ 学习 AgentTeams 框架
   ├─ 理解多Agent协同设计
   └─ 积累赛事经验

5. 社区建设：
   ├─ 开源接口，建立社区
   ├─ 闭源核心，保护竞争力
   └─ 形成生态壁垒
```

---

## 7. 附录

### 7.1 SelfBrain × Memory Palace 映射表

| Memory Palace 概念 | SelfBrain 对应 | 映射方式 |
|-------------------|---------------|---------|
| Curator（Team Leader） | Privacy Guardian | 直接映射：都是总调度 |
| L1 Worker | Memory Navigator (L1模式) | 部分映射：Navigator 处理所有层级 |
| L2 Worker | Memory Navigator (L2模式) | 部分映射：Navigator 处理所有层级 |
| L2.5 Worker | Memory Navigator (L2.5模式) | 部分映射：Navigator 处理所有层级 |
| L2.7 Worker | Memory Navigator (L2.7模式) | 部分映射：Navigator 处理所有层级 |
| L3 Worker | Memory Navigator (L3模式) | 部分映射：Navigator 处理所有层级 |
| Validator | Validator | 直接映射：都是结果验证 |
| AlertFusion Skill | PrivacyShield Skill | 重新设计：从告警归并到隐私保护 |
| ImpactMapping Skill | MemoryProbe Skill | 重新设计：从影响面到知识检索 |
| LogTraceRca Skill | DataFusion Skill | 重新设计：从根因分析到数据融合 |
| RunbookRag Skill | AccessControl Skill | 重新设计：从Runbook到权限控制 |
| IncidentMemory Skill | AuditTrail Skill | 重新设计：从事故记忆到审计日志 |
| CaseRetrieval Skill | ResultVerify Skill | 重新设计：从案例检索到结果验证 |

### 7.2 关键技术指标对比

| 指标 | Memory Palace | SelfBrain | 对比 |
|------|---------------|-----------|------|
| Agent 数量 | 7 | 7 | 持平 |
| Skill 数量 | 6 | 6 | 持平 |
| Token 节约 | 98.8% | 70-80% | MP 更优 |
| 安全级别 | 企业级 | 银行级 | SB 更优 |
| 本地运行 | 支持 | 支持 | 持平 |
| 追赶时间 | 6-24月 | 6-24月 | 持平 |
| 开源策略 | 接口开源 | 接口开源 | 持平 |

### 7.3 参赛材料清单

```
初赛必交材料：
├─ 作品简介（500字以内）
│   ├─ 项目名称：SelfBrain - 隐私保护的多Agent协同系统
│   ├─ 问题与场景：企业使用AI的数据隐私担忧
│   ├─ 核心解决方案：7-Agent架构 + 6-Skill体系 + 黑盒保护
│   ├─ 创新点：银行级动态加密 + Token优化 + 本地运行
│   ├─ 开放/复用价值：开源接口，闭源核心，6-24月追赶时间
│   └─ 当前进展：完善的架构设计和部署方案
│
└─ 方案PPT
    ├─ 场景与价值：财务分析场景的真实痛点
    ├─ 方案设计：7-Agent架构、Skill体系、黑盒保护
    ├─ Skill与工具集成：6-Skill设计、MCP接口、RAG实现
    └─ 可行性与落地计划：13天行动计划、风险缓解
```

### 7.4 关键引用

#### Memory Palace 适配策略

> "黑板模式（Team Room + 共享黑板 + 轮番喊人）：7 个 Agent：1 个 Curator（Team Leader）+ 5 个 Layer Workers + 1 个 Validator"

> "黑盒保护架构（四层隔离）：开源：Agent 调用逻辑 + Skill Schema（JSON）+ Skill Wrapper（Python薄层）+ API 接口定义；闭源：Core SDK（.so/.dll 二进制），所有核心算法、权重、阈值、模型架构"

> "Skill = Schema + Wrapper + SDK 三层：Schema（JSON）：输入输出格式 → 开源；Wrapper（Python）：薄薄一层参数验证 + 调用 API → 开源；SDK（闭源黑盒）：所有核心算法 → 不开放"

#### GOAI 赛道要求

> "参赛作品应围绕真实企业场景，设计不少于3个不同职能的Agent的完整闭环方案，并将关键能力沉淀为可复用Skill"

> "多Agent设计必须以AgentTeams作为协同设计基点，说明角色编排、任务拆解、上下文传递、协同执行与状态追踪如何映射到该框架能力"

---

## 8. 总结

### 8.1 核心变化

```
从原评估到新评估：

1. 赛道匹配度：60% → 85%（+25%）
   ├─ 从"4组件"到"7-Agent"
   ├─ 从"插件系统"到"6-Skill"
   └─ 从"隐私保护中间层"到"隐私保护的多Agent协同系统"

2. 评审标准得分：55.5/100 → 78/100（+22.5）
   ├─ 多Agent协同：5/10 → 8/10（+3）
   ├─ Skill工程体系：4/10 → 7/10（+3）
   └─ 开放/开源贡献：3/10 → 7/10（+4）

3. 时间线可行性：40% → 70%（+30%）
   ├─ 借鉴 Memory Palace 成熟模板
   ├─ 复用 SelfBrain 已有能力
   └─ 聚焦初赛材料（不做代码实现）

4. 材料充分度：30% → 65%（+35%）
   ├─ Agent架构设计完善
   ├─ Skill体系设计完善
   └─ 场景演示设计完善

5. 最终建议：谨慎参赛 → 推荐参赛（✅ 升级）
```

### 8.2 关键成功因素

```
成功参赛的关键：

1. 快速学习 AgentTeams 框架
   ├─ 阅读官方文档
   ├─ 参考 Memory Palace 映射方式
   └─ 简化映射（只做概念设计）

2. 保持 SelfBrain 特色
   ├─ 隐私保护（银行级动态加密）
   ├─ Token 优化（70-80% 节约）
   └─ 本地运行（数据不出本地）

3. 借鉴 Memory Palace 模板
   ├─ 黑板模式（Team Room + 共享黑板）
   ├─ 黑盒保护（开源接口，闭源核心）
   └─ Skill 三层架构（Schema + Wrapper + SDK）

4. 聚焦初赛材料
   ├─ 500 字简介（突出差异化）
   ├─ 方案 PPT（详细设计）
   └─ 不做代码实现（降低风险）
```

### 8.3 最终结论

```
基于 Memory Palace 的成熟模板，SelfBrain 的参赛可行性大幅提升：

✅ 赛道匹配度：60% → 85%（符合要求）
✅ 评审标准：55.5/100 → 78/100（中上水平）
✅ 时间线：40% → 70%（可行）
✅ 材料充分度：30% → 65%（基本满足）
✅ 最终建议：谨慎参赛 → 推荐参赛

核心价值：
1. 项目重新定位：从"隐私保护中间层"到"隐私保护的Agent基础设施"
2. 技术架构升级：从"4组件"到"7-Agent"
3. 商业模式完善：从"单点产品"到"平台生态"
4. 团队能力提升：学习 AgentTeams，理解多Agent协同

建议行动：
1. 立即开始 13 天行动计划
2. 借鉴 Memory Palace 成熟模板
3. 保持 SelfBrain 隐私保护特色
4. 聚焦初赛材料（500字简介 + 方案PPT）
5. 目标：参与奖 + 项目曝光 + 学习经验
```

---

**报告完成时间**：2026-08-03 11:13 GMT+8  
**评估Agent**：Craft Agent  
**数据来源**：SelfBrain 项目文档、GOAI 参赛手册、Memory Palace AgentTeams 适配方案 v3.0
