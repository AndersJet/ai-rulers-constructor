# 规则维护协议

> **角色**: 此可复用模板的规则影响评估与结构维护决策树。

```yaml
metadata:
  applies_to:
    - "{{RULERS_DIR}}/**"
    - AGENTS.md
    - PROJECT_PROFILE.md
    - scripts/**
  trigger_keywords:
    - ruler impact assessment
    - maintain rules
    - update rules
    - validate rulers
    - domain index
    - leaf rule
    - bootstrap
    - validation script
    - 规则影响评估
    - 维护规则
    - 更新规则
    - 校验规则
    - 领域索引
    - 叶子规则
    - 校验脚本
    - 规范维护
  must_load_with:
    - ../AGENTS.md
    - HARD_CONSTRAINTS.md
    - DOC_GOVERNANCE.md
```

---

## 1. 必需的规则影响评估

当工作改变开发模式、约束、路由、激活等级、校验、规则结构或已记录的权威来源时，AI 必须在修改规则前执行此评估：

```text
1. 是否需要规则更新：是 / 否
2. 变更层级：全局 / 领域索引 / 叶子规则 / 项目画像 / 引导规则 / 校验脚本
3. 目标文件：...
4. 验证命令：python3 {{RULERS_DIR}}/scripts/validate_rulers.py
```

如果答案是“否”，说明为什么现有规则已经覆盖该变更，或为什么该任务不属于规则范围。

---

## 2. 决策规则

### 修改 `AGENTS.md`

仅当更新影响全局加载顺序、路由类别、激活门禁定义、常驻核心规则、冲突顺序或所有任务行为时，才修改 `AGENTS.md`。

不要把详细的领域实现规则放入 `AGENTS.md`。

### 修改领域 `INDEX.md`

当在某领域新增、移除、重命名、拆分或合并叶子规则文件，或某类任务的条件加载发生变化时，修改领域 `INDEX.md`。

`INDEX.md` 文件应包含导航、必需加载、条件加载和收尾路由。不应包含长篇可执行规则正文。

### 修改叶子规则

当为某一专题新增或细化可执行约束、示例、验证命令、允许模式、禁止模式或收尾检查时，修改叶子规则。

如果创建新的叶子规则，必须在同一变更中从所属 `INDEX.md` 链接它。

### 修改 `PROJECT_PROFILE.md`

当目标项目事实、命令、证据、置信度、激活状态、所有权、集成、安全模型、部署模型或未确认事实发生变化时，修改 `PROJECT_PROFILE.md`。

不要在 `PROJECT_PROFILE.md` 中存放通用模板策略。

### 修改引导规则

当项目发现、项目画像生成、棕地规则生成、激活晋级或完整性审阅工作流发生变化时，修改引导规则。

不要使用引导规则绕过激活门禁；引导工作用于发现并生成已审阅规则。

### 修改校验脚本

当某条结构规则应被机器检查时，修改校验脚本，例如必需 metadata 字段、必需链接、路由可达性、激活声明或禁止占位符。

当脚本发生变化时，包含一次校验运行结果，或记录其无法运行的原因。

---

## 3. 结构维护要求

- 每个核心、领域索引、引导规则和叶子规则文档都必须包含带必需 metadata 字段的围栏式 `yaml` metadata 块。
- 每条已激活叶子规则都必须能从 `AGENTS.md` 通过 `INDEX.md` 路由或已记录引导路由到达。
- `metadata.must_load_with` 必须使用可解析的相对路径，或使用同一目录内的文件名。
- 模板占位符和示例不得在没有证据的情况下成为已激活项目事实。
- 规则文件必须避免复制由另一个规则文件拥有的完整正文。

---

## 4. 校验

首选校验命令：

```bash
python3 {{RULERS_DIR}}/scripts/validate_rulers.py
```

如果脚本尚不存在或无法在目标环境中运行，记录该阻塞原因，并执行可用的最强结构检查。