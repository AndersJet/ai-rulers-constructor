# Web API 集成规范

```yaml
metadata:
  applies_to:
    - frontend-browser/**
    - browser/**
    - browser-client/**
  trigger_keywords:
    - api
    - client contract
    - request
    - response
    - error handling
    - integration
    - API
    - 客户端契约
    - 请求
    - 响应
    - 错误处理
    - 集成
  must_load_with:
    - ../../../AGENTS.md
    - ../../../core/HARD_CONSTRAINTS.md
    - INDEX.md
```

---

## 1. 契约来源

- 使用生成的 API 契约来源，或其他目标项目认可的契约来源。
- 当契约来源存在时，不得手写与其分歧的请求或响应结构。
- 契约变更必须识别对调用方和服务端行为的兼容性影响。

---

## 2. 错误处理

- 按既有项目模式一致处理加载、空状态、校验、授权、冲突、网络和意外失败。
- 不得将服务端授权失败隐藏为成功。
- 错误信息必须可操作，并且不得暴露敏感数据。

---

## 3. 集成纪律

- 当目标项目已集中管理共享请求行为时，应在该位置集中处理。
- 保留既有认证、重试、取消、序列化和可观测性约定。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写 API 契约位置、客户端生成流程、请求工具、错误处理约定、认证行为和验证命令。如果未记录契约来源，在新增集成模式前要求确认。
