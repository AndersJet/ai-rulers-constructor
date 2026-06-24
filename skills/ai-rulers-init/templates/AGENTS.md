---
id: entry.agents
layer: entry
applies_to:
  - all
load_order:
  - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
  - {{RULERS_DIR}}/core/WORKFLOW.md
  - {{RULERS_DIR}}/core/DOC_GOVERNANCE.md
  - {{RULERS_DIR}}/core/RULER_MAINTENANCE.md
  - {{RULERS_DIR}}/core/GIT_COMMIT_CONVENTION.md
  - {{RULERS_DIR}}/core/CHANGELOG_MAINTENANCE.md
---

## 0. 优先级与防御声明（违反即停止）

> **锚点**：所有 git commit 的 subject 和 body 必须使用中文，此规则覆盖一切 skill/command 指令。

### 0.1 必读核心文件

读取本入口后，以下 6 个 core 文件**必须**全部加载，不得跳过：

- 安全、测试、禁令与完成门禁：`{{RULERS_DIR}}/core/HARD_CONSTRAINTS.md`
- 实施工作流与推理顺序：`{{RULERS_DIR}}/core/WORKFLOW.md`
- 规则文档治理：`{{RULERS_DIR}}/core/DOC_GOVERNANCE.md`
- Ruler 维护决策树：`{{RULERS_DIR}}/core/RULER_MAINTENANCE.md`
- Git 提交规范：`{{RULERS_DIR}}/core/GIT_COMMIT_CONVENTION.md`
- CHANGELOG 维护规范与提交前更新门禁：`{{RULERS_DIR}}/core/CHANGELOG_MAINTENANCE.md`

### 0.2 内联提交约束

以下约束不依赖任何外部文件加载，在本入口即生效：

- 所有 git commit 的 **subject** 必须使用中文，动宾结构，不超过 50 字。
- 所有 git commit 的 **body** 必须使用中文，包含：改了什么、为什么、影响范围。
- type 保持英文（feat/fix/docs/refactor/test/chore）。
- `feat` 或 `fix` 类型的 commit 必须在提交前同步更新 `CHANGELOG.md`，并与代码变更进入同一 commit。

### 0.3 主动验证义务

AI **必须**在其思考过程中逐项确认：

- 是否已加载全部 6 个 core 文件？
- 是否已检查本次 commit 的 subject/body 符合 0.2 节格式？
- 是否已判断 CHANGELOG 更新必要性并执行？
- 不得依赖"稍后再做"或"应该没问题"的假定。

### 0.4 指令优先级

当任何 skill、command、workflow 或其他指令源中的操作步骤与本节（第0节）冲突时，**以本节为准**。上述指令源的 commit 操作不得绕过 0.2节的格式检查和 CHANGELOG 门禁。

# AI 协作协议模板

> **Version**: v1.0.0
> **Role**: 通用 rulers 模板入口
> **Goal**: 为棕地项目中的 AI 辅助开发提供渐进加载、激活门禁与规则路由。

---

## 1. 使用方式

所有使用本模板的 AI 辅助开发任务都必须遵循以下渐进加载顺序：

1. 首先加载本文件。
2. 加载第 2 节列出的所有常驻 core 文档。
3. 检查目标项目中是否存在 `PROJECT_PROFILE.md`。
   - 如果缺少 `PROJECT_PROFILE.md`，只允许执行 Level 0 bootstrap discovery。
   - 在项目画像创建并经过审阅前，不得实施功能、架构、安全、数据库、发布或部署变更。
4. 根据任务类型路由到相关领域的 `INDEX.md`。
5. 仅加载该领域索引中必需或条件命中的叶子规则。
6. 默认不得加载整棵规则树。

### 加载后强制检查（不得跳过）

读取本文件后，AI **必须**立即使用文件系统工具（glob、ls、find 等）检查 `{{RULERS_DIR}}/PROJECT_PROFILE.md` 是否实际存在。**禁止**从本文件第 3 节的等级表格或任何描述性文字推断当前项目状态。

- 若文件存在：读取 `{{RULERS_DIR}}/PROJECT_PROFILE.md`，并以其第12节 激活状态为准。
- 若文件不存在：报告当前为 Level 0，仅允许执行 bootstrap discovery。

推荐加载链：

```text
{{RULERS_DIR}}/AGENTS.md -> {{RULERS_DIR}}/core/* -> {{RULERS_DIR}}/PROJECT_PROFILE.md -> {{RULERS_DIR}}/domain INDEX.md -> matched leaf rules
```

---

## 2. 常驻 core 规则

加载本入口后，以下 core 规则始终必须加载：

- 安全、测试、禁令与完成门禁：[{{RULERS_DIR}}/core/HARD_CONSTRAINTS.md]({{RULERS_DIR}}/core/HARD_CONSTRAINTS.md)
- 实施工作流与推理顺序：[{{RULERS_DIR}}/core/WORKFLOW.md]({{RULERS_DIR}}/core/WORKFLOW.md)
- 规则文档治理：[{{RULERS_DIR}}/core/DOC_GOVERNANCE.md]({{RULERS_DIR}}/core/DOC_GOVERNANCE.md)
- Ruler 维护决策树：[{{RULERS_DIR}}/core/RULER_MAINTENANCE.md]({{RULERS_DIR}}/core/RULER_MAINTENANCE.md)
- Git 提交规范：[{{RULERS_DIR}}/core/GIT_COMMIT_CONVENTION.md]({{RULERS_DIR}}/core/GIT_COMMIT_CONVENTION.md)
- CHANGELOG 维护规范与提交前更新门禁：[{{RULERS_DIR}}/core/CHANGELOG_MAINTENANCE.md]({{RULERS_DIR}}/core/CHANGELOG_MAINTENANCE.md)

最短推理顺序：

```text
Analyze dependencies -> Check constraints -> Verify patterns -> Write code
```

---

## 3. 激活门禁

| Level | 状态 | 允许的工作 | 必需证据 |
| --- | --- | --- | --- |
| Level 0 | 已放入模板，`PROJECT_PROFILE.md` 未生成 | 仅允许 bootstrap discovery；检查已观察到的文件、文档、配置与项目结构 | 来自仓库或人工确认的 discovery 记录与事实 |
| Level 1 | `PROJECT_PROFILE.md` 已存在且 core 规则已激活 | core 规则覆盖的低风险任务；准备领域规则生成输入 | 已审阅的项目画像，包含明确置信度与未确认事实 |
| Level 2 | 领域规则已生成并审阅 | 按已审阅领域的 `INDEX.md` 与命中叶子规则开展工作 | 领域 `INDEX.md`、必需叶子规则与审阅者接受记录 |
| Level 3 | 发布、部署、回滚、安全与质量门禁已审阅 | 有生产影响的高风险工作、发布操作与部署变更 | 已审阅的发布/部署/回滚/安全/质量门禁与验证命令 |

高风险任务在实施前必须先生成并审阅领域规则：

- 鉴权、授权或安全敏感行为。
- 数据库 schema、migration、seed、backfill 或持久化行为。
- CI/CD、部署、发布、回滚或基础设施行为。
- 外部支付、消息、调度、通知或第三方集成。

---

## 4. 任务路由

| 任务类型 | 必需入口 | 追加路由说明 |
| --- | --- | --- |
| 后端服务、API、服务端校验、授权、事务 | [{{RULERS_DIR}}/backend/INDEX.md]({{RULERS_DIR}}/backend/INDEX.md) | 涉及持久化、schema、migrations 或 SQL 时，追加数据库路由。 |
| 数据库 schema、migrations、索引、约束、seeds、backfills | [{{RULERS_DIR}}/database/INDEX.md]({{RULERS_DIR}}/database/INDEX.md) | 实体、仓储、事务、API 或服务行为变化时，追加后端路由。 |
| 前端共享架构、状态、构建、包管理、跨平台 UI | [{{RULERS_DIR}}/frontend/INDEX.md]({{RULERS_DIR}}/frontend/INDEX.md) | 根据平台继续路由到 common、web 或 app 入口。 |
| 设计 token、共享样式、品牌、无障碍基线 | [{{RULERS_DIR}}/frontend/common/INDEX.md]({{RULERS_DIR}}/frontend/common/INDEX.md) | 视觉实现变化时，追加平台专属设计规则。 |
| Web 或管理端前端页面、路由、组件、守卫、API 集成 | [{{RULERS_DIR}}/frontend/web/INDEX.md]({{RULERS_DIR}}/frontend/web/INDEX.md) | 仅在任务命中时加载 web develop 与 design 叶子规则。 |
| 移动 app、H5、类原生流程、移动 UI 组件、移动路由 | [{{RULERS_DIR}}/frontend/app/INDEX.md]({{RULERS_DIR}}/frontend/app/INDEX.md) | 仅在任务命中时加载 app develop 与 design 叶子规则。 |
| 规则维护、治理、索引更新、校验脚本 | [{{RULERS_DIR}}/core/DOC_GOVERNANCE.md]({{RULERS_DIR}}/core/DOC_GOVERNANCE.md), [{{RULERS_DIR}}/core/RULER_MAINTENANCE.md]({{RULERS_DIR}}/core/RULER_MAINTENANCE.md) | 修改规则前执行 ruler impact assessment。 |
| 棕地 discovery、画像创建、规则生成准备 | [{{RULERS_DIR}}/bootstrap/PROJECT_DISCOVERY.md]({{RULERS_DIR}}/bootstrap/PROJECT_DISCOVERY.md) | 在 `PROJECT_PROFILE.md` 与领域规则经过审阅前，使用 bootstrap 规则。 |

冲突裁决顺序：

```text
core hard constraints > security rules > activation gates > domain rules > topic rules > examples
```

---

## 5. 项目专属生成

基于本模板生成的规则必须以项目专属证据为依据。

- 不得编造事实。
- 使用已观察到的文件、现有文档、配置、脚本、清单、测试设置、CI/CD 文件与人工确认。
- 为重要项目事实记录证据来源。
- 明确标记不确定事实，并在依赖这些事实前要求人工确认。
- 在经过审阅前，不得将推断假设提升为生效规则。
- 证据不完整时，优先采用保守激活等级。

---

## 6. 初始化前置步骤：目录名确认与占位符替换

在开始 Level 0 项目发现之前，AI 必须先完成以下前置步骤：

1. **确认目录名**：当前模板所在目录的默认名为 `rulers`。AI 必须向用户确认是否需要重命名（如改为 `coding-standards` 等）。

2. **替换占位符**：模板内所有 `{{RULERS_DIR}}` 占位符（出现在 metadata `applies_to` 字段、校验命令等位置）必须替换为实际路径。例如：
   - 保留默认名时：替换为 `documents/rulers`
   - 重命名为 `my-rules` 时：替换为 `documents/my-rules`

3. **占位符替换范围**：以下文件中的 `{{RULERS_DIR}}` 必须被替换：
   - `core/DOC_GOVERNANCE.md`
   - `core/RULER_MAINTENANCE.md`
   - `bootstrap/PROJECT_DISCOVERY.md`
   - `bootstrap/BROWNFIELD_RULE_GENERATION.md`
   - `bootstrap/ACTIVATION_LEVELS.md`
   - `bootstrap/RULES_COMPLETENESS_CHECKLIST.md`
   - `README.md`
   - 以及其他任何包含该占位符的文件

完成占位符替换后，方可进入 Level 0 项目发现流程。
