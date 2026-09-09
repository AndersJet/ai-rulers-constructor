# 后端规范索引

```yaml
metadata:
  applies_to:
    - backend/**
    - server/**
    - services/**
  trigger_keywords:
    - backend
    - server
    - api
    - service
    - configuration
    - observability
    - 后端
    - 服务端
    - 接口
    - 服务
    - 配置
    - 可观测性
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
```

---

## 1. 条件加载

处理后端、服务端、API 与服务行为任务时，先加载本索引，再按任务条件加载叶子规则：

| 任务条件 | 还需加载 |
| --- | --- |
| 模块边界、服务职责、契约或架构模式 | [{{RULERS_DIR}}/backend/ARCHITECTURE.md]({{RULERS_DIR}}/backend/ARCHITECTURE.md) |
| API、认证、授权、输入校验、响应安全 | [{{RULERS_DIR}}/backend/API_SECURITY.md]({{RULERS_DIR}}/backend/API_SECURITY.md) |
| 行为变更、回归修复、验证或收尾声明 | [{{RULERS_DIR}}/backend/TESTING.md]({{RULERS_DIR}}/backend/TESTING.md) |
| 持久化、仓储、数据映射 | [{{RULERS_DIR}}/backend/DATA_ACCESS.md]({{RULERS_DIR}}/backend/DATA_ACCESS.md) |
| 运行时配置、环境、功能开关、密钥 | [{{RULERS_DIR}}/backend/CONFIGURATION.md]({{RULERS_DIR}}/backend/CONFIGURATION.md) |
| 日志、指标、链路追踪、定时任务、运维故障模式 | [{{RULERS_DIR}}/backend/OBSERVABILITY.md]({{RULERS_DIR}}/backend/OBSERVABILITY.md) |
| Schema、migration、seed、backfill | [{{RULERS_DIR}}/database/INDEX.md]({{RULERS_DIR}}/database/INDEX.md) |

---

## 2. 激活说明

后端工作必须遵循 [{{RULERS_DIR}}/AGENTS.md]({{RULERS_DIR}}/AGENTS.md) 与 [{{RULERS_DIR}}/core/HARD_CONSTRAINTS.md]({{RULERS_DIR}}/core/HARD_CONSTRAINTS.md) 中的激活等级和证据要求。认证、授权、持久化行为、运维行为以及其他高风险后端变更，在实施前需要 Level 2 或更高等级，并具备已审阅的项目特定事实。

---

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 将通用后端路径、命令、运行时名称、框架名称、鉴权模型和验证命令替换为目标项目事实。如果后端事实未经观察或人工确认，则将后端保持在 Level 0 或 Level 1，不授权高风险后端变更。
