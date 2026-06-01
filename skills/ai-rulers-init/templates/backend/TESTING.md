# 后端测试规范

```yaml
metadata:
  applies_to:
    - backend/**
    - server/**
    - services/**
  trigger_keywords:
    - test
    - verification
    - behavior
    - security
    - permission
    - 测试
    - 验证
    - 行为
    - 安全
    - 权限
    - 后端测试
  must_load_with:
    - ../AGENTS.md
    - ../core/HARD_CONSTRAINTS.md
    - INDEX.md
```

---

## 1. 测试位置

- 行为变更需要在最低且可靠的层级补充测试。
- 测试应使用目标项目真实的测试框架，而不是发明并行工具链。
- 当存在既有 fixture、factory、环境设置和辅助工具约定时，优先复用这些约定。

---

## 2. 按风险要求的覆盖

- 安全、权限和数据边界变更需要负向路径测试。
- 契约变更需要为受影响消费者提供测试或有记录的验证。
- 持久化、并发、集成和配置变更需要测试；若测试不可行，则需要明确且有审阅支撑的替代方案。

---

## 3. 验证命令

- 验证命令来自 `PROJECT_PROFILE.md` 和本领域生成的规范。
- 不得使用无关工具替代目标项目既有检查。
- 如果命令无法运行，必须记录阻塞原因、跳过的覆盖范围和剩余风险。

---

## AI_FILL

根据 `PROJECT_PROFILE.md` 生成项目特定的测试路径、测试框架名称、fixture 约定、覆盖率预期和验证命令。如果测试事实未经观察或人工确认，则保持生成规则的通用性，并要求在声明后端行为已验证前进行审阅。
