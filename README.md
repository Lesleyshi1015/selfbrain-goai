# SelfBrain - AI 隐私保护层

> "Your AI, Your Control" — 让企业完全掌控自己的 AI 使用

## 项目概述

SelfBrain 是一个本地运行的 AI 隐私保护层，通过**架构分片 + 动态加密**实现银行级数据安全，同时集成 Memory Palace 实现智能 Token 优化。

## 核心架构

```
VibeThinker-3B FP16（Core 总调度）
├── VibeThinker-3B INT4（Data Broker，Core 的量化版）
├── Qwen2.5-1.5B + MEMO 训练（Navigator，记忆补丁）
└── Qwen2.5-1.5B + MEMO 训练（Cipher，密码补丁）
```

**总参数量**: ~5B（VibeThinker-3B 共享）

## 核心创新

1. **三 MEMO 协同架构** — Navigator + Cipher + Data Broker 协同工作
2. **动态密码系统** — 类银行 U盾，5 分钟自动过期
3. **Memory Palace 深度集成** — Token 节约 70-80%
4. **四层可视化 Dashboard** — 实时安全监控

## 项目结构

```
SelfBrain/
├── .specs/          # 项目规格（dev-workflow）
├── docs/            # 技术文档（15 章）
├── src/             # 源代码
├── tests/           # 测试
├── scripts/         # 脚本
├── archive/         # 归档
├── CHANGELOG.md     # 变更日志
├── LESSONS.md       # 经验教训
└── README.md        # 本文件
```

## 技术文档

详见 `docs/` 目录：

| 章节 | 内容 |
|------|------|
| 第1章 | 项目概述 |
| 第2章 | 核心架构 |
| 第3章 | MEMO-Navigator |
| 第4章 | MEMO-Cipher |
| 第5章 | Data Broker |
| 第6章 | SelfBrain-Core |
| 第7章 | 动态密码系统 |
| 第8章 | 分层权限系统 |
| 第9章 | 可视化 Dashboard |
| 第10章 | 插件架构实现 |
| 第11章 | API 规格说明 |
| 第12章 | 性能优化 |
| 第13章 | 部署方案 |
| 第14章 | 产品形态 |
| 第15章 | 实施路线图 |

## 相关项目

- **Memory Palace** — 三层映射记忆架构（底层基础设施）
- **VibeThinker-3B** — 本地推理模型
- **MEMO** — 记忆即模型（训练方法论）

## 许可证

待定

---

## GOAI 初赛提交说明

> GOAI 新智基座 | AgentInfra 赛道初赛可执行代码包。

### 运行入口

```bash
pip install -e .            # 安装（框架内置）
python src/demo.py          # 运行 Demo（stub 引擎，无需闭源核心）
pytest                      # 运行全部测试
```

### 依赖

- Python >= 3.10
- 内置 agent_teams_sdk 框架（本仓库包含）
- 闭源引擎可选：`SB_SELFBRAIN_SRC` 环境变量注入主项目源码路径

### 样例输入输出

Demo 展示隐私保护多 Agent 协同闭环：用户请求 → Privacy Guardian 发布任务到黑板 → Workers（Memory Navigator / Cipher Generator 等）分工执行 → Validator 核查 → 整合返回。

### 运行证据

```
pytest
# 195 passed, 88% coverage
```

### 黑盒说明

本仓库**不包含**核心引擎源码与模型权重（MEMO 微调模型 / 主项目 src）。评审运行 Demo 和测试无需闭源引擎：stub 模式零模型加载零推理；`--real` 模式通过 `SB_SELFBRAIN_SRC` 注入真实引擎，加载失败优雅降级回 stub。

### 品牌

- 对外品牌：**SelfBrain**
- 技术包名：selfbrain-goai
