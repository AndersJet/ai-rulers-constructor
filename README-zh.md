<div align="center">

<img src="logo.png" alt="Rulers Template" width="120">

# Rulers Template

**通用 AI 开发规范模板 — 为 AI 编程助手提供渐进式开发护栏**

> 规范非终稿，乃与业务共生的活物。在实践中校准，于反馈中进化——没有一劳永逸的标准，只有持续逼近真相的迭代。

<div align="center">

<strong>简体中文</strong> |
<a href="./README.md">English</a>

</div>

[![Version](https://img.shields.io/badge/version-v1.0.0-blue)](https://github.com/AndersJet/ai-rulers-template/releases)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/AndersJet/ai-rulers-template/pulls)

[![Claude Code](https://img.shields.io/badge/AI-Claude%20Code-d97757)](https://claude.ai)
[![Cursor](https://img.shields.io/badge/AI-Cursor-6c4df5)](https://cursor.sh)
[![GitHub Copilot](https://img.shields.io/badge/AI-GitHub%20Copilot-0288d1)](https://github.com/features/copilot)

</div>

---

## 📑 目录

- [解决什么问题](#解决什么问题)
- [怎么解决](#怎么解决)
- [快速开始](#快速开始)
- [激活等级](#激活等级)
- [日常使用](#日常使用)
- [校验](#校验)
- [完整初始化流程](#完整初始化流程)
- [模板目录说明](#模板目录说明)
- [关键约定](#关键约定)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [常见问题](#常见问题)
- [Star History](#star-history)

---

## 🎯 解决什么问题

AI 编码助手很强大，但也很难预测。没有明确的边界约束，它们可能会：

- 触犯项目的安全、数据或部署策略
- 在不同会话中输出风格不一致的代码
- 使用与项目技术栈不匹配的通用模式
- 未经审阅就执行高风险操作（数据库迁移、认证变更等）

**每个项目都需要开发护栏。从零手写这些规则既繁琐又容易出错。**

## 💡 怎么解决

Rulers Template 为 AI 助手提供一套**项目专属的规则手册**——规则基于你项目的实际代码库自动生成，不是从博客文章复制来的。

- **证据驱动** — 规则基于项目真实的文件、配置和命令生成，绝不编造
- **渐进加载** — AI 只加载当前任务相关的规则，而非整棵规则树
- **激活门禁** — 四级安全等级（Level 0-3），规则经人工审阅前 AI 不能执行危险操作
- **领域路由** — 后端、数据库、前端——每个领域有独立的约束集
- **一键初始化** — `ai-rulers-init` skill 自动扫描项目并生成所有规则

### 工作流程

```text
1. 模板放入你的项目
2. AI 扫描代码库（九个维度：技术栈、安全、数据库、CI/CD 等）
3. AI 生成 PROJECT_PROFILE.md，记录已确认的项目事实
4. 为项目实际使用的每个领域生成专属规则
5. 规则逐级经人工审阅后激活
6. 之后每次 AI 会话自动遵循这些规则
```

---

## 🚀 快速开始

两种使用方式，选择适合你的。

### 方式一：拷贝模板 + AI 自动初始化

将模板复制到项目中，然后向 AI 发送明确的初始化指令。

```bash
# 1. 克隆本仓库
git clone https://github.com/AndersJet/ai-rulers-template.git

# 2. 将 rulers/ 目录复制到目标项目
cp -r ai-rulers-template/documents/rulers /path/to/your-project/documents/
```

**3. 在 AI 编码助手（Claude Code、Cursor、Copilot 等）中打开项目，发送以下指令：**

> 请加载 `documents/rulers/AGENTS.md` 文档到上下文，然后按照其中的初始化流程完成对当前项目的规范初始化。

AI 会读取 AGENTS.md 并自动执行：确认目录名 → 替换占位符 → 迁移 AGENTS.md → 九维项目发现 → 生成 PROJECT_PROFILE.md → 生成领域规则 → 校验 → 激活。

### 方式二：安装 Skill + 一句话初始化（推荐）

>[!TIP]
> **推荐大多数用户使用此方式** — 一次安装，所有项目通用。

[ai-rulers-init](skills/ai-rulers-init/) skill 可自动完成整个初始化流程。

**下载与安装：**

```bash
# 1. 克隆本仓库
git clone https://github.com/AndersJet/ai-rulers-template.git

# 2. 安装 skill
#    Claude Code
cp -r ai-rulers-template/skills/ai-rulers-init/ ~/.claude/skills/ai-rulers-init/

#    其他平台（Cursor、Copilot 等）
#    导入 ai-rulers-template/skills/ai-rulers-init.skill
```

**3. 打开目标项目，对 AI 发送：**

> 使用 ai-rulers-init skill，帮我初始化 AI rulers。

Skill 自动执行全部步骤。支持增量重跑——后续添加新平台（如移动端）时，重跑 skill 自动识别新领域，不修改已有活跃规则。详见 [SKILL.md](skills/ai-rulers-init/SKILL.md)。

| | 方式一（拷贝） | 方式二（Skill） |
|---|---|---|
| **准备** | 手动拷贝目录 | 一次性安装 skill |
| **初始化** | 对 AI 说："加载 AGENTS.md，按初始化流程执行" | 对 AI 说："使用 skill 初始化 rulers" |
| **增量更新** | 手动重新拷贝 + 重新初始化 | 重跑 skill，自动识别新领域 |
| **适合** | 一次使用、试试看 | 多个项目、团队推广 |

---

## 🔒 激活等级

控制 AI 在各阶段的允许操作范围：

| Level | 状态 | 允许的操作 |
|-------|------|-----------|
| **Level 0** | 模板已放入，无项目画像 | 仅项目发现 |
| **Level 1** | 项目画像已审阅 | 只读分析、低风险文档、小型本地修复 |
| **Level 2** | 领域规则已审阅 | 在已激活领域内工作 |
| **Level 3** | 发布门禁已审阅 | 有生产影响的工作 |

**高风险工作最低要求：**

| 工作类型 | 最低等级 |
|----------|----------|
| 认证/安全敏感变更 | Level 2 |
| 数据库 schema/migration/seed/backfill | Level 2 |
| 外部支付/消息/通知等集成 | Level 2 或 Level 3 |
| 发布/部署/CI/CD 变更 | Level 3 |

---

## 📋 日常使用

初始化完成后，AI 在每次会话中按以下顺序加载规范：

```text
AGENTS.md → core/* → PROJECT_PROFILE.md → 领域 INDEX.md → 命中的叶子规则
```

只需在 AI 指令中引用对应的领域即可：

- 后端接口开发 → AI 自动加载 `backend/INDEX.md` 及其叶子规则
- 数据库变更 → AI 自动加载 `database/INDEX.md` 及其叶子规则
- 前端页面开发 → AI 自动加载 `frontend/INDEX.md` 及对应平台的 develop/design 规则

---

## ✅ 校验

```bash
python3 documents/rulers/scripts/validate_rulers.py
```

>[!NOTE]
> ai-rulers-init skill 在初始化过程中会自动运行校验。手动编辑规则后，可直接运行此命令进行校验。

校验内容：
- Markdown 链接有效性（不指向模板外部）
- 每个权威文档包含 `metadata`（applies_to、trigger_keywords、must_load_with）
- `must_load_with` 路径可解析且在模板范围内
- 每个 `INDEX.md` 覆盖同级所有叶子文档
- `AGENTS.md` 引用全部 5 个 core 规则
- `ACTIVATION_LEVELS.md` 包含 Level 0-3 定义
- 高风险文档包含 Level 2 或 Level 3 激活语言

---

## 🔄 完整初始化流程

AI 执行初始化时（无论哪种方式），完整流程为：

```text
确认目录名 → 替换占位符 → 复制 AGENTS.md 到根目录 → 项目发现 → 生成 PROJECT_PROFILE.md → 生成领域规则 → 校验 → 按等级激活
```

| 步骤 | 做什么 | 谁来做 | 产出 |
|------|--------|--------|------|
| 1. 确认目录名 | 询问是否重命名 `rulers` 目录，若重命名则替换所有 `{{RULERS_DIR}}` 占位符 | AI + 人工确认 | 正确的目录名和路径引用 |
| 2. 迁移入口 | 将 AGENTS.md 从模板目录复制到项目根目录（模板内保留副本供校验） | AI/自动 | 根目录 `AGENTS.md` |
| 3. 项目发现 | 九维扫描：仓库形态、技术栈、命令、安全模型、持久化、API 契约、前端平台、CI/CD、高风险区域 | AI + 人工确认 | 发现记录 |
| 4. 生成画像 | 基于 `PROJECT_PROFILE.template.md` 填入已确认事实，标注证据来源 | AI + 人工审阅 | `PROJECT_PROFILE.md` |
| 5. 生成规则 | 仅为项目实际存在的领域生成 `INDEX.md` + 叶子规则，删除不适用领域模板 | AI + 人工审阅 | 各领域 `INDEX.md` + 叶子规则 |
| 6. 校验 | 运行 `validate_rulers.py` 检查结构完整性，按错误修复（最多 3 轮） | AI/自动 | 校验通过 |
| 7. 激活 | 按激活等级逐级解锁各领域 | 人工审阅确认 | 可工作的 AI 规范体系 |

---

## 📁 模板目录说明

模板（`documents/rulers/`）包含：

### 入口文件

| 文件 | 说明 |
|------|------|
| `AGENTS.md` | AI 协作协议入口 — AI 读取此文件启动初始化 |
| `INDEX.md` | 模板导航 |
| `PROJECT_PROFILE.template.md` | 项目画像模板 |

### core/ — 全局常驻规则

| 文件 | 说明 |
|------|------|
| `HARD_CONSTRAINTS.md` | 全局硬约束 |
| `WORKFLOW.md` | 实施工作流与推理顺序 |
| `DOC_GOVERNANCE.md` | 规范文档治理规则 |
| `RULER_MAINTENANCE.md` | 规则维护决策树 |
| `GIT_COMMIT_CONVENTION.md` | Git 提交规范 |

### backend/ — 后端规范

架构、API 安全、数据访问、配置、可观测性、测试。

### database/ — 数据库规范

Schema 设计、Migration、评审清单、Seed 与 Backfill。

### frontend/ — 前端规范

- `common/`：共享设计 token、样式、无障碍基线
- `web/develop/`：Web 端架构、API 集成、授权、状态管理、测试
- `web/design/`：Web 端视觉系统、组件模式、无障碍
- `app/develop/`：移动端架构、UI 模式、测试
- `app/design/`：移动端 token、布局、组件、交互、无障碍、示例

### bootstrap/ — 引导指南

| 文件 | 说明 |
|------|------|
| `PROJECT_DISCOVERY.md` | 项目发现流程 |
| `BROWNFIELD_RULE_GENERATION.md` | 棕地项目规则生成指南 |
| `ACTIVATION_LEVELS.md` | 四级激活门禁定义 |
| `RULES_COMPLETENESS_CHECKLIST.md` | 完整性检查清单 |

### scripts/

`validate_rulers.py` — 结构校验脚本。

---

## 🔑 关键约定

### 必须保护的内容

- `metadata:` / `applies_to` / `trigger_keywords` / `must_load_with` — 机器可解析元数据键
- `AI_FILL` — 标记需要 AI 填充的章节
- `PROJECT_PROFILE.md` / `PROJECT_PROFILE.template.md` / `AGENTS.md` / `INDEX.md` — 协议文件名
- `Level 0` / `Level 1` / `Level 2` / `Level 3` — 激活等级标识

### trigger_keywords 策略

每个规则文件的 `trigger_keywords` 采用中英双语，确保跨模型命中率：

```yaml
trigger_keywords:
  - git
  - commit
  - conventional commits
  - 提交
  - 提交规范
```

### 冲突裁决

```
core 全局硬约束 > 安全规则 > 激活门禁 > 领域规则 > 专题规则 > 示例
```

### 提交规范

- `type`：英文（feat/fix/docs/refactor/test/chore/build/ci）
- `subject`：中文，动宾结构，不以句号结尾
- `body`：中文，说明"改了什么"和"为什么"
- 格式：`<type>[optional scope]: <subject>`

---

## 🏗️ 项目结构

```text
ai-rulers-template/
├── README.md                        # 本文件（英文版）
├── README-zh.md                     # 中文版
├── AGENTS.md                        # 模板维护 AI 协作入口
├── logo.png
├── LICENSE
├── skills/                          # 打包的 skills（交付物）
│   ├── ai-rulers-init.skill         # 可移植 skill 包
│   └── ai-rulers-init/              # 解包 skill
│       ├── SKILL.md
│       └── templates/               # 内嵌 rulers 模板
├── documents/
│   └── rulers/                      # Rulers 模板（核心产品）
│       ├── AGENTS.md
│       ├── INDEX.md
│       ├── PROJECT_PROFILE.template.md
│       ├── core/                    # 全局常驻规则
│       ├── backend/                 # 后端领域规范
│       ├── database/                # 数据库领域规范
│       ├── frontend/                # 前端领域规范
│       │   ├── common/
│       │   ├── web/
│       │   └── app/
│       ├── bootstrap/               # 引导与生成指南
│       └── scripts/                 # 校验脚本
└── docs/
    └── superpowers/
        ├── specs/                   # 设计规格
        └── plans/                   # 实现计划
```

---

## 🛠️ 开发指南

### 修改模板规则

1. 修改前加载 `documents/rulers/core/DOC_GOVERNANCE.md` 了解治理规则
2. 修改前执行 ruler impact assessment（见 `documents/rulers/core/RULER_MAINTENANCE.md`）
3. 修改后运行校验：`python3 documents/rulers/scripts/validate_rulers.py`
4. 遵循提交规范（见 `documents/rulers/core/GIT_COMMIT_CONVENTION.md`）

### 修改 ai-rulers-init Skill

1. 编辑 `skills/ai-rulers-init/SKILL.md` 修改工作流
2. 编辑 `skills/ai-rulers-init/templates/` 更新模板内容
3. 重新打包：`python -m scripts.package_skill skills/ai-rulers-init`（需要 skill-creator）
4. 用新包替换 `skills/ai-rulers-init.skill`

### 提交规范

- `type`：英文（feat/fix/docs/refactor/test/chore/build/ci）
- `subject`：中文，动宾结构，不以句号结尾
- `body`：中文，说明"改了什么"和"为什么"
- 格式：`<type>[optional scope]: <subject>`

---

## ❓ 常见问题

<details>
<summary><strong>是否必须使用全部领域？</strong></summary>

不需要。如果目标项目没有移动端，删除 `frontend/app/` 并更新 `AGENTS.md` 和 `INDEX.md` 中的路由。ai-rulers-init skill 会自动完成此清理。

</details>

<details>
<summary><strong>可以直接在 Level 0 下写代码吗？</strong></summary>

不可以。Level 0 只允许项目发现。必须先完成 PROJECT_PROFILE.md 并审阅。

</details>

<details>
<summary><strong>校验脚本报错怎么办？</strong></summary>

按错误提示逐项修复。常见问题：链接指向不存在的文件、metadata 缺失、INDEX 遗漏叶子文档等。ai-rulers-init skill 会自动修复大部分校验错误。手动方式下，对照错误信息逐项修正即可。

</details>

<details>
<summary><strong>如何更新已激活的规则？</strong></summary>

修改规则前执行 ruler impact assessment（见 `core/RULER_MAINTENANCE.md`）。ai-rulers-init skill 支持增量重跑——自动检测变更，仅重新生成需要的部分。

</details>

<details>
<summary><strong>后续添加新平台（如移动端）怎么办？</strong></summary>

**Skill 方式：** 重新运行 ai-rulers-init skill。**手动方式：** 从本仓库复制缺失领域模板到项目中，然后对 AI 说："加载 AGENTS.md，项目新增了领域，请执行项目发现。"

</details>

<details>
<summary><strong>如何安装 skill？</strong></summary>

**Claude Code：** 将 `skills/ai-rulers-init/` 复制到 `~/.claude/skills/ai-rulers-init/`
**其他平台：** 导入 `skills/ai-rulers-init.skill`

</details>

<details>
<summary><strong>AI 没有自动开始初始化怎么办？</strong></summary>

发送明确指令："请加载 `documents/rulers/AGENTS.md` 文档到上下文，然后按照其中的初始化流程完成对当前项目的规范初始化。"

</details>

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=AndersJet/ai-rulers-template&type=Date)](https://star-history.com/#AndersJet/ai-rulers-template&Date)

---

<div align="center">

### 如果这个项目对你有帮助，欢迎给我们一个 Star！

Made with ❤️ by [AndersJet](https://github.com/AndersJet)

</div>
