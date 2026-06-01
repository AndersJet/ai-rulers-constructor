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
    - ../AGENTS.md
    - ../core/HARD_CONSTRAINTS.md
```

---

## 1. 必读文档

处理后端、服务端、API 与服务行为任务时，加载以下后端规范：

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [API_SECURITY.md](API_SECURITY.md)
- [TESTING.md](TESTING.md)

---

## 2. 条件加载

| 任务条件 | 还需加载 |
| --- | --- |
| 持久化、仓储、数据映射 | [DATA_ACCESS.md](DATA_ACCESS.md) |
| 运行时配置、环境、功能开关、密钥 | [CONFIGURATION.md](CONFIGURATION.md) |
| 日志、指标、链路追踪、定时任务、运维故障模式 | [OBSERVABILITY.md](OBSERVABILITY.md) |
| Schema、migration、seed、backfill | [../database/INDEX.md](../database/INDEX.md) |

---

## 3. 激活说明

后端工作必须遵循 [../AGENTS.md](../AGENTS.md) 与 [../core/HARD_CONSTRAINTS.md](../core/HARD_CONSTRAINTS.md) 中的激活等级和证据要求。认证、授权、持久化行为、运维行为以及其他高风险后端变更，在实施前需要 Level 2 或更高等级，并具备已审阅的项目特定事实。

---

## 4. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 将通用后端路径、命令、运行时名称、框架名称、鉴权模型和验证命令替换为目标项目事实。如果后端事实未经观察或人工确认，则将后端保持在 Level 0 或 Level 1，不授权高风险后端变更。
