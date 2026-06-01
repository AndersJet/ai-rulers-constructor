---
name: ai-rulers-init
description: >
  Initialize AI development rulers (coding standards and guardrails) in brownfield projects.
  Use this skill whenever the user wants to set up or initialize rulers, add coding standards
  templates, generate project profiles, activate AI guardrails, establish development constraints,
  or bootstrap AI-assisted development rules in existing projects. Triggers on mentions of:
  rulers init, init rulers, setup rulers, initialize rulers, brownfield rules, AI development
  rules, project-specific guidelines, coding standards setup, PROJECT_PROFILE, 初始化 rulers,
  rulers 初始化, 项目规范初始化, or any request to set up AI coding standards from templates.
---

# AI Rulers Init

初始化棕地项目的 AI 开发规范体系。将 rulers 模板放入项目、扫描项目结构、生成项目画像、逐领域生成专属规则、校验并激活。

## 流程总览

```text
Step 0: 前置准备 → Step 1: 项目发现 → Step 2: 项目画像 → Step 3: 领域规则 → Step 4: 校验 → Step 5: 激活
```

每步产出物写入文件系统。再次运行自动检测已完成步骤并跳过。当检测到 `PROJECT_PROFILE.md` 已存在时进入增量模式，仅为新发现领域生成规则。

## 模式检测

在开始任何操作前，检查目标项目中是否存在 `PROJECT_PROFILE.md`：

- **不存在** → 首次运行，走完整流程
- **已存在** → 增量模式（见文末"增量模式"章节）

以下步骤描述首次运行的完整流程。

## 激活等级速查

| Level | 状态 | 允许 |
|-------|------|------|
| Level 0 | 无 PROJECT_PROFILE.md | 仅项目发现 |
| Level 1 | 画像已审阅 | 只读分析、低风险文档 |
| Level 2 | 领域规则已审阅 | 在已激活领域内工作 |
| Level 3 | 发布门禁已审阅 | 生产影响工作 |

当前任务在 Step 2 完成前为 Level 0，Step 2 审阅后进入 Level 1，Step 3 逐领域审阅后进入 Level 2。

---

## Step 0: 前置准备

在开始项目发现前，完成模板放置和配置。

### 0.1 确认目标目录

当前工作目录即为目标项目根目录。向用户确认：

> 当前项目根目录：`<cwd>`。规范模板将放入 `documents/rulers/`。是否需要重命名 `rulers` 目录？（如 `coding-standards`、`dev-rules` 等）

用户确认目录名后，将其记为 `RULERS_DIR_NAME`，完整路径为 `documents/<RULERS_DIR_NAME>/`。

### 0.2 复制模板文件

将 skill 内嵌的 `templates/` 目录全量复制到 `documents/<RULERS_DIR_NAME>/`：

- 如果 `documents/` 目录不存在，先创建它
- 如果目标目录已存在且有内容，提示用户是否需要覆盖或跳过已有文件
- 使用 `cp -r` 复制后，确认所有文件就位

模板位于 skill 目录下的 `templates/`，使用如下命令查找模板路径：
```bash
SKILL_DIR=$(dirname $(grep -rl "name: ai-rulers-init" ~/.claude/skills/ 2>/dev/null | head -1))
cp -r "$SKILL_DIR/templates" "documents/<RULERS_DIR_NAME>/"
```

### 0.3 占位符替换（三阶段）

#### 阶段 A：显式占位符 `{{RULERS_DIR}}`

将 `{{RULERS_DIR}}` 替换为 `documents/<RULERS_DIR_NAME>`。

```bash
find documents/<RULERS_DIR_NAME> -type f \( -name "*.md" -o -name "*.py" \) \
  -exec sed -i '' 's|{{RULERS_DIR}}|documents/<RULERS_DIR_NAME>|g' {} +
```

验证：
```bash
grep -r "{{RULERS_DIR}}" documents/<RULERS_DIR_NAME>/ \
  && echo "FOUND: unexpanded" || echo "OK"
```

#### 阶段 B：隐式路径占位符替换

模板中存在非 `{{}}` 形式的路径占位符。这些是模板针对通用场景定义的路径模式，必须替换为项目实际路径（基于 Step 1 发现结果）。如果项目无对应平台，则删除该行。

| 模板路径 | 替换规则 |
|----------|---------|
| `frontend-browser/**` | 前端 Web 平台实际路径（如 `frontend/web/**`） |
| `browser/**` | 同上 |
| `browser-client/**` | 同上（如无对应平台则删除该行） |
| `frontend-mobile/**` | 前端 App/H5 平台实际路径（如 `frontend/h5/**`） |
| `touch-client/**` | 同上（如无对应平台则删除该行） |
| `mobile-client/**` | 同上 |
| `mobile/**` | 同上 |
| `design-system/**` | 前端设计系统实际路径 |
| `server/**` | 后端实际路径（如 `backend/**`，如已在列表中则删除该行） |
| `services/**` | 同上 |
| `db/**` | 数据库/持久层实际路径 |
| `migrations/**` | 同上（如项目无独立 migration 目录则删除该行） |
| `schema/**` | 同上 |

**替换原则：**
- 项目有对应平台 → 替换为 Step 1 发现的**实际目录名**
- 项目无对应平台 → `sed -i '' '/pattern/d'` 删除该行
- 保留 `backend/**`、`database/**`、`frontend/**` 等顶层路径不变

**验证：**
```bash
grep -rn "frontend-browser\|browser-client\|frontend-mobile\|touch-client\|mobile-client" \
  documents/<RULERS_DIR_NAME>/ --include="*.md" \
  && echo "FOUND: template paths remain" || echo "OK"
```

#### 阶段 C：模板语言本地化

```bash
find documents/<RULERS_DIR_NAME> -name "*.md" \
  -exec sed -i '' 's/目标项目/本项目/g' {} +
find documents/<RULERS_DIR_NAME> -name "*.md" \
  -exec sed -i '' 's/target project/this project/g' {} +
```

**验证：**
```bash
grep -rn "目标项目" documents/<RULERS_DIR_NAME>/ --include="*.md" \
  | grep -v "bootstrap/\|core/DOC_GOVERNANCE" \
  && echo "FOUND: template language" || echo "OK"
```

### 0.4 复制 AGENTS.md 到项目根目录

检查项目根目录是否已存在 `AGENTS.md`：

**不存在** → 将 `documents/<RULERS_DIR_NAME>/AGENTS.md` **复制**到项目根目录（保留模板内副本，供 validate_rulers.py 校验使用）。

**已存在** → 向用户报告冲突并询问：

> ⚠️ 项目根目录已存在 `AGENTS.md`。如何处理？
> 1. **覆盖** — 用 rulers 模板的 AGENTS.md 替换现有文件
> 2. **合并** — 将 rulers 模板的 AGENTS.md 内容追加到现有文件末尾（标注来源和日期）
> 3. **跳过** — 保留现有 AGENTS.md，不迁移（rulers 入口将不可用）

根据用户选择执行。如果合并，追加格式为：

```markdown
---

## Rulers 模板入口 (ai-rulers-init 追加，<日期>)

以下内容由 ai-rulers-init skill 自动追加，与现有 AGENTS.md 合并。
```

### 0.5 替换根目录 AGENTS.md 中的占位符

无论复制/合并/跳过，如果根目录 AGENTS.md 中包含 `{{RULERS_DIR}}`，同样替换为 `documents/<RULERS_DIR_NAME>`。

### Step 0 完成确认

```
✅ Step 0 完成
   - 模板目录：documents/<RULERS_DIR_NAME>/
   - 占位符已全部替换
   - AGENTS.md：<已迁移到根目录 / 已合并 / 已跳过>
```

---

## Step 1: 项目发现 (Level 0)

对当前项目进行九维扫描。每个维度基于实际文件、配置和文档输出事实，不得编造。

### 扫描原则

- 只使用已观察到的文件、现有配置、文档和代码作为证据
- 每个已确认事实标注证据文件路径和行号
- 不确定的事项标记为 `❓ 待确认`，附原因和建议确认人
- 完全未发现的维度如实地报告为"无证据"

### 九维扫描清单

#### 维度 1: 仓库形态与模块边界

检查项：
- 顶层目录结构（`ls -la`）
- 工作区/包管理配置（`package.json` workspaces、`pnpm-workspace.yaml`、`go.work`、`lerna.json`、`nx.json`、`turbo.json`）
- `.gitignore` 中的排除目录
- 子目录中的独立 `package.json`/`go.mod`/`Cargo.toml`（判断是否为 monorepo）

输出格式：
```
## 维度 1: 仓库形态与模块边界
✅ 已确认：<monorepo/单仓库>，包含 <N> 个模块
   - <模块1路径>：<用途>
   - <模块2路径>：<用途>
📄 证据：<配置文件名:行号>
❓ 待确认：<如有不确定的模块边界>
```

#### 维度 2: 技术栈与版本

检查项：`package.json`、`go.mod`、`Cargo.toml`、`pyproject.toml`、`Gemfile`、`build.gradle`、`pom.xml`、lock 文件类型、ORM/数据库驱动依赖。

输出格式：
```
## 维度 2: 技术栈与版本
| 区域 | 技术 | 版本 | 版本来源 |
|------|------|------|----------|
| 后端运行时 | ... | ... | ... |
❓ 待确认：<无法从配置文件确认的版本>
```

#### 维度 3: 命令与工作目录

检查项：`package.json` scripts 字段、`Makefile`、`Taskfile`、`.github/workflows/*.yml`、`Dockerfile` 中的命令。

输出格式：
```
## 维度 3: 命令与工作目录
| 用途 | 命令 | 工作目录 | 置信度 |
|------|------|----------|--------|
| 安装依赖 | ... | ... | 高/中/低 |
❓ 待确认：<无法从配置中确定的命令>
```

#### 维度 4: 安全模型

检查项：搜索 `auth`/`authenticate`/`login`/`jwt`/`session`/`passport` 相关文件和目录；搜索 `middleware`/`guard`/`interceptor` 模式；`.env.example` 中的密钥变量名；密钥管理方案；密码哈希依赖（`bcrypt`/`argon2`）。

输出格式：
```
## 维度 4: 安全模型
✅ 已确认：
- 认证方式：<JWT / Session / OAuth2 / 无>
- 授权方式：<RBAC / ABAC / 自定义中间件 / 无>
- 密钥存储：<环境变量 / Vault / .env 文件>
📄 证据：<文件路径>
❓ 待确认：<不确定的安全机制>
```

#### 维度 5: 持久化与 Migration

检查项：搜索 `migration`/`migrations`/`prisma/migrations`/`alembic/versions` 目录；ORM 配置；`seed` 相关文件；数据库连接配置。

输出格式：
```
## 维度 5: 持久化与 Migration
✅ 已确认：
- 数据存储：<PostgreSQL / MySQL / MongoDB / SQLite / 无>
- Migration 工具：<Prisma Migrate / Alembic / Flyway / 无>
- ORM：<Prisma / TypeORM / SQLAlchemy / 无>
📄 证据：<文件路径>
❓ 待确认：<不确定的持久化策略>
```

#### 维度 6: API 契约与外部集成

检查项：`openapi`/`swagger`/`graphql`/`proto` 文件；API 路由定义；外部 HTTP 调用；消息队列；第三方 SDK；`webhook` 相关代码。

输出格式：
```
## 维度 6: API 契约与集成
✅ 已确认：
- API 风格：<REST / GraphQL / gRPC / 无>
- 契约来源：<文件路径>
- 外部集成：<列出第三方服务和 SDK>
📄 证据：<文件路径>
❓ 待确认：<不确定的集成>
```

#### 维度 7: 前端平台与设计系统

检查项：前端框架和渲染目标；组件库依赖；CSS 方案；设计 token 来源；无障碍相关依赖。

如果没有前端代码，输出 `✅ 无前端代码` 并跳过后续子维度。

#### 维度 8: CI/CD 与部署

检查项：`.github/workflows/`、`.gitlab-ci.yml`、`Jenkinsfile`；`Dockerfile`、`docker-compose.yml`；`kubernetes/`、`helm/`、`k8s/`、`terraform/`；部署脚本。

输出格式：
```
## 维度 8: CI/CD 与部署
✅ 已确认：
- CI 提供方：<GitHub Actions / GitLab CI / Jenkins / 无>
- 部署目标：<AWS ECS / K8s / Vercel / VPS / 无>
- 必需检查：<lint / test / build / typecheck>
📄 证据：<文件路径>
❓ 待确认：<不确定的 CI/CD 细节>
```

#### 维度 9: 高风险区域

交叉分析前八个维度，识别：
- 安全敏感路径：认证/授权/密钥管理相关代码
- 数据敏感路径：migration/seed/backfill/数据库变更相关代码
- 部署敏感路径：CI/CD 配置/Dockerfile/部署脚本
- 外部计费/消息/通知路径

输出格式：
```
## 维度 9: 高风险区域
| 区域 | 风险类型 | 路径 | 建议审阅人 |
|------|----------|------|-----------|
| ... | ... | ... | ... |
```

### 发现结果汇总

九个维度全部扫描完成后汇总呈现，询问确认：

> 以上九个维度的发现结果，是否有需要更正或补充的地方？

用户确认后方可进入 Step 2。

```
✅ Step 1 完成 — 九维项目发现已确认
   当前等级：Level 0
   下一步：Step 2 生成项目画像
```

---

## Step 2: 生成项目画像 (Level 0 → Level 1)

### 2.1 加载模板

读取 `documents/<RULERS_DIR_NAME>/PROJECT_PROFILE.template.md`。

### 2.2 填充事实

将 Step 1 中确认的事实填入模板对应章节：

| 模板章节 | 数据来源 |
|----------|----------|
| §1 Rulers 模板信息 | 固定值：目录路径、当前日期、模板版本 |
| §2 项目身份 | 维度 1（仓库形态）+ 维度 2（技术栈） |
| §3 源码布局 | 维度 1（模块边界） |
| §4 技术栈 | 维度 2（技术栈与版本） |
| §5 命令 | 维度 3（命令与工作目录） |
| §6 安全模型 | 维度 4（安全模型） |
| §7 数据模型与持久化 | 维度 5（持久化与 Migration） |
| §8 API 契约与集成 | 维度 6（API 契约与集成） |
| §9 前端平台 | 维度 7（前端平台） |
| §10 设计系统 | 维度 7（设计系统部分） |
| §11 CI/CD、部署与发布 | 维度 8（CI/CD 与部署） |
| §12 激活状态 | 基于发现结果初始建议 |
| §13 未确认事实 | 所有维度中 `❓ 待确认` 的汇总 |

### 2.3 事实填充规则

- 在生成的 PROJECT_PROFILE.md 标题后添加 `` ```yaml `` fenced metadata 块（非 `---` frontmatter 格式），包含 `metadata:` 顶级键，以及 `applies_to`、`trigger_keywords`、`must_load_with` 子键
- 每个已确认事实标注证据路径：`📄 <文件路径>:<行号>`
- 每个单元格标注置信度：`高`（配置文件直接声明）、`中`（从代码推断）、`低`（仅凭文件名猜测）
- `[AI_FILL]` 占位符替换为实际值
- 未确认事实放入 §13，包含：事实描述、为什么重要、建议确认人
- 不适用领域在 §3 中标记为"不存在"，§12 中标记为"不适用"

### 2.4 激活状态初始建议 (§12)

| 领域 | 初始激活等级 | 条件 |
|------|-------------|------|
| Core | Level 1 | PROJECT_PROFILE.md 审阅后 |
| Backend | Level 0 | 如存在后端代码 |
| Database | Level 0 | 如存在数据库 |
| Frontend | Level 0 | 如存在前端代码 |
| Release | Level 0 | CI/CD 证据充分时建议审阅 |

### 2.5 门禁：人工审阅

生成后请求用户审阅：

> PROJECT_PROFILE.md 已生成。请逐项审阅：
> - §2-§12 中已确认事实是否准确
> - §13 未确认事实是否需要补充
> - §12 激活状态建议是否合理
>
> 审阅通过后项目进入 Level 1。是否需要修改？

用户确认后方可进入 Step 3。

```
✅ Step 2 完成 — PROJECT_PROFILE.md 已生成并审阅
   当前等级：Level 1
   下一步：Step 3 生成领域规则
```

---

## Step 3: 生成领域规则 (Level 1 → Level 2)

仅为项目中实际存在的领域生成规则。执行前先加载 `documents/<RULERS_DIR_NAME>/bootstrap/BROWNFIELD_RULE_GENERATION.md` 作为生成指导。**特别注意"AI_FILL 节处理规则"章节——该章节定义了领域规则内容质量的强制标准，违反将导致生成不合格的元指令文本残留。**

### 3.1 领域清单确认

| 领域 | 存在条件 |
|------|---------|
| core | 始终存在 |
| backend | PROJECT_PROFILE.md §3 后端不为空 |
| database | PROJECT_PROFILE.md §3 数据库不为空 |
| frontend/common | §3 前端不为空 |
| frontend/web | §3 前端 Web 不为空 |
| frontend/app | §3 前端 App 不为空 |

### 3.2 更新 AGENTS.md 路由表

编辑项目根目录的 `AGENTS.md`：
- 路由表中移除不适用领域的行
- 确保每个适用领域路由指向正确的 `INDEX.md`
- 确保 `must_load_with` 和 `load_order` 字段使用实际路径（非 `{{RULERS_DIR}}`）

### 3.3 逐领域生成规则

对每个适用领域：

1. 读取模板 `INDEX.md`
2. 基于 PROJECT_PROFILE.md 事实重写：适用范围对齐、验证命令替换为实际命令、移除不匹配示例
3. 生成叶子规则：保留通用约束、删除不匹配示例、替换模板占位符
4. 更新 `RULES_COMPLETENESS_CHECKLIST.md`
5. 请求人工审阅：

> `<领域> 领域规则已生成。请审阅：
> - INDEX.md 路由是否正确
> - 叶子规则是否与项目技术栈匹配
> - 验证命令是否正确
>
> 审阅通过后该领域激活为 Level 2。是否需要修改？

### 3.4 模板清理（仅首次运行）

删除不适用领域的模板目录：
- 无 App → 删除 `frontend/app/`
- 无 Web → 删除 `frontend/web/`
- 无前端 → 删除整个 `frontend/`
- 无数据库 → 删除 `database/`
- 无后端 → 删除 `backend/`

清理后同步更新 `documents/<RULERS_DIR_NAME>/INDEX.md`：
- 更新目录地图（移除已删除目录）
- 移除指向已删除领域的入口行（如 backend/INDEX.md、database/INDEX.md 等）

### 3.5 验证路由引用

确认 AGENTS.md 和 INDEX.md 路由表中无指向已删除目录的链接。

```
✅ Step 3 完成 — 领域规则已生成并审阅
   已激活领域：<列出已激活为 Level 2 的领域>
   当前等级：Level 2（仅在已激活领域内）
   下一步：Step 4 校验
```

---

## Step 4: 校验

### 4.1 运行校验

```bash
python3 documents/<RULERS_DIR_NAME>/scripts/validate_rulers.py
```

### 4.2 修复问题

如校验失败，逐项分析修复：
- **链接失效**：修正路径或删除无效引用
- **metadata 缺失**：补充 `applies_to`、`trigger_keywords`、`must_load_with`
- **INDEX 遗漏**：确保覆盖同级所有叶子文档
- **core 引用缺失**：确保 AGENTS.md 引用全部 5 个 core 文件

每轮修复后重跑校验，最多 3 轮。3 轮后仍有失败的列出并请求人工处理。

```
✅ Step 4 完成 — 校验通过
```

---

## Step 5: 激活

### 5.1 更新完整性检查清单

更新 `documents/<RULERS_DIR_NAME>/bootstrap/RULES_COMPLETENESS_CHECKLIST.md`。

### 5.2 输出激活状态摘要

```
╔══════════╦════════╦════════╦══════════╦══════════════════╗
║ 领域     ║ 已生成 ║ 已审阅 ║ 激活等级 ║ 备注             ║
╠══════════╬════════╬════════╬══════════╬══════════════════╣
║ core     ║   ✅   ║   ✅   ║ Level 1  ║                  ║
║ backend  ║   ✅   ║   ✅   ║ Level 2  ║                  ║
║ database ║   ✅   ║  ⏳等待 ║ Level 0  ║ 需 DBA 审阅     ║
║ frontend ║   ❌   ║   —    ║    —     ║ 无前端代码       ║
╚══════════╩════════╩════════╩══════════╩══════════════════╝
```

### 5.3 下一步指引

列出待办：
- 哪些领域需要审阅人确认才能激活
- 当前等级下哪些高风险工作不能执行
- 如何触发下一级激活（Level 3 需审阅发布流程）

```
🎉 ai-rulers-init 初始化完成
   - PROJECT_PROFILE.md：已生成
   - 激活等级：Level 2（部分领域）
   - 加载链：AGENTS.md → core/* → PROJECT_PROFILE.md → 领域 INDEX.md → 叶子规则
   - 校验：validate_rulers.py 通过
```

---

## 增量模式

当检测到 `PROJECT_PROFILE.md` 已存在时自动启用。

### 行为变化

| 步骤 | 增量模式行为 |
|------|-------------|
| Step 0 | **全部跳过** |
| Step 1 | **全量重扫** + 与现有画像 diff，输出 🆕/✏️/❌ |
| Step 2 | **增量更新**画像：保留已有 + 追加新发现 |
| Step 3 | **仅为新领域**生成规则；**不执行**模板清理删除 |
| Step 4 | 全量校验 |
| Step 5 | 仅新领域需激活 |

### 增量 Step 1 diff 示例

```
🆕 新增领域：frontend/web（检测到 apps/web/ 目录，含 React 18.3）
✏️ 变更事实：后端新增依赖 — Redis 6.x（apps/api/package.json:25）
❌ 已移除：未检测到删除
```

### 增量 Step 2 操作

1. 读取现有 PROJECT_PROFILE.md
2. §3 追加新发现路径，§4 追加新技术，§12 追加新领域行
3. 保留已有章节所有内容不变

### 增量 Step 3 操作

1. 仅为 🆕新增领域 生成规则
2. 从 skill `templates/` 中复制缺失领域模板到 `documents/<RULERS_DIR_NAME>/`
3. 替换恢复文件中的 `{{RULERS_DIR}}` 占位符
4. 删除恢复领域中不适用的子平台（如恢复 frontend/ 后删除 app/）
5. 更新该领域 `INDEX.md` 移除指向已删除子平台的链接
6. AGENTS.md 路由表追加新领域入口
7. 已有活跃领域文件不做任何修改
8. 不执行模板清理删除

---

## 边界情况处理

### 空仓库（无任何代码）

如果 Step 1 九个维度全部无发现：
- 告知用户当前仓库为空
- 询问是否仍需放置模板（未来使用）还是终止
- 如果继续：仅生成 core 规则 + 最小 PROJECT_PROFILE.md（标记所有领域为不存在）

### Python 不可用

如果 `python3` 命令不可用：
- 报告校验脚本需要 Python 3
- 跳过自动校验，提示手动运行
- 不阻塞后续步骤

### documents/ 目录不存在

自动创建，无需询问。

### 目标目录名冲突

如果 `documents/<RULERS_DIR_NAME>/` 已存在且非空：
- 列出已有内容
- 询问：覆盖 / 选择其他名称 / 合并

### 用户中途取消

产物写入文件系统，重跑时自动检测并从中断处继续：
- PROJECT_PROFILE.md 存在 → Step 0-2 已完成
- 领域 INDEX.md 存在 → 该领域 Step 3 已完成

### 占位符替换不完整

如 Step 0.3 后仍有 `{{RULERS_DIR}}` 残留，进入 Step 1 前必须修复。

---

## 禁止行为

在执行本 skill 期间，AI 不得：

- 在 Level 0 阶段生成代码或修改项目文件（模板放置和占位符替换除外）
- 编造项目事实来填充 PROJECT_PROFILE.md
- 在未得到人工审阅确认前激活任何领域为 Level 2 或以上
- 在增量模式中删除或修改已有已激活领域的规则
- 在增量模式中执行模板清理删除操作
- 静默覆盖已有 AGENTS.md — 冲突时必须人工裁决
- 在 PROJECT_PROFILE.md 审阅通过前开始领域规则生成
