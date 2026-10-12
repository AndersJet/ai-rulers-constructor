# README 流程图与验证记录

三类 workflow，各提供中英文版本。README 使用静态 SVG；HTML 为 archify 的已验证交互产物。

## 适用范围

绿地与棕地图展示默认 init-plan/init-apply 流程：发现工程与业务证据、准备最小候选、集中审阅实际差异、采纳并验证。主子工程由同一入口编排，未初始化模块保留待接入；完整流程见 [initialization reference](../../../skills/ai-rulers-init/references/initialization.md)。重复初始化检查增量，无变化直接结束。

任务图区分已知选择直接 load 与未知范围先 Context/INDEX，load 校验状态并展开真实依赖。执行反馈先判断正文、路由或无需改动，确需调整时才进入维护。图示不表达统一分支/CI 编排，也不将规则生效等同生产授权。

## 内容依据

- `skills/ai-rulers-init/references/discovery.md`：approved 与 observed 的区别。
- `references/lifecycle.md`、`generation.md`、`activation.md`：草稿、审阅、候选与激活门禁。
- `references/rule-quality.md`、`maintenance.md`：单一权威正文、语义去重及最小完整维护。
- `templates/runtime/AGENTS.md.tmpl`：Context、最低 core、领域与模块选择、阻断处理。
- `scripts/rulers_lib/rule_loading.py`、`module_loading.py`：有效规则、必需依赖、模块快照加载。

初始化图描述首次建立框架；修订后重新计划并按适用授权审阅。无领域需求的低风险任务可以只使用已审阅 core 与事实。图中来源引用绑定本仓库实现提交 `29152856816e24fd2747f9c1c460590c6ec3b313`，使用该提交的源码与 GitHub 永久链接。后续文档提交不改变所引用的实现；普通 clone 获取该提交后即可使用 `--repo-root .` 复验。

## 验证

- 六份最终 JSON/HTML 均通过 showcase validate、deliver、严格 provenance check 和真实浏览器 browser-check；0 错误、0 警告。
- 自动浏览器检查覆盖 1440×900、1600×1000、1920×1080、2048×1320；当前截图与凭据在 `quality-1.0.0/`。
- 已逐份目视检查最终 1440×900 浅色/深色截图中的节点、连线与文字；六份均未发现文字溢出或连线遮挡。
- SVG 从当前交付 HTML 的 DOM 提取，内联浅色样式，清理查看器辅助层并规范化颜色及中文字体/分隔符；六份均经 CairoSVG 渲染与目视检查，XML 有效且无脚本或 foreignObject。
- 交互菜单、搜索、焦点和实际下载操作未逐项人工测试；自动浏览器检查与截图审阅不代表真实模型工作流效果评测。

完整哈希与当前状态见 [verification.json](verification.json)。根目录 `*.delivery.json` 是当前规格/HTML 凭据；`quality-1.0.0/` 保存新图的 finalize、browser-check 和 visual-check 记录。旧仓库的截图与验证凭据不随本次发布分发。自动记录中的 visualReview 保持 pending，本文件与 verification.json 单独记录实际截图审阅。

本轮使用 Archify 3.0.1 的临时副本，仅在写入与计算哈希前去除空白行上的空格，以满足仓库格式检查；未修改全局工具、校验器或交付后的 HTML。所有最终凭据均绑定规范化后的真实产物。

## 交互文件

| 流程 | 中文 | English |
| --- | --- | --- |
| 绿地初始化 | [greenfield-init.zh.html](greenfield-init.zh.html) | [greenfield-init.en.html](greenfield-init.en.html) |
| 棕地初始化 | [brownfield-init.zh.html](brownfield-init.zh.html) | [brownfield-init.en.html](brownfield-init.en.html) |
| 任务规则加载 | [task-loading.zh.html](task-loading.zh.html) | [task-loading.en.html](task-loading.en.html) |

## 更新图表

修改对应 JSON 后使用当前 archify 的 finalize 完成 validate → deliver → check → browser-check，再用 visual-check 获取截图并目视检查；已有截图绑定旧产物时使用新的证据目录。已交付 HTML 不手工改写。README 静态图从最新 HTML 重新导出，核对图文含义、双语、源码快照与字节凭据一致。

### Archify 3.0.1 的格式兼容

该版本在生成 HTML 时保留部分空白行缩进。仓库附带[单行补丁](archify-whitespace.patch)，只在临时工具副本中规范化这些空白，校验器和全局安装保持原样。下列命令从本仓库根执行；先把工具路径设为实际安装位置：

```bash
RULERS_ARCHIFY_SOURCE=/absolute/path/to/archify
test "$(shasum -a 256 "$RULERS_ARCHIFY_SOURCE/renderers/shared/cli.mjs" | cut -d ' ' -f 1)" = 097f968a614008b07972f56de995e5b933c61ee0ba0d16d967c0a97c6d92e9d7 || exit 1
RULERS_ARCHIFY_TMP=$(mktemp -d)
cp -R "$RULERS_ARCHIFY_SOURCE/." "$RULERS_ARCHIFY_TMP/"
patch --batch -p1 -d "$RULERS_ARCHIFY_TMP" < assets/diagrams/rulers-flows/archify-whitespace.patch
node "$RULERS_ARCHIFY_TMP/bin/archify.mjs" finalize workflow assets/diagrams/rulers-flows/task-loading.zh.json assets/diagrams/rulers-flows/task-loading.zh.html --repo-root . --quality showcase --out-dir /tmp/rulers-flow-review --json
node "$RULERS_ARCHIFY_TMP/bin/archify.mjs" visual-check assets/diagrams/rulers-flows/task-loading.zh.html --out-dir /tmp/rulers-flow-review --summary --require-provenance
```

校验失败时先核对工具版本和图示引用的源码提交，不把补丁强行套到其他版本。再次修订图示时使用新的证据目录；其余五图按相同方式处理。此补丁不改变图示内容或验证门禁。
