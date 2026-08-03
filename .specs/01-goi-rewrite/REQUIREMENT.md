# REQUIREMENT-001: SelfBrain-GOAI 全文档 AgentTeams 适配改写

## 用户故事

作为 GOAI 参赛项目的技术负责人，
我希望 15 章技术文档全部升级，融入 AgentTeams 适配方案，
以便提交初赛材料（500字简介 + 方案PPT）时能够展示完整的 AgentInfra 方案。

## 验收标准（AC）

### AC-1: 项目定位统一
- [ ] 所有文档的项目定位从"AI隐私保护中间层"统一为"隐私保护的多Agent协同系统"
- [ ] 关键词：AgentInfra、AgentTeams、多Agent协同、黑板模式、黑盒保护

### AC-2: 7-Agent 架构融入
- [ ] 02-核心架构.md：替换原有4组件架构图为7-Agent+黑板模式架构图
- [ ] 06-SelfBrain-Core.md：Core 升级为 Privacy Guardian（Team Leader）
- [ ] 03-MEMO-Navigator.md：Navigator 升级为 Memory Navigator（L1-L3 Worker）
- [ ] 04-MEMO-Cipher.md：Cipher 升级为 Cipher Generator（加密 Worker）
- [ ] 05-Data-Broker.md：Broker 升级为 Data Coordinator（数据融合 Worker）
- [ ] 10-插件架构.md：新增 Policy Enforcer + Audit Logger + Validator Worker

### AC-3: 6-Skill 体系设计
- [ ] 新增或更新章节说明 6-Skill 体系
- [ ] Skill = Schema(JSON) + Wrapper(Python) + SDK(闭源黑盒) 三层架构
- [ ] 每个 Skill 明确开源/闭源边界

### AC-4: 黑盒保护策略
- [ ] 所有文档明确标注开源/闭源边界
- [ ] 核心算法在 Core SDK（.so/.dll）中，不外泄
- [ ] Agent 调用逻辑、Skill Schema、Skill Wrapper 可开源

### AC-5: 场景演示
- [ ] 至少设计 1 个完整场景演示（查询+存储+验证闭环）
- [ ] 包含黑板状态变化 JSON
- [ ] 包含 Agent 协作序列图（Mermaid）

### AC-6: 赛道评分优化
- [ ] 文档内容直接对标 5 项评审标准
- [ ] 突出 Token 优化（70-80% 节约）和银行级加密

### AC-7: 文档完整性
- [ ] 15 章文档全部更新（不删旧结构，只升级内容）
- [ ] 文档编号不变
- [ ] 不破坏原有文档的已有章节结构

## 范围

**纳入改写**：docs/ 下全部 .md 技术文档
**不纳入**：.specs/ 目录下的文件、src/ tests/ 下的代码

## 参考材料

1. `research/tech-survey/2026-08-03-SelfBrain-黑盒AgentTeams适配方案-续.md`
2. `research/tech-survey/2026-08-03-GOAI参赛评估报告.md`
3. Memory Palace AgentTeams 适配方案 v3.0（黑板模式 + 7-Agent + 6-Skill + 黑盒保护）
