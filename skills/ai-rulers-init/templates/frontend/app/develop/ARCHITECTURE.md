# App 架构规范

```yaml
metadata:
  applies_to:
    - frontend-mobile/**
    - touch-client/**
    - mobile-client/**
    - mobile/**
  trigger_keywords:
    - mobile architecture
    - navigation
    - page state
    - platform boundary
    - offline
    - network
    - 移动端架构
    - 导航
    - 页面状态
    - 平台边界
    - 离线
    - 网络
  must_load_with:
    - ../../../AGENTS.md
    - ../../../core/HARD_CONSTRAINTS.md
    - INDEX.md
```

---

## 1. 导航与页面状态

- 保留目标项目的导航模型和页面状态所有权。
- 当导航、刷新、后台运行或返回流程相关行为重要时，定义状态如何保留。
- 未经项目批准，不得引入平行导航或页面生命周期模式。

---

## 2. 平台边界

- 将平台专属能力保留在已建立的项目边界之后。
- 除非目标项目已经使用该模式，否则避免将可复用业务逻辑耦合到设备、浏览器或宿主 API。
- API 和授权行为必须与前端和服务端契约保持一致。

---

## 3. 离线和弱网行为

相关时，移动端变更必须定义加载、重试、超时、过期数据、离线和恢复行为。除非目标项目明确规定该行为，否则不得静默丢弃用户操作。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写导航约定、页面目录、状态持久化规则、平台能力边界、API 客户端约定、离线标准和验证命令。
