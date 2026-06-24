# 实施工作流

> **角色**: 面向 AI 辅助开发、感知激活等级的通用执行工作流。

```yaml
metadata:
  applies_to:
    - "**/*"
  trigger_keywords:
    - workflow
    - implementation
    - plan
    - activation
    - verification
    - closeout
    - 工作流
    - 实施
    - 计划
    - 激活
    - 激活等级
    - 验证
    - 收尾
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
```

---

## 1. 必需思维顺序

```text
Analyze dependencies -> Check constraints -> Verify patterns -> Write code
```

在依赖、约束和模式检查达到任务范围所需的充分程度之前，不得编写或修改实现。

---

## 2. 标准执行阶段

1. 影响分析：识别会触及的模块、所有者、数据流、下游契约、安全边界和验证需求。
2. 命中规则加载：仅加载 `AGENTS.md`、常驻核心规则、存在时的 `PROJECT_PROFILE.md`、相关领域 `INDEX.md` 文件以及命中的叶子规则。
3. 激活检查：确认当前激活等级允许该任务；当任务需要更高等级时，停止或请求审阅。
4. 模式复用：检查现有项目约定，并复用既有结构、命名、测试、错误处理、日志和配置模式。
5. 实施：在保留无关用户工作的前提下，做出满足任务的最小一致变更。
6. 验证：运行 `PROJECT_PROFILE.md` 和命中领域规则要求的命令；当验证无法运行时记录阻塞原因。
7. 规则影响评估：评估本次工作是否改变了模式、约束、路由、激活、校验或规则结构。
8. 如需提交则执行提交门禁：
   a. 重新加载 `{{RULERS_DIR}}/core/GIT_COMMIT_CONVENTION.md`，不得依赖历史记忆。
   b. 运行 `git log --oneline -20` 识别历史格式，警告自身历史中可能存在违规格式，不得模仿。
   c. 运行 `git diff --cached --stat` 和 `git diff --cached` 收集变更证据。
   d. 按 `GIT_COMMIT_CONVENTION.md` 第5.1-5.5节推断 type、scope、subject、body。
   e. 判断是否需要更新 `CHANGELOG.md`，如需则在 `[Unreleased]` 下追加条目并一并 `git add`。
   f. 展示提交信息草案和文件清单等待用户确认。
   g. 用户确认后执行 `git commit`；没有明确人工确认不得提交。

---

## 3. 开始前检查清单

修改文件前，确认：

- 已理解任务目标、范围和排除路径。
- 已识别相关文件、模块和依赖。
- 已通过路由链加载必需核心规则以及任何相关领域规则。
- `PROJECT_PROFILE.md` 中的事实和激活状态已知，或任务仅限于允许的项目发现/模板工作。
- 激活等级允许执行该工作。
- 已检查现有实现模式。
- 已评估安全、数据、发布和生产风险。
- 已知验证命令和预期证据。
- 将保留任何用户拥有的无关变更。

---

## 4. 收尾检查清单

报告完成前，确认：

- 适用时，已通过 `AGENTS.md` 和领域 `INDEX.md` 文件加载命中的规则。
- 激活等级允许该任务。
- 行为变更已有测试，或已记录无法测试的原因。
- 必需验证命令已运行，或已记录阻塞原因。
- 当工作改变模式、约束或规则结构时，已执行规则影响评估。
- 文件变更仅限于批准范围。
- 除非用户明确请求并确认，否则未创建提交。
