# 迁移参考（v1/v2 -> Schema 3）

## v1 迁移

python3 scripts/rulers_init.py migrate-v1 --project-root . --rulers-dir documents/rulers --apply

内部构建 operation=upgrade 并调用统一 apply；保留画像与人工内容；未登记文件冲突时停止，不覆盖。迁移结果保持 draft，不把旧画像文字当作批准。

## v2 -> Schema 3 升级

通过 plan --operation upgrade 创建升级计划：

- 画像满足当前格式、内容 hash 匹配且审阅证据完整时保留批准；否则保留正文并降为 draft
- 不完整 review 降级：Profile -> Draft，Core -> Level0
- incremental_pending 提取为独立 reconcile 输入
- 根 block 原位替换为无版本边界，人工正文保留；旧 version=2/3 仅作兼容输入
- 合并安装版本到 `template.version`，移除旧 `template_version` 重复字段
- 保留 policy/rulers_dir/ownership；readiness 仅在依赖与审阅仍有效时保留
