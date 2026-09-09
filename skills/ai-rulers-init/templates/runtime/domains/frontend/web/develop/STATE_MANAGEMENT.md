# Web 状态管理规范

```yaml
metadata:
  applies_to:
    - frontend-browser/**
    - browser/**
    - browser-client/**
  trigger_keywords:
    - state
    - store
    - cache
    - server data
    - local state
    - invalidation
    - 状态
    - 状态管理
    - 存储
    - 缓存
    - 服务端数据
    - 本地状态
    - 失效
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/frontend/web/develop/INDEX.md
```

---

## 1. 状态所有权

- 实施前先识别每个被变更状态值的所有者。
- 按目标项目约定区分服务端数据、派生数据、持久化客户端偏好和局部 UI 状态。
- 避免在无关的 store、组件或缓存之间重复保存状态。

---

## 2. 缓存失效

- Mutation 必须定义哪些缓存数据会过期。
- 刷新、乐观更新、回滚和冲突行为必须遵循既有项目模式。
- 登出、账户切换或权限变更后，不得在缓存中留下授权或身份敏感数据。

---

## 3. UI 状态

- 局部 UI 状态应保持局部，除非它必须共享、持久化或恢复。
- 加载、空、错误和禁用状态必须显式表达到足以支持一致的 UI 行为。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写状态所有权约定、store 位置、缓存工具、持久化规则、失效模式和验证命令。如果所有权不清晰，在新增全局状态前要求确认。
