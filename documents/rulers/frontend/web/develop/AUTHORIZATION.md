# Web 授权规范

```yaml
metadata:
  applies_to:
    - frontend-browser/**
    - browser/**
    - browser-client/**
  trigger_keywords:
    - authorization
    - permission
    - guard
    - role
    - access control
    - 授权
    - 权限
    - 守卫
    - 角色
    - 访问控制
  must_load_with:
    - ../../../AGENTS.md
    - ../../../core/HARD_CONSTRAINTS.md
    - INDEX.md
```

---

## 1. 权威边界

- 客户端守卫只属于用户体验层。
- 受保护操作依赖服务端规则作为最终授权决策。
- 绝不能将仅前端权限检查作为敏感数据或状态变更的唯一保护。

---

## 2. 用户体验行为

- 路由和组件守卫应在用户执行不可用操作前提供引导。
- 当目标项目区分未认证和无权限状态时，两者必须在视觉上明确不同。
- 除非目标项目明确规定该行为，否则不得将授权失败转换为成功的空状态。

---

## 3. 变更纪律

- 权限键、角色和能力变更必须追溯到其权威来源。
- 更新必须考虑导航、直接 URL 进入、条件控件、API 失败和缓存状态。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写授权来源、守卫位置、权限命名、导航规则、错误展示约定和验证命令。未记录的敏感授权假设应保持待确认状态。
