<div align="center">

<img src="assets/promo/rulers-constructor-guardrails-poster.png" alt="Rulers Constructor" width="120">

# Rulers Constructor

**通用 AI 开发规范构建器 — 为 AI 编程助手提供渐进式开发护栏**

> 规范非终稿，乃与业务共生的活物。在实践中校准，于反馈中进化——没有一劳永逸的标准，只有持续逼近真相的迭代。

<div align="center">

<strong>简体中文</strong> |
<a href="./README.md">English</a>

</div>

[![Version](https://img.shields.io/badge/version-v1.0.8-blue)](https://github.com/AndersJet/ai-rulers-constructor/releases)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/AndersJet/ai-rulers-constructor/pulls)

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
- [Rulers 目录说明](#rulers-目录说明)
- [关键约定](#关键约定)
- [常见问题](#常见问题)
- [Star 趋势](#star-趋势)

---

## 🎯 解决什么问题

AI 编码助手很强大，但也很难预测。没有明确的边界约束，它们可能会：

- 触犯项目的安全、数据或部署策略
- 在不同会话中输出风格不一致的代码
- 使用与项目技术栈不匹配的通用模式
- 未经审阅就执行高风险操作（数据库迁移、认证变更等）

**每个项目都需要开发护栏。从零手写这些规则既繁琐又容易出错。**

## 💡 怎么解决

Rulers Constructor 为 AI 助手提供一套**项目专属的规则手册**——规则基于你项目的实际代码库自动生成，不是从博客文章复制来的。

- **证据驱动** — 规则基于项目真实的文件、配置和命令生成，绝不编造
- **渐进加载** — AI 只加载当前任务相关的规则，而非整棵规则树
- **激活门禁** — 四级安全等级（Level 0-3），规则经人工审阅前 AI 不能执行危险操作
- **领域路由** — 后端、数据库、前端——每个领域有独立的约束集
- **一键初始化** — `ai-rulers-init` skill 自动扫描项目并生成所有规则

### 工作流程

```text
1. 将 rulers 复制到你的项目中
2. AI 扫描代码库并生成 PROJECT_PROFILE.md
3. AI 根据技术栈创建各领域专属规则
4. 规则经人工审阅后逐级激活
5. 之后每次 AI 会话自动遵循这些规则
```

<details>
<summary><strong>完整初始化流程（点击展开）</strong></summary>

| 步骤 | 做什么 | 产出 |
|------|--------|------|
| 1. 确认目录名 | 询问是否重命名 `rulers` 目录，若重命名则替换 `{{RULERS_DIR}}` 占位符 | 正确的目录名和路径引用 |
| 2. 迁移入口 | 将 `AGENTS.md` 复制到项目根目录 | 根目录 `AGENTS.md` |
| 3. 项目发现 | 九维扫描：仓库形态、技术栈、命令、安全模型、持久化、API 契约、前端平台、CI/CD、高风险区域 | 发现记录 |
| 4. 生成画像 | 基于 `PROJECT_PROFILE.template.md` 填入已确认事实，标注证据来源 | `PROJECT_PROFILE.md` |
| 5. 生成规则 | 仅为项目实际存在的领域生成 `INDEX.md` + 叶子规则，删除不适用模板 | 各领域 `INDEX.md` + 叶子规则 |
| 6. 校验 | 运行 `validate_rulers.py` 检查结构完整性，按错误修复（最多 3 轮） | 校验通过 |
| 7. 激活 | 按激活等级逐级解锁各领域 | 可工作的 AI 规范体系 |

</details>

---

## 🚀 快速开始

### 方式一：拷贝 rulers + AI 自动初始化

```bash
# 1. 克隆本仓库
git clone https://github.com/AndersJet/ai-rulers-constructor.git

# 2. 将 rulers/ 目录复制到目标项目
cp -r ai-rulers-constructor/documents/rulers /path/to/your-project/documents/
```

**3. 在 AI 编码助手中打开项目，发送以下指令：**

> 请加载 `documents/rulers/AGENTS.md` 文档到上下文，然后按照其中的初始化流程完成对当前项目的规范初始化。

### 方式二：安装 Skill + 一句话初始化（推荐）

```bash
# 1. 克隆本仓库
git clone https://github.com/AndersJet/ai-rulers-constructor.git

# 2. 安装 skill
#    Claude Code:
cp -r ai-rulers-constructor/skills/ai-rulers-init/ ~/.claude/skills/ai-rulers-init/

#    其他平台（Cursor、Copilot 等）:
#    导入 ai-rulers-constructor/skills/ai-rulers-init.skill
```

**3. 打开目标项目，对 AI 发送：**

> 使用 ai-rulers-init skill，帮我初始化 AI rulers。

| | 方式一（拷贝） | 方式二（Skill） |
|---|---|---|
| **准备** | 手动拷贝目录 | 一次性安装 skill |
| **初始化** | 对 AI 说："加载 AGENTS.md，按初始化流程执行" | 对 AI 说："使用 skill 初始化 rulers" |
| **增量更新** | 手动重新拷贝 + 重新初始化 | 重跑 skill，自动识别新领域 |
| **适合** | 一次使用、试试看 | 多个项目、团队推广 |

<details>
<summary><strong>配合 <code>ruler</code> CLI 部署（可选）</strong></summary>

完成初始化后，你可以选装 [`ruler`](https://github.com/intellectronica/ruler) CLI 以获得更紧密的 AI 助手集成体验。

**前置条件：** Node.js + `npm install -g @intellectronica/ruler`

```bash
# 在目标工程根目录执行：
ruler init                           # 创建 .ruler/ 目录
cp AGENTS.md .ruler/AGENTS.md       # 复制生成的 AGENTS.md

# 根据开发环境部署：
ruler apply --agents claude         # Claude Code
ruler apply --agents codex          # GitHub Copilot / Codex
# 其他支持的 agent：kilocode、opencode、trae
```

> `ruler` 工具是可选的辅助工具。你也可以继续直接通过 `AGENTS.md` 使用 rulers，无需安装 `ruler` CLI。

</details>

---

## 🔒 激活等级

控制 AI 在各阶段的允许操作范围：

| Level | 状态 | 允许的操作 |
|-------|------|-----------|
| **Level 0** | rulers 已放入，无项目画像 | 仅项目发现 |
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
AGENTS.md → core/* → {{RULERS_DIR}}/PROJECT_PROFILE.md → 领域 INDEX.md → 命中的叶子规则
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

ai-rulers-init skill 在初始化过程中会自动运行校验。手动编辑规则后，可直接运行此命令进行校验。

校验内容：
- Markdown 链接有效性（不指向 rulers 目录外部）
- 每个权威文档包含 `metadata`（`applies_to`、`trigger_keywords`、`must_load_with`）
- `must_load_with` 路径可解析且在 rulers 范围内
- 每个 `INDEX.md` 覆盖同级所有叶子文档
- `AGENTS.md` 引用全部 5 个 core 规则
- `ACTIVATION_LEVELS.md` 包含 Level 0-3 定义
- 高风险文档包含 Level 2 或 Level 3 激活语言

---

## 📁 Rulers 目录说明

rulers（`documents/rulers/`）包含：

| 路径 | 说明 |
|------|------|
| `AGENTS.md` | AI 协作协议入口 — 从这里开始 |
| `INDEX.md` | rulers 导航 |
| `PROJECT_PROFILE.template.md` | 项目画像模板 |
| `core/` | 全局常驻规则：硬约束、工作流、治理、维护、提交规范 |
| `backend/` | 后端领域规范：架构、API 安全、数据访问、可观测性、测试 |
| `database/` | 数据库规范：Schema 设计、Migration、评审清单、Seed 与 Backfill |
| `frontend/` | 前端规范：Web + 移动端，develop + design 子领域 |
| `bootstrap/` | 引导与生成指南：项目发现、棕地规则、激活等级、完整性检查 |
| `scripts/` | `validate_rulers.py` — 结构校验脚本 |

完整目录说明请见 [`documents/rulers/INDEX.md`](documents/rulers/INDEX.md)。

---

## 🔑 关键约定

### 冲突裁决

```
core 全局硬约束 > 安全规则 > 激活门禁 > 领域规则 > 专题规则 > 示例
```

### 保护关键字

- `metadata:` / `applies_to` / `trigger_keywords` / `must_load_with` — 机器可解析元数据键
- `AI_FILL` — 标记需要 AI 填充的章节
- `Level 0` / `Level 1` / `Level 2` / `Level 3` — 激活等级标识

### 提交规范

- `type`：英文（`feat`/`fix`/`docs`/`refactor`/`test`/`chore`/`build`/`ci`）
- `subject`：中文，动宾结构，不以句号结尾
- `body`：中文，说明"改了什么"和"为什么"
- 格式：`<type>[optional scope]: <subject>`

完整规范请见 [`core/GIT_COMMIT_CONVENTION.md`](documents/rulers/core/GIT_COMMIT_CONVENTION.md)。

---

## ❓ 常见问题

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

---

## 🤝 参与贡献

想修改规则或 skill？请查看 [CONTRIBUTING-zh.md](./CONTRIBUTING-zh.md)。

---

## ⭐ Star 趋势

[![Star History Chart](https://api.star-history.com/svg?repos=AndersJet/ai-rulers-constructor&type=Date)](https://star-history.com/#AndersJet/ai-rulers-constructor&Date)

---

<div align="center">

### 如果这个项目对你有帮助，欢迎给我们一个 Star！

Made with ❤️ by [AndersJet](https://github.com/AndersJet)

</div>
