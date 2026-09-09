# README 流程图与验证记录

三类 workflow，各提供中英文版本。README 使用静态 SVG；HTML 为 archify 的已验证交互产物。

## 适用范围

绿地与棕地图展示单项目内部的发现、画像、审阅和激活阶段，不展示主子工程的批次编排。默认 Skill 入口通过 init-plan/init-apply 自动发现模块并集中审阅；完整流程见 [initialization reference](../../../skills/ai-rulers-init/references/initialization.md)。重复初始化检查增量，不要求用户逐工程重新执行整张图。

本次只补充图示范围说明，源 JSON、交互 HTML、静态 SVG 及对应哈希凭据保持原样。

## 内容依据

- `skills/ai-rulers-init/references/discovery.md`：approved 与 observed 的区别。
- `references/lifecycle.md`、`generation.md`、`activation.md`：草稿、审阅、候选与激活门禁。
- `templates/runtime/AGENTS.md.tmpl`：Context、最低 core、领域与模块选择、阻断处理。
- `scripts/rulers_lib/rule_loading.py`、`module_loading.py`：有效规则、必需依赖、模块快照加载。

初始化图描述首次建立框架；修订后回到对应审阅步骤。无领域需求的低风险任务可以只使用已审阅 core 与事实。任务图概括有领域规则需求的路径，范围选择后仍须复验状态。关系未标注文字时，相邻动作已表达顺序；通过、未通过、阻断等分支保留显式标签。

## 验证

- 每份最终 JSON/HTML 均通过 9 项 showcase 检查，0 错误、0 警告。
- 六份 HTML 均通过 archify visual-check：1440×900、1600×1000、1920×1080、2048×1320 无页面溢出。
- 已检查浅色／深色截图及节点、连线、文字；修正了一轮标题与图标的视觉拥挤。
- SVG 从交付 HTML 提取，内联浅色样式，移除查看器控件和脚本；另以 CairoSVG 检查静态呈现。
- 交互菜单、搜索、焦点和实际下载操作未逐项人工测试；自动浏览器检查与截图审阅不代表真实模型工作流效果评测。

完整哈希与状态见 [verification.json](verification.json)。单图的 `*.delivery.json` 是规格／HTML 字节凭据，`*.visual-check.json` 与对应截图是浏览器证据；自动记录中的 visualReview 保持 pending，本文件与 verification.json 单独记录截图审阅。

## 交互文件

| 流程 | 中文 | English |
| --- | --- | --- |
| 绿地初始化 | [greenfield-init.zh.html](greenfield-init.zh.html) | [greenfield-init.en.html](greenfield-init.en.html) |
| 棕地初始化 | [brownfield-init.zh.html](brownfield-init.zh.html) | [brownfield-init.en.html](brownfield-init.en.html) |
| 任务规则加载 | [task-loading.zh.html](task-loading.zh.html) | [task-loading.en.html](task-loading.en.html) |

## 更新图表

修改对应 JSON 后，使用 archify 的 validate → deliver → visual-check 重新验证。已交付 HTML 不手工改写。README 静态图需要同步刷新，并核对图与文字含义一致。
