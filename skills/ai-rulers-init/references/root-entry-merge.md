# 根入口合并参考

## 区块格式

- 新区块使用无版本边界：`<!-- ai-rulers-init:begin -->` / `<!-- ai-rulers-init:end -->`。
- 解析器继续识别旧 `version=2`、`version=3` 区块；upgrade 时原位转换，保留区块外人工正文。未知带版本标记仍拒绝。
- 恰好一个合法受管区块是入口结构要求；有效运行态仍需 Context 校验。
- 区块边界不表示产品版本。发布版本用 `python3 scripts/rulers_init.py --version` 查询；安装记录以 State 的 `template.version` 为准。

## 合并规则

- 保留人工根正文（block 外的所有内容）
- 已有 CLAUDE.md 时同步合并 block；缺失时不创建
- 双区块或畸形区块报 RootEntryConflictError

## Context Fallback

- Context blocked=true、非零退出或非法 JSON 时立即 Level 0
- 仍加载 HARD + WORKFLOW，但不加载 Profile/领域 INDEX
- 不得通过读取 State 自由推断 Context 内容
