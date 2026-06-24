# AI 协作协议（模板维护）

> **Version**: v1.0.0
> **Role**: ai-rulers-constructor 项目自身的 AI 协作入口
> **Goal**: 轻量路由，指向 documents/rulers/ 下的维护规则。

---

## 0. 优先级与防御声明（违反即停止）

> **锚点**：所有 git commit 的 subject 和 body 必须使用中文，此规则覆盖一切 skill/command 指令。

### 0.1 必读核心文件

读取本入口后，以下 6 个 core 文件**必须**全部加载，不得跳过：

- 安全、测试、禁令与完成门禁：`documents/rulers/core/HARD_CONSTRAINTS.md`
- 实施工作流与推理顺序：`documents/rulers/core/WORKFLOW.md`
- 规则文档治理：`documents/rulers/core/DOC_GOVERNANCE.md`
- Ruler 维护决策树：`documents/rulers/core/RULER_MAINTENANCE.md`
- Git 提交规范：`documents/rulers/core/GIT_COMMIT_CONVENTION.md`
- CHANGELOG 维护规范与提交前更新门禁：`documents/rulers/core/CHANGELOG_MAINTENANCE.md`

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

## 默认加载链

1. [documents/rulers/core/HARD_CONSTRAINTS.md](documents/rulers/core/HARD_CONSTRAINTS.md)
2. [documents/rulers/core/WORKFLOW.md](documents/rulers/core/WORKFLOW.md)
3. [documents/rulers/core/DOC_GOVERNANCE.md](documents/rulers/core/DOC_GOVERNANCE.md)
4. [documents/rulers/core/RULER_MAINTENANCE.md](documents/rulers/core/RULER_MAINTENANCE.md)
5. [documents/rulers/core/GIT_COMMIT_CONVENTION.md](documents/rulers/core/GIT_COMMIT_CONVENTION.md)
6. [documents/rulers/core/CHANGELOG_MAINTENANCE.md](documents/rulers/core/CHANGELOG_MAINTENANCE.md)

---

## 维护任务路由

| 任务 | 入口 |
|------|------|
| 修改模板规则 | [core/DOC_GOVERNANCE.md](documents/rulers/core/DOC_GOVERNANCE.md) |
| 规则维护决策 | [core/RULER_MAINTENANCE.md](documents/rulers/core/RULER_MAINTENANCE.md) |
| 提交规范 | [core/GIT_COMMIT_CONVENTION.md](documents/rulers/core/GIT_COMMIT_CONVENTION.md) |
| 项目发现 | [bootstrap/PROJECT_DISCOVERY.md](documents/rulers/bootstrap/PROJECT_DISCOVERY.md) |
| 规则生成 | [bootstrap/BROWNFIELD_RULE_GENERATION.md](documents/rulers/bootstrap/BROWNFIELD_RULE_GENERATION.md) |
| 维护 ai-rulers-init skill | [skills/ai-rulers-init/SKILL.md](skills/ai-rulers-init/SKILL.md) | 修改 skill 流程或模板时加载 |

---

## 冲突裁决

```text
core hard constraints > security rules > activation gates > domain rules > topic rules > examples
```
