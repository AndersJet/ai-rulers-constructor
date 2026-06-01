# Rules 完整性检查清单

> **角色**: 跟踪各领域规则的生成、审阅和激活状态，判断规则体系是否完备可激活。

```yaml
metadata:
  applies_to:
    - "{{RULERS_DIR}}/**"
    - PROJECT_PROFILE.md
    - AGENTS.md
  trigger_keywords:
    - completeness checklist
    - rules completeness
    - activation checklist
    - bootstrap
    - review protocol
    - 完整性检查
    - rules 完整性
    - 激活检查清单
    - 激活等级
    - 启动引导
    - 审阅协议
  must_load_with:
    - ../AGENTS.md
    - PROJECT_DISCOVERY.md
    - BROWNFIELD_RULE_GENERATION.md
    - ACTIVATION_LEVELS.md
```

---

## 目的

跟踪哪些 rule 领域存在、项目事实是否已生成、人工审阅是否完成，以及允许的激活等级。

在模板启动引导期间，以及任何平台、模块、部署或 rule 路由变更之后，使用此检查清单。

---

## 完整性矩阵

| 领域 | 是否存在 | 项目事实已生成 | 已审阅 | 激活等级 | 验证命令 |
| --- | --- | --- | --- | --- | --- |
| core | 是 | 不需要 | 待处理 | 经审阅的 `PROJECT_PROFILE.md` 证据支持 core 激活后为 Level 1 | `python3 {{RULERS_DIR}}/scripts/validate_rulers.py` |
| backend | 待确认 | 待确认 | 待处理 | 生成、校验并审阅前为 Level 0 | 待确认 |
| database | 待确认 | 待确认 | 待处理 | 生成、校验并审阅前为 Level 0 | 待确认 |
| frontend/common | 待确认 | 待确认 | 待处理 | 生成、校验并审阅前为 Level 0 | 待确认 |
| frontend/web | 待确认 | 待确认 | 待处理 | 生成、校验并审阅前为 Level 0 | 待确认 |
| frontend/app | 待确认 | 待确认 | 待处理 | 生成、校验并审阅前为 Level 0 | 待确认 |
| security | 待确认 | 待确认 | 待处理 | 生成、校验并完成带明确风险接受的审阅前为 Level 0 | 待确认 |
| release | 待确认 | 待确认 | 待处理 | 回滚、验证证据与人工审阅支持 Level 3 前为 Level 0 | 待确认 |

---

## 审阅协议

- 未经人工审阅的领域不得标记为 Level 2。
- 高风险领域没有明确的审阅人接受记录时，不得标记为 Level 2。
- 缺少回滚与验证证据时，release 不得标记为 Level 3。
- 已删除或重命名的平台目录必须反映到 `AGENTS.md`、`INDEX.md` 与此检查清单中。

---

## 检查清单维护规则

- 保持“是否存在”与已观察仓库结构、人工确认的领域边界一致。
- 只有当相关项目画像章节包含已确认证据或明确的未确认事实条目后，才能标记“项目事实已生成”。
- 只有当人工已审阅领域 rules 或明确接受风险等级后，才能标记“已审阅”。
- 当证据不完整或存在冲突时，保持激活等级保守。
- 只有在项目发现识别出权威命令来源后，才能用项目专属命令替换“待确认”验证命令。
- 如果某个领域被有意省略，请将其标记为不存在，并移除或禁用会加载它的路由。

---

## 退出检查

使用生成的 rules 执行实施工作前：

1. 确认 `PROJECT_PROFILE.md` 存在，且经审阅证据支持所请求的激活等级。
2. 确认目标领域行存在于此检查清单中。
3. 确认目标领域的激活等级允许所请求的工作。
4. 确认验证命令已知，或命令缺失已被明确审阅。
5. 确认高风险审阅要求已满足。
6. 运行校验并解决结构性失败。