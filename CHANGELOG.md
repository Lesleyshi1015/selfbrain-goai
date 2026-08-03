# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-08-01

### Added
- 初始化项目结构（dev-workflow 规范）
- 迁移 15 章技术规格文档
- 修复模型选择错误：
  - Core: Qwen2.5-3B → VibeThinker-3B FP16
  - Data Broker: 独立 0.5B 模型 → VibeThinker-3B INT4 量化版
  - 总参数量: 6.5B → ~5B
- 明确 MEMO 为训练方法论（非具体模型）
- MEMO base 模型: Qwen2.5-1.5B
- 初始化 Git 版本控制

### Fixed
- 修正前总调度的模型幻觉（Qwen → VibeThinker）
- 修正 Data Broker 架构设计（独立模型 → Core 量化版）
