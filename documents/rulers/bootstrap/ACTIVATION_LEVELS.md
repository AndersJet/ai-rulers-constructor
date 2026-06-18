# 激活等级

> **角色**: 定义四级激活门禁的详细标准与晋级条件。

```yaml
metadata:
  applies_to:
    - "{{RULERS_DIR}}/**"
    - "{{RULERS_DIR}}/PROJECT_PROFILE.md"
    - AGENTS.md
  trigger_keywords:
    - activation level
    - activate rules
    - high-risk domain
    - bootstrap
    - review gate
    - 激活等级
    - 激活 rules
    - 高风险领域
    - 启动引导
    - 审阅门禁
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/bootstrap/PROJECT_DISCOVERY.md
    - {{RULERS_DIR}}/bootstrap/BROWNFIELD_RULE_GENERATION.md
    - {{RULERS_DIR}}/bootstrap/RULES_COMPLETENESS_CHECKLIST.md
```

---

## 目的

定义何时生成的 rules 可以安全用于仓库工作。

激活等级用于防止模板假设或未经审阅的生成 rules 控制高风险代码、数据、安全或发布变更。

---

## 等级

| Level | 状态 | 允许的工作 | 不允许的工作 |
| --- | --- | --- | --- |
| Level 0 | 已放入模板，尚无 `PROJECT_PROFILE.md` | 项目发现与项目画像生成 | 代码、数据库、安全、发布变更 |
| Level 1 | `PROJECT_PROFILE.md` 已存在，且经人工审阅的证据支持 core 激活 | 只读分析、低风险文档、小型本地修复 | 安全、数据库、部署、高风险集成 |
| Level 2 | 某个领域已生成、已校验且已审阅 | 在该已激活领域内工作 | 在已激活领域之外工作 |
| Level 3 | 发布规则、回滚、CI/CD、安全与质量门禁已审阅 | 经人工确认的发布影响工作 | 未确认的生产影响变更 |

---

## Level 0: 已放入模板

将模板放入仓库后立即使用 Level 0。

要求：

- 只执行项目发现。
- 在把任何 rule 视为项目专属规则前，先生成 `PROJECT_PROFILE.md`。
- 不得在 Level 0 rules 下执行代码、数据库、安全或发布变更。

退出条件：

- `PROJECT_PROFILE.md` 已存在。
- 已确认事实与未确认事实已分离。
- 已识别可用于 Level 1 激活的 core 通用约束。

---

## Level 1: 项目画像与 Core 已激活

当项目画像存在，且经人工审阅的证据支持 core rules 作为已激活规则时，使用 Level 1。审阅必须覆盖置信度、未确认事实，以及通用 core 约束对当前工作是否安全。

允许：

- 只读分析
- 低风险文档工作
- 不影响高风险领域的小型本地修复

不允许：

- 安全变更
- 数据库变更
- 部署变更
- 高风险集成变更

领域达到 Level 2 的退出条件：

- 领域 rules 基于已确认项目事实生成。
- 领域 `INDEX.md` 路由到必需的叶子 rules。
- 校验通过。
- 每个已激活领域的领域审阅均已完成。
- 高风险领域具备明确的审阅人接受记录。

---

## Level 2: 已审阅领域已激活

Level 2 用于在特定已激活领域内工作。

要求：

- 该领域存在于目标项目中。
- 领域 rules 基于 `PROJECT_PROFILE.md` 证据生成。
- 领域 rules 已校验。
- 领域 rules 已审阅。
- 高风险领域具备明确的审阅人接受记录。

允许：

- 在已激活领域内工作。
- 运行领域验证命令。
- 在证据变化时更新领域 rules，但必须遵守审阅要求。

不允许：

- 在已激活领域之外工作。
- 执行发布影响变更，除非 Level 3 已激活。
- 基于未确认事实执行生产影响变更。

---

## Level 3: 发布影响工作已激活

只有在发布规则、回滚、CI/CD、安全与质量门禁完成审阅后，才使用 Level 3。

要求：

- 发布流程已基于已确认证据记录。
- 回滚预期已记录并审阅。
- CI/CD 与质量门禁已记录并审阅。
- 安全影响已审阅。
- 发布影响工作已获得人工确认。

允许：

- 经人工确认的发布影响工作。
- 具备审阅与回滚证据的部署工作流变更。
- 仅在事实与防护措施均已确认时执行生产影响变更。

不允许：

- 未确认的生产影响变更。
- 缺少回滚证据的发布变更。
- 缺少验证证据的部署变更。

---

## 高风险最低等级

| 高风险区域 | 最低激活等级 |
| --- | --- |
| 认证与安全 | Level 2 |
| 数据库与持久化变更 | Level 2 |
| 外部集成 | 按需使用 Level 2 或 Level 3 |
| 发布与部署 | Level 3 |

当不确定某个外部集成是否影响发布或生产时，要求 Level 3 与人工确认。