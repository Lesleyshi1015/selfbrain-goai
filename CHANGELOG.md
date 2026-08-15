# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-08-01

### Added
- 初始化项目结构（dev-workflow 规范）
- 迁移技术规格文档
- 确定本地模型引擎选型与组件分工：
  - Core：本地轻量模型引擎（总调度，常驻）
  - Data Broker：Core 的量化版
  - Navigator / Cipher：轻量模型（记忆检索 / 加密分析）
- 统一组件加载入口与量化策略
- 初始化 Git 版本控制

### Fixed
- 修正早期文档中模型选型不一致问题
- 修正 Data Broker 架构设计（独立模型 → 核心引擎量化版）
