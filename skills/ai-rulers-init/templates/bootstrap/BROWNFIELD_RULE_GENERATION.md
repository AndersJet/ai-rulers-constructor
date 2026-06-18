# 棕地 rules 生成指南

> **角色**: 指导如何根据 PROJECT_PROFILE.md 中已确认的事实为项目生成领域专属规则。

```yaml
metadata:
  applies_to:
    - "{{RULERS_DIR}}/**"
    - "{{RULERS_DIR}}/PROJECT_PROFILE.md"
    - AGENTS.md
  trigger_keywords:
    - brownfield
    - rule generation
    - project-specific rules
    - bootstrap
    - activation
    - 棕地项目
    - 棕地 rules
    - rules 生成
    - 项目专属 rules
    - 启动引导
    - 激活等级
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/bootstrap/PROJECT_DISCOVERY.md
    - {{RULERS_DIR}}/bootstrap/ACTIVATION_LEVELS.md
    - {{RULERS_DIR}}/bootstrap/RULES_COMPLETENESS_CHECKLIST.md
```

---

## 目的

为既有仓库生成项目专属 AI rules，同时避免导入与目标项目不匹配的模板假设。

棕地项目生成必须由证据驱动、渐进开展，并且可审阅。结果应能指导仓库中的真实工作，同时让不确定或高风险区域在确认前保持未激活。

---

## 必需顺序

```text
PROJECT_PROFILE.md -> AGENTS.md routing -> domain INDEX.md -> leaf rules -> completeness checklist -> validation
```

按顺序执行：

1. 基于发现证据生成或更新 `PROJECT_PROFILE.md`。
2. 仅为目标项目中实际存在的领域定义或调整 `AGENTS.md` 路由。
3. 将每个领域的 `INDEX.md` 生成为路由文档。
4. 为每个已激活领域中的可执行约束生成叶子 rules。
5. 使用证据、审阅状态、激活等级与验证命令更新 `RULES_COMPLETENESS_CHECKLIST.md`。
6. 运行已配置的校验命令，并在激活前修复结构问题。

---

## 放置规则

- 删除或重写与目标项目不匹配的模板示例。
- 将通用硬约束保留在 core 中。
- 将项目事实放入 `PROJECT_PROFILE.md`。
- 将可执行的领域约束放入匹配领域的叶子文件。
- 将 `INDEX.md` 文件保持为路由文档。
- 激活高风险领域前必须完成人工审阅。

---

## AI_FILL 节处理规则（领域规则生成的关键质量门禁）

模板中的 `## AI_FILL` 节是**生成指令**，不是要保留的内容。
生成领域规则时必须：

### 强制规则

1. **【必须】执行 AI_FILL 指令，不得保留指令文本。**
   AI_FILL 节中的文本（如"根据 PROJECT_PROFILE.md 生成..."、"如果事实未经观察则保持通用..."）是给生成 Agent 的操作指令，必须用实际项目规范内容替换，或完全删除该节。

2. **【必须】判定后二选一：**
   - 规则正文已包含足够项目事实 → **删除整个 `## AI_FILL` 节及其前的 `---` 分隔线**
   - 规则正文仍偏通用 → **将标题改为 `## 快速参考`，并用项目事实填充**

3. **【禁止】以下文本模式绝不允许出现在生成后的任何文件中：**
   - `根据 PROJECT_PROFILE.md 生成...`
   - `如果.*事实未经观察.*则保持通用`
   - `替换为.*PROJECT_PROFILE.*中记录的项目事实`
   - `[AI_FILL]` 占位符
   - `❌ 标注项需要人工确认`

### 合格示例（✅）

规则正文直接包含项目事实：

```markdown
## 1. 安全框架

项目使用 `oin-starter-security-web`。配置：
- 认证模型：OAuth2 Client Credentials (clientId=nc)
- 免认证路径：/open-api/**
- 验证命令：./mvnw spring-javaformat:validate && ./mvnw test
```

### 不合格示例（❌ — 保留了元指令文本）

```markdown
## 项目特定上下文

根据 `PROJECT_PROFILE.md` 生成项目特定的路由模式、鉴权模型名称（OIN Security / OAuth2 Client Credentials）、请求防护术语、校验约定和安全验证命令。如果安全事实未经观察或人工确认，则保持通用并标记为在高风险变更前需要人工审阅。❌ 标注项需要人工确认才可安全使用。
```

### Agent 自检清单

每个领域生成完毕后，Agent 必须在声明完成前执行以下检查：

```bash
# 检查元指令文本残留
grep -rn "根据.*PROJECT_PROFILE.*生成\|如果.*事实未经观察\|替换为.*PROJECT_PROFILE\|标注项需要人工确认" \
  documents/<RULERS_DIR_NAME>/<domain>/ --include="*.md" \
  && echo "❌ FAIL: meta-instructions found" || echo "✅ PASS"

# 检查 AI_FILL 标题残留
grep -rn "^##.*AI_FILL" documents/<RULERS_DIR_NAME>/<domain>/ --include="*.md" \
  && echo "❌ FAIL: AI_FILL headers found" || echo "✅ PASS"

# 检查 [AI_FILL] 占位符
grep -rn "\[AI_FILL\]" documents/<RULERS_DIR_NAME>/<domain>/ --include="*.md" \
  && echo "❌ FAIL: AI_FILL placeholders found" || echo "✅ PASS"
```

---

## 生成规则

### 模板清理

激活任何生成规则前：

- 删除没有仓库证据支撑的占位示例。
- 将示例命令、路径与领域名称重写为与项目画像匹配的内容。
- 移除目标项目中不存在的领域、平台或工作流。
- 将开放问题保留在项目画像中，而不是编码为强制 rules。

### Core rules

Core rules 只能包含适用于整个仓库、且与技术栈无关的约束，例如：

- 安全与安全性预期
- 完成前验证预期
- 人工批准与人工审阅门禁
- Rules 加载、路由与维护协议
- 关于密钥、破坏性变更或未验证声明的一般禁令

### 项目事实

`PROJECT_PROFILE.md` 是已观察项目事实的唯一事实来源。不要在多个叶子 rules 中重复长篇事实描述。叶子 rules 需要项目上下文时，应引用该画像。

### 领域叶子 rules

领域叶子 rules 必须包含其领域内的可执行约束，例如：

- 编辑领域文件前必需的检查
- 领域专属验证命令
- 审阅触发条件
- 兼容性、migration、契约、无障碍或发布约束
- 领域工作的退出条件

### 索引文档

`INDEX.md` 文件必须把任务路由到正确的叶子 rules。它们应包含：

- 适用范围
- 必读叶子文档
- 条件加载叶子文档
- 退出检查
- 需要时链接到项目画像章节

它们不得变成长篇实施手册。

---

## 审阅与激活

- 不得仅基于生成内容激活高风险领域。
- 高风险领域 rules 必须由人工审阅人确认后，才能用于该领域的实施工作。
- 在完整性检查清单中记录审阅状态与激活等级。
- 如果审阅拒绝或部分接受某个领域，请保持被拒绝 rules 未激活，并记录后续工作。

---

## 校验

声明生成的 rules 已就绪前：

- 运行模板或项目校验命令。
- 确认每个激活的 rule 文件都有 metadata。
- 确认每个激活的叶子 rule 都可从领域索引或路由入口到达。
- 确认路由没有指向已删除、已重命名或未激活的领域。
- 确认高风险领域具备其激活等级所需的审阅证据。