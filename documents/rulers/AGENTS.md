---
id: entry.agents
layer: entry
applies_to:
  - all
load_order:
  - documents/rulers/core/HARD_CONSTRAINTS.md
  - documents/rulers/core/WORKFLOW.md
  - documents/rulers/core/DOC_GOVERNANCE.md
  - documents/rulers/core/RULER_MAINTENANCE.md
  - documents/rulers/core/GIT_COMMIT_CONVENTION.md
---

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

推荐加载链：

```text
{{RULERS_DIR}}/AGENTS.md -> {{RULERS_DIR}}/core/* -> PROJECT_PROFILE.md -> {{RULERS_DIR}}/domain INDEX.md -> matched leaf rules
```

---

## 2. 常驻 core 规则

加载本入口后，以下 core 规则始终必须加载：

- 安全、测试、禁令与完成门禁：[core/HARD_CONSTRAINTS.md]({{RULERS_DIR}}/core/HARD_CONSTRAINTS.md)
- 实施工作流与推理顺序：[core/WORKFLOW.md]({{RULERS_DIR}}/core/WORKFLOW.md)
- 规则文档治理：[core/DOC_GOVERNANCE.md]({{RULERS_DIR}}/core/DOC_GOVERNANCE.md)
- Ruler 维护决策树：[core/RULER_MAINTENANCE.md]({{RULERS_DIR}}/core/RULER_MAINTENANCE.md)
- Git 提交规范：[core/GIT_COMMIT_CONVENTION.md]({{RULERS_DIR}}/core/GIT_COMMIT_CONVENTION.md)

最短推理顺序：

```text
Analyze dependencies -> Check constraints -> Verify patterns -> Write code
```

---

## 3. 激活门禁

| Level | 状态 | 允许的工作 | 必需证据 |
| --- | --- | --- | --- |
| Level 0 | 已放入模板，尚无 `PROJECT_PROFILE.md` | 仅允许 bootstrap discovery；检查已观察到的文件、文档、配置与项目结构 | 来自仓库或人工确认的 discovery 记录与事实 |
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
| 后端服务、API、服务端校验、授权、事务 | [backend/INDEX.md]({{RULERS_DIR}}/backend/INDEX.md) | 涉及持久化、schema、migrations 或 SQL 时，追加数据库路由。 |
| 数据库 schema、migrations、索引、约束、seeds、backfills | [database/INDEX.md]({{RULERS_DIR}}/database/INDEX.md) | 实体、仓储、事务、API 或服务行为变化时，追加后端路由。 |
| 前端共享架构、状态、构建、包管理、跨平台 UI | [frontend/INDEX.md]({{RULERS_DIR}}/frontend/INDEX.md) | 根据平台继续路由到 common、web 或 app 入口。 |
| 设计 token、共享样式、品牌、无障碍基线 | [frontend/common/INDEX.md]({{RULERS_DIR}}/frontend/common/INDEX.md) | 视觉实现变化时，追加平台专属设计规则。 |
| Web 或管理端前端页面、路由、组件、守卫、API 集成 | [frontend/web/INDEX.md]({{RULERS_DIR}}/frontend/web/INDEX.md) | 仅在任务命中时加载 web develop 与 design 叶子规则。 |
| 移动 app、H5、类原生流程、移动 UI 组件、移动路由 | [frontend/app/INDEX.md]({{RULERS_DIR}}/frontend/app/INDEX.md) | 仅在任务命中时加载 app develop 与 design 叶子规则。 |
| 规则维护、治理、索引更新、校验脚本 | [core/DOC_GOVERNANCE.md]({{RULERS_DIR}}/core/DOC_GOVERNANCE.md), [core/RULER_MAINTENANCE.md]({{RULERS_DIR}}/core/RULER_MAINTENANCE.md) | 修改规则前执行 ruler impact assessment。 |
| 棕地 discovery、画像创建、规则生成准备 | [bootstrap/PROJECT_DISCOVERY.md]({{RULERS_DIR}}/bootstrap/PROJECT_DISCOVERY.md) | 在 `PROJECT_PROFILE.md` 与领域规则经过审阅前，使用 bootstrap 规则。 |

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

---

## 7. 初始化执行流程

当 AI 被要求"按照 AGENTS.md 初始化项目规范"或类似指令时，按以下顺序执行。

| 步骤 | 操作 | 门禁 |
|------|------|------|
| 1. 确认目录名 + 占位符替换 | (a) 询问用户是否重命名 `rulers` 目录；(b) 三阶段替换：显式 `{{RULERS_DIR}}` → 隐式路径占位符（如 `frontend-browser/**` → 实际路径）→ 模板语言（"目标项目" → "本项目"）。详见 §7.3 | 人工确认 |
| 2. 迁移入口 | 将本文件 (AGENTS.md) 复制到项目根目录（保留模板内副本供校验使用） | 自动 |
| 3. 项目发现 | 九维扫描：仓库形态、技术栈、命令、安全模型、持久化、API 契约、前端平台、CI/CD、高风险区域 | 人工确认发现结果 |
| 4. 生成项目画像 | 基于 `PROJECT_PROFILE.template.md` 填入已确认事实（使用 `` ```yaml `` fenced metadata 块，非 `---` frontmatter），标注证据来源（📄 文件路径:行号），未确认事实归入 §13 | 人工审阅 |
| 5. 生成领域规则 | 仅为实际存在的领域生成规则，**必须遵循 BROWNFIELD_RULE_GENERATION.md 中的"AI_FILL 节处理规则"**——删除元指令文本、用项目事实替换、执行 Agent 自检清单。删除不适用领域模板，同步更新 INDEX.md 和本文件的路由表 | 逐领域人工审阅 |
| 6. 校验 | 运行 `python3 scripts/validate_rulers.py`，按错误提示修复（最多 3 轮），无法自动修复的列出并请求人工处理 | 自动 |
| 7. 激活 | 更新 `RULES_COMPLETENESS_CHECKLIST.md`，按等级逐级激活各领域 | 人工确认 |

### 7.1 项目发现九维清单

1. **仓库形态与模块边界** — 顶层目录、工作区配置（package.json workspaces、go.work 等）、monorepo 判定、.gitignore 排除目录
2. **技术栈与版本** — 依赖清单文件（package.json/go.mod/Cargo.toml/pyproject.toml 等）、语言版本、包管理器（npm/yarn/pnpm 等）
3. **命令与工作目录** — package.json scripts、Makefile/Taskfile、CI 配置中的命令、Dockerfile 中的命令
4. **安全模型** — auth 相关文件/目录、中间件/guard/interceptor 模式、.env.example 密钥变量、密钥管理方案（Vault/KMS/环境变量）、密码哈希依赖（bcrypt/argon2）
5. **持久化与 Migration** — ORM 配置（Prisma/TypeORM/SQLAlchemy 等）、migration 目录、seed 文件、数据库连接配置
6. **API 契约与外部集成** — OpenAPI/Swagger/GraphQL/gRPC 文件、API 路由定义、外部 HTTP 调用（axios/fetch/requests）、消息队列（Redis/RabbitMQ/Kafka）、第三方 SDK 依赖、webhook 代码
7. **前端平台与设计系统** — 前端框架（React/Vue/Next.js 等）、组件库（MUI/Antd/shadcn 等）、CSS 方案（Tailwind/CSS Modules/Sass）、设计 token 来源、无障碍依赖
8. **CI/CD 与部署** — CI 提供方（GitHub Actions/GitLab CI/Jenkins）、Dockerfile/docker-compose、Kubernetes/Helm/Terraform 配置、部署脚本
9. **高风险区域** — 交叉分析安全敏感路径、数据敏感路径、部署敏感路径、外部计费/消息/通知路径

### 7.2 约束

- 不得编造项目事实。只能使用已观察到的文件、配置和文档作为证据。
- 不确定的事项标记为"❓ 待确认"并附原因和"建议谁来确认"。
- 在 PROJECT_PROFILE.md 经人工审阅通过前，不得开始领域规则生成。
- 高风险领域（安全、数据库）必须经人工审阅人明确接受后，才能激活为 Level 2。
- 证据冲突时，保留冲突可见，并在生成硬约束前请求人工确认。
- 如果某个项目发现范围没有证据，将其标记为不完整，而不是省略。

### 7.3 占位符替换（三阶段）

#### 阶段 A — 显式占位符

将所有 `{{RULERS_DIR}}` 替换为实际路径 `documents/<目录名>`。

```bash
find documents/<RULERS_DIR_NAME> -type f \( -name "*.md" -o -name "*.py" \) \
  -exec sed -i '' 's|{{RULERS_DIR}}|documents/<RULERS_DIR_NAME>|g' {} +
```

#### 阶段 B — 隐式路径占位符

模板中存在非 `{{}}` 形式的路径占位符。将以下模板路径替换为 Step 3（项目发现）确定的实际目录名。如项目无对应平台，删除该行。

| 模板路径 | 替换为 |
|----------|--------|
| `frontend-browser/**` | 前端 Web 目录（如 `frontend/web/**`） |
| `browser/**` | 同上 |
| `browser-client/**` | 同上（不存在则删除该行） |
| `frontend-mobile/**` | 前端 App/H5 目录（如 `frontend/h5/**`） |
| `touch-client/**` | 同上（不存在则删除该行） |
| `mobile-client/**` | 同上 |
| `mobile/**` | 同上 |
| `server/**` | 后端目录（如 `backend/**`，不存在则删除） |
| `services/**` | 同上 |
| `migrations/**` | 数据库目录（如无独立 migration 目录则删除） |
| `schema/**` | 同上 |

使用 `sed` 批量替换。验证：
```bash
grep -rn "frontend-browser\|browser-client\|frontend-mobile\|touch-client\|mobile-client" \
  documents/<RULERS_DIR_NAME>/ --include="*.md" \
  && echo "FAIL: template paths remain" || echo "OK"
```

#### 阶段 C — 模板语言

```bash
find documents/<RULERS_DIR_NAME> -name "*.md" -exec sed -i '' 's/目标项目/本项目/g' {} +
find documents/<RULERS_DIR_NAME> -name "*.md" -exec sed -i '' 's/target project/this project/g' {} +
```

验证：
```bash
grep -rn "目标项目" documents/<RULERS_DIR_NAME>/ --include="*.md" \
  | grep -v "bootstrap/\|core/DOC_GOVERNANCE" \
  && echo "FAIL: template language" || echo "OK"
```
