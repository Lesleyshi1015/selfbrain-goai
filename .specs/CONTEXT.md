# SelfBrain-GOAI 项目上下文

**最后更新**: 2026-08-03

---

## 项目概述

SelfBrain 是一个**多Agent隐私防护协作的本地隐私模型**，基于 7-Agent AgentTeams 架构，通过 Skill 体系和 Memory Adapter 适配器层，实现外部模型的"外脑"能力，同时保证用户数据隐私安全。

**口号**：接入你想用的任何外部先进大模型，但把隐私留在你的手上

**核心痛点**：企业面临两难困境——使用外部大模型则隐私暴露，本地部署则成本高昂。SelfBrain提供第三条路：用外部最强模型，但隐私留在自己手上。

**参赛赛道**: 阿里巴巴全球 AI 大赛 - 赛道一: 新智基座 | AgentInfra

---

## 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| 基础模型 | Qwen2.5-3B / 1.5B | Core 3B + Worker 1.5B |
| Agent 框架 | AgentTeams 黑板模式 | Team Room + 共享黑板 |
| 适配器层 | MemoryAdapter（开源） | 通用记忆系统接口 |
| Skill 体系 | Schema + Wrapper + SDK | 6-Skill 三层架构 |
| 向量数据库 | ChromaDB / Milvus | 可选后端 |
| 量化工具 | AutoGPTQ | INT4 量化 |
| 微调方法 | LoRA (r=16) | 持续学习 |
| 协议 | MCP | Model Context Protocol |

---

## 7-Agent 架构

| Agent | 角色 | 职责 | 映射原组件 |
|-------|------|------|-----------|
| Privacy Guardian | Team Leader | 总调度、黑板发布、完整度评估 | Core |
| Memory Navigator | Worker | Memory Adapter 路由 + 检索 | Navigator |
| Cipher Generator | Worker | 动态密码生成 + 加密 | Cipher |
| Data Coordinator | Worker | 多源数据融合 | Data Broker |
| Policy Enforcer | Worker | 分层权限验证 | 权限系统 |
| Audit Logger | Worker | 审计日志 + 证据链 | Dashboard |
| Validator | Worker | 结果一致性 6 维核查 | 新增 |

---

## 目录结构

```
F:/SelfBrain-GOAI/
├── .specs/                    # 规范文档
│   ├── 01-goi-rewrite/       # GOAI文档改写变更
│   ├── CONTEXT.md            # 本文件
│   ├── ARCHITECTURE.md       # 架构文档
│   ├── evolve/               # 架构沉淀
│   └── health/               # 健康巡检
├── archive/                  # 归档
├── docs/                     # 15章技术文档
├── src/                      # 源代码（开发阶段填充）
├── tests/                    # 测试（开发阶段填充）
├── scripts/                  # 脚本
├── research/                 # 研究资料
├── 参赛PPT/                  # 参赛演示材料
├── README.md
├── CHANGELOG.md
├── LESSONS.md
└── .gitignore
```

---

## 关键设计决策

1. **MemoryAdapter 通用接口** — Navigator 不绑定 Memory Palace，支持任意记忆系统
2. **开源/闭源边界** — Agent 调用逻辑 + Skill Schema + Wrapper 开源，Core SDK 闭源
3. **商业分层** — Community(免费) / Pro($99/月) / Enterprise($499/月，含MemoryPalaceAdapter)
4. **13天冲刺** — 2026-08-03 ~ 2026-08-16

---

## 参赛时间线

| 日期 | 任务 | 状态 |
|------|------|------|
| Day 1 (8/3) | 15章文档改写 + Memory Adapter | ✅ 完成 |
| Day 2-3 (8/4-5) | 参赛PPT | ⏳ 待开始 |
| Day 4 (8/6) | 500字产品介绍 | ⏳ 待开始 |
| Day 5-7 (8/7-9) | 代码框架 | ⏳ 待开始 |
| Day 8-10 (8/10-12) | Core SDK 封装 | ⏳ 待开始 |
| Day 11-12 (8/13-14) | 集成测试 + 场景演示 | ⏳ 待开始 |
| Day 13 (8/15-16) | 最终审查 + 提交 | ⏳ 待开始 |
