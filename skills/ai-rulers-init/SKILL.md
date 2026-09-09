---
name: ai-rulers-init
description: >
  Generate and maintain a progressive Agent rules framework for greenfield or
  brownfield projects. Use for initialization, adding/editing/removing or reorganizing
  rulers, reconciling project decisions and evidence, and upgrading or repairing an
  installation. Initialization automatically discovers direct Git submodules; also use
  for explicit module export, sync and workspace adjustments.
  Ordinary feature coding and standalone prose editing are outside scope.
metadata:
  runtime: Python 3.11+ on macOS/Linux; Windows requires WSL. No third-party runtime dependencies.
---

# AI Rulers

生成可持续维护的项目规范脚手架。AI 负责证据发现、规则内容和语义审阅；脚本负责
路径、差异、状态、依赖、事务和加载清单。保留名称 ai-rulers-init 兼容已有安装。

## 入口与边界

- 先读 `references/lifecycle.md`，检查目标项目实际文件；开发本 Skill 时使用隔离目标。
- 脚本路径相对本 Skill 目录，project-root 指向目标项目；命令可从任意目录执行。
- 机器权威为目标 `RULERS_STATE.json`；日常任务运行安装目录 validator 的 Context。
- 证据分为 observed 实现事实、approved 用户设计决定；未确认项保持未决。
- 审阅记录绑定用户实际批准的内容，不自行编造批准；合成审阅仅用于隔离测试。
- 项目定制与删除决定由目标清单保存；模板是建议起点，不强制保留所有专题文件。

## 任务路由

| 任务 | 读取 |
| --- | --- |
| 初始化／再次初始化 | `references/initialization.md`，缺少候选时再读 `references/discovery.md`、`references/generation.md` |
| 新增、修改、删除、移动、合并或拆分 ruler | `references/maintenance.md` |
| 项目事实或批准决定变化 | `references/incremental.md` |
| 恢复、升级、修复 | `references/lifecycle.md` |
| 旧版无 State 安装迁移 | `references/migration-v1.md` |
| 根入口冲突／已有 CLAUDE | `references/root-entry-merge.md` |
| 画像或领域批准与激活 | `references/activation.md` |
| Git submodule 登记、模块规则导出／同步、组合调整、集中规则拆分迁移 | `references/module-workflows.md` |

## 默认初始化

```bash
python3 scripts/rulers_init.py init-plan --project-root <ABSOLUTE_PROJECT_ROOT>
```

自动发现当前根与直接子模块，默认全选；读取准备清单并按 initialization reference
准备缺少的主、子工程候选。再次运行生成增量计划，status=noop 时直接结束。
新安装默认 project-native，已有策略保留；未初始化模块等待接入，不自动拉取。

展示 review_path 中的实际差异，集中说明归属冲突与未完成范围。用户审阅后：

```bash
python3 scripts/rulers_init.py init-apply --plan <PLAN_JSON> \
  --reviewed-by <REVIEWER> --evidence <REVIEW_EVIDENCE>
```

初始化批准涵盖计划列明的主、子工程写入与规则适用性。已批准绿地设计可用于生成候选，
无需等待代码存在；未决内容不冒充事实。底层单项目 plan/apply 仍用于明确的生命周期维护。

## 维护与验证

规则内容变化使用 rules-plan/rules-apply；画像变化使用 reconcile。所有变化先给出
可审阅差异及增删原因，再按已有授权实施。规则变化降级受影响领域，审阅后重新激活。
低风险的文字改善与安全语义变化分别说明；不要因为模型能力较弱就无限增加规则。

```bash
python3 <RULERS_DIR>/scripts/validate_rulers.py --mode candidate --project-root <PROJECT_ROOT>
python3 <RULERS_DIR>/scripts/validate_rulers.py --mode runtime --project-root <PROJECT_ROOT>
```

自定义目录时每个命令追加 `--rulers-dir <RULERS_DIR>`。相同输入重复运行应零差异。
每阶段报告已做、已验证、剩余与阻塞；校验不通过时不声明可用。语义冲突由来源和审阅
解决，静态检查只证明结构与状态；不得用结构测试宣称真实模型效果已验证。
