# Domain docs

采用 single-context 布局：根 `CONTEXT.md` 记录领域词汇与边界，`docs/adr/` 保存架构决定。

## 读取规则

- 探索相关代码前，读取已有的根 `CONTEXT.md` 和命中主题的 ADR。
- 如果未来出现 `CONTEXT-MAP.md`，按其索引读取相关 context。
- 这些文档不存在时直接继续；不因缺失而阻塞，也不预先生成空文档。
- 使用 `CONTEXT.md` 中定义的术语。发现重要概念缺口时，在实际讨论中交由 domain-modeling 维护。
- 建议与现有 ADR 冲突时，明确指出冲突和需要重新讨论的决定。

## 与 rulers 的关系

本工程必需的维护约束保存在根 `AGENTS.md`；生成目标项目的默认规范来自 `skills/ai-rulers-init/templates/runtime/`。领域文档提供项目语义，不替代维护规范，也不在本工程恢复 Skill 安装状态。
