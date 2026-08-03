# CHANGE-001: SelfBrain → SelfBrain-GOAI 全文档改写

**日期**: 2026-08-03
**状态**: planning → in_progress
**发起人**: Lesley

## 变更背景

SelfBrain 项目决定参加 GOAI（阿里巴巴全球AI大赛）赛道一：新智基座 | AgentInfra。
需要在 13 天内（8月3日-8月16日）将现有 15 章技术文档从"AI隐私保护中间层"
重新定位为"隐私保护的多Agent协同系统"。

## 变更目标

1. 项目定位升级：AI隐私保护中间层 → 隐私保护的多Agent协同系统（AgentInfra）
2. 架构升级：4组件（Core+Navigator+Cipher+Broker） → 7-Agent + 6-Skill + 黑板模式
3. 融入 AgentTeams 适配方案：黑板模式、黑盒保护（开源接口+闭源SDK）
4. 15章文档全部升级，保持原有编号结构不变
5. 输出材料：500字作品简介 + 方案PPT

## 影响范围

- docs/ 目录下全部 15 章技术文档
- research/ 目录下所有研究报告
- README.md, CHANGELOG.md, LESSONS.md

## 不影响的

- SelfBrain 主项目（F:/SelfBrain/）保持原样，完全隔离
- .specs/ 目录下的 spec 文件
- src/ tests/ 目录下的代码

## 时间线

- Day 1 (8月3日): 文档改写（本任务）
- Day 2-3 (8月4-5日): PPT制作
- Day 4 (8月6日): 500字简介
- Day 5-13 (8月7-16日): 审查、迭代、提交
