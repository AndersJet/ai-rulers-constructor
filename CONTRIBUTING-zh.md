# 参与贡献

[English](CONTRIBUTING.md) · [返回 README](README-zh.md)

Rulers Constructor 维护的是 AI coding harness 的规范约束层。贡献的目标，是让项目约定更容易表达、找到、更新和验证。

一条有证据的删减、一处加载范围的修正，或一个能复现状态错误的测试，都值得提交。新增规则时，请说明它解决了什么问题，以及为什么应该由框架承载。

## 从一个具体问题开始

在 [GitHub Issues](https://github.com/AndersJet/ai-rulers-constructor/issues) 描述任务场景、预期行为与实际结果。涉及模型行为时，保留脱敏后的指令、加载内容和关键输出；涉及脚本时，提供可复现命令、运行环境和错误信息。

| 贡献方向 | 有用的证据 |
| --- | --- |
| 规则内容 | 哪个失败反复出现，已有约束为什么没起作用 |
| 渐进加载 | 哪些内容漏读、误读，或在无关任务中被加载 |
| 生命周期与恢复 | 哪组输入使审阅失效、文件被误覆盖，或事务无法恢复 |
| 项目适配 | 绿地决定、棕地事实或模块边界在哪一步表达不清 |
| 文档与示例 | 读者在哪一步停住，命令或概念与实际行为有什么出入 |

涉及规则权威、状态结构或公共命令的较大变更，先在 Issue 中说明方案和兼容影响。定位明确的修复可以直接提交 PR。请使用合成项目复现，移除客户代码、凭据和内部地址。

## 找到正确的修改位置

本仓库开发并分发 `ai-rulers-init`。目标项目安装后的规则与本仓库模板是不同的对象。

| 位置 | 负责什么 |
| --- | --- |
| [SKILL.md](skills/ai-rulers-init/SKILL.md) | Skill 入口与任务路由，保持简短 |
| [references/](skills/ai-rulers-init/references/) | 按任务加载的发现、生成、维护、迁移等操作说明 |
| [templates/runtime/](skills/ai-rulers-init/templates/runtime/) | 当前生成默认值，修改新安装内容从这里开始 |
| [scripts/rulers_lib/](skills/ai-rulers-init/scripts/rulers_lib/) | 计划、状态、校验、事务、规则加载与模块同步 |
| [tests/](tests/) | 自动化回归，包含真实临时 Git submodule 场景 |
| [evals/](skills/ai-rulers-init/evals/) | 真实模型行为评测场景，区别于脚本测试 |
| [scripts/](scripts/) | 分发构建、临时项目夹具与上下文预算报告 |

项目术语见 [CONTEXT.md](CONTEXT.md)，架构决定按需读取已有的 `docs/adr/`。用 AI 协作时先读取根 [AGENTS.md](AGENTS.md)，再按任务路由加载相关规则。

运行态验证在临时目标项目中完成。本仓库不生成自己的 `PROJECT_PROFILE.md`、`RULERS_STATE.json` 或 Skill 安装入口。

## 修改时守住的边界

**把判断与执行分开。** 模型可以发现证据、起草规则、解释冲突；哈希、路径检查、状态变化、事务和加载清单应由脚本确定。结构校验通过，不能代替规则内容的审阅。

**让每条规则有归属。** 入口负责路由，INDEX 负责导航，叶子负责具体约束，画像负责事实，State 负责生命周期与审阅记录。跨文件复制正文，会让下一次维护更难。

**让规则可以退出。** 新增能力应同时考虑修改、停用和删除。升级保留项目定制与删除决定；冲突时保留人工内容，并给出可操作的处理路径。

**让加载成本随任务增长。** 每次增加常驻内容，都要解释为什么所有任务都需要它。只与某类任务有关的内容放在条件路由后。规则细化应有失败证据，而非依靠不断叠加提醒。

**保持同一套生命周期。** 绿地的已批准决定和棕地的观察事实共用 schema 3。模块同步复用 State 与事务，主工程采纳快照不复制子工程的整份生命周期状态。

修改规则、路由、所有权或校验契约前，按根 [AGENTS.md](AGENTS.md) 中的规则维护约定记录影响层级、目标文件和验证方法，并说明权威冲突的取舍。

## 默认入口与底层命令

面向用户的初始化入口是 `init-plan` / `init-apply`。`plan/apply`、规则维护和模块命令继续作为底层能力，由默认入口复用。修改底层能力时，同时检查集中预演和应用是否仍能正确调用它。

初始化的回归范围包括：自动发现、默认全选与排除、未初始化模块、主子候选集中审阅、重复调用零差异、归属冲突保留，以及中断后对全部来源的重新校验。源码与解压分发包都要运行 `tests.test_auto_initialization`。

更新初始化行为时，同步检查 README、Skill 路由、initialization reference 和评测场景。现有绿地／棕地图展示单项目内部阶段；默认编排的变化应在图示说明中明确，不能让读者误以为需要逐工程手动初始化。

## 本地开发与验证

使用 Python 3.11+ 和 Git，在 macOS / Linux 或 WSL 中执行。运行时只依赖 Python 标准库。以下命令均从本仓库根目录运行。

先检查模板，再运行与变更相关的测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 skills/ai-rulers-init/scripts/validate_rulers.py --mode template
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_scaffold_lifecycle
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_module_workflows tests.test_auto_initialization
```

生命周期改动还应覆盖 `tests.test_ai_rulers_unified_plans`、`tests.test_ai_rulers_unified_transactions`、`tests.test_ai_rulers_unified_context` 和 `tests.test_ai_rulers_unified_upgrade_repair`。

行为测试优先走公开 CLI，在临时项目中检查最终文件、有效规则、冲突、回滚和零差异。模块测试创建真实本地 Git 仓库，不连接业务远端。测试中的审阅身份只用于夹具，不代表真实批准。

修改常驻内容或加载逻辑后，测量实际生成项目的上下文：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m scripts.report_context_budget \
  --check --format json --domain backend
```

报告先验证临时项目，并实际执行 20 次零差异 reconcile。报告中的字节数用于检查加载预算；模型正确率需要独立评测，不能从文件大小推算。

## 验证用户拿到的分发包

Skill 源码或模板改变后，先构建候选包：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m scripts.package_skill \
  --skill-root skills/ai-rulers-init --output /tmp/ai-rulers-init-candidate.skill
```

模块能力变更时，将候选包解压到一个新的临时目录，把 `RULERS_TEST_SKILL_ROOT` 指向其中的 `ai-rulers-init`，再执行同套公开流程：

```bash
RULERS_TEST_SKILL_ROOT=/absolute/path/to/extracted/ai-rulers-init \
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_module_workflows tests.test_auto_initialization
```

源码定稿后重建已跟踪分发包，再运行全量回归：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m scripts.package_skill --skill-root skills/ai-rulers-init
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

全量测试包含 `test_package_parity`、可复现构建和源码／分发包一致性检查。仅修改根 README 或 CONTRIBUTING 时无需重建 Skill 包；检查链接、命令和相关文档测试即可。

## 发布版本

发布版本唯一来源为 `skills/ai-rulers-init/scripts/rulers_lib/version.py` 中的 `RELEASE_VERSION`。
运行 `python3 skills/ai-rulers-init/scripts/rulers_init.py --version` 查询；入口模板通过占位符生成版本标题，不手写第二份数字。
State 的 `template.version` 记录安装版本；schema 和其他数据协议版本只在协议变化时调整，不能随产品发版批量替换。

准备发布时，修改唯一版本来源，将 CHANGELOG 的待发布内容归入对应版本，重建包并执行全量检查。
核对 Git 标签、Release 标题与 CLI 输出一致，上传后核对分发包 SHA-256；已有正式标签和附件不覆盖更新。

## 提交一份容易审阅的 PR

先说明具体问题与修改后的行为，再给出验证结果。写清涉及哪些规则层级、如何处理已有项目，以及有哪些未执行项。涉及模型效果时，附任务、模型、实际加载内容和结果，避免用“更智能”“更稳定”替代证据。

本仓库的提交约定：

- type 使用英文，例如 `feat`、`fix`、`docs`。
- subject 使用中文动宾结构，不超过 50 字。
- body 使用中文，说明改了什么、为什么、影响范围。
- `feat`、`fix` 与面向用户的文档变更，按类型更新 [CHANGELOG.md](CHANGELOG.md)。功能或修复的记录与实现进入同一提交。

```text
docs: 重写规范框架介绍与贡献指南

- 改了什么：围绕规范生成、维护和验证重写双语文档
- 为什么：让使用者理解 Skill 的价值与适用边界
- 影响范围：README、CONTRIBUTING 与变更记录
```

使用 AI 代为提交时，遵循[提交门禁](AGENTS.md#提交门禁)：先展示具体文件和提交草案，得到确认后执行。项目有意义的改进，也可能是让某条规则变得更短，或不再需要它。
