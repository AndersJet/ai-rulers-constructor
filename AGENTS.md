# AI 协作协议（模板维护）

> **Version**: v1.0.0
> **Role**: ai-rulers-template 项目自身的 AI 协作入口
> **Goal**: 轻量路由，指向 documents/rulers/ 下的维护规则。

---

## 默认加载链

1. [documents/rulers/core/HARD_CONSTRAINTS.md](documents/rulers/core/HARD_CONSTRAINTS.md)
2. [documents/rulers/core/WORKFLOW.md](documents/rulers/core/WORKFLOW.md)
3. [documents/rulers/core/DOC_GOVERNANCE.md](documents/rulers/core/DOC_GOVERNANCE.md)

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
