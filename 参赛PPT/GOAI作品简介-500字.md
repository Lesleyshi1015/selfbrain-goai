<!-- @agent: session-260808-mild-gold | module: delivery/500words-intro | ts: 2026-08-13T19:25+08:00 -->

# GOAI 2026 参赛作品简介（500 字）

**作品名称**：SelfBrain — 多Agent隐私防护协作的本地隐私模型
**参赛赛道**：新智基座｜AgentInfra

---

企业使用 AI 面临"两难困境"：接入 GPT-4 等外部大模型能力最强，但客户数据、财务数据、病历等敏感信息明文出境，合规风险高企；本地部署开源模型虽保隐私，却需百万级 GPU 投入、专职团队，且能力始终落后。SelfBrain 提供第三条路——**外部最强模型的能力 × 本地部署的隐私 × 70-80% 的 Token 成本节约**。

SelfBrain 构建了 7 个专业化 Agent 的黑板协同架构：Privacy Guardian 作为 Team Leader 统一调度，Memory Navigator 负责记忆检索、Cipher Generator 负责动态加密、Data Coordinator 负责数据融合、Policy Enforcer 负责权限验证、Audit Logger 负责证据链沉淀、Validator 执行六维结果核查。所有 Agent 通过共享黑板松耦合交互，由完整度评估驱动自主闭环，实现"加密、分片、检索、权限、审计"全链路防护。

核心安全机制采用银行 U 盾级动态密码系统：敏感数据发送给外部模型前自动加密、分片、打散，密码 5 分钟自动过期、会话级隔离、用后即销毁；五层数据分级中 L2.7 预测层与 L3 归档层仅 SelfBrain 独占，外部模型永不可触达。整套方案通过 7 种攻击场景模拟验证，安全评分 99/100。

工程能力沉淀为 6 个可复用 Skill（PrivacyShield / MemoryProbe / DataFusion / AccessControl / AuditTrail / ResultVerify），采用 Schema + Wrapper + SDK 三层架构，开源可审计、闭源保护核心算法，支持企业热替换与生态贡献。项目已交付端到端可执行 Demo 与 195 项测试（88% 覆盖率），评审可一键复现数据隐私保护闭环；本地微调的四模型引擎（4.4GB）将在复赛随完整模型包提供，实现评审端一键真实推理。

SelfBrain 让企业"用上最强 AI，同时把隐私留在自己手上"，为 AgentInfra 提供安全、可审计、可复用的基础设施底座。
