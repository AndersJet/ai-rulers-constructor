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
  must_load_with: []
```

按任务条件选择叶子；有效范围与激活状态由入口校验。

| 任务条件 | 还需加载 |
| --- | --- |
| 模块边界、服务职责、契约或架构模式 | [backend/ARCHITECTURE.md]({{RULERS_DIR}}/backend/ARCHITECTURE.md) |
| API、认证、授权、输入校验、响应安全 | [backend/API_SECURITY.md]({{RULERS_DIR}}/backend/API_SECURITY.md) |
| 行为变更、回归修复、验证或收尾声明 | [backend/TESTING.md]({{RULERS_DIR}}/backend/TESTING.md) |
| 持久化、仓储、数据映射 | [backend/DATA_ACCESS.md]({{RULERS_DIR}}/backend/DATA_ACCESS.md) |
| 运行时配置、环境、功能开关、密钥 | [backend/CONFIGURATION.md]({{RULERS_DIR}}/backend/CONFIGURATION.md) |
| 日志、指标、链路追踪、定时任务、运维故障模式 | [backend/OBSERVABILITY.md]({{RULERS_DIR}}/backend/OBSERVABILITY.md) |
| Schema、migration、seed、backfill | [database/INDEX.md]({{RULERS_DIR}}/database/INDEX.md) |

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 将通用后端路径、命令、运行时名称、框架名称、鉴权模型和验证命令替换为目标项目事实。
