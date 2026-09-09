# 项目协作约定

本仓库开发和分发 `ai-rulers-init` Skill。根 AGENTS.md 是本工程的协作入口，以下约束只用于维护本仓库。

## 项目边界

- 当前生成模板以 `skills/ai-rulers-init/templates/runtime/` 为准，工作流以 `skills/ai-rulers-init/SKILL.md` 及其 references 为准。
- 本工程不安装自身 Skill，不生成项目画像、State 或受管入口。目标项目的激活等级不用于限制本仓库维护。
- 初始化、迁移、修复和模块同步在临时目标项目中验证；操作真实业务仓库需要用户针对目标和动作的授权。

## 实施与验证

- 修改前检查相关源码、调用方、现有约定和影响范围，确定验收方法。
- 保留无关人工修改和其他任务的暂存区；不覆盖、回滚或清理未知归属的变更。
- 外部输入先校验；路径、哈希、状态、事务及加载清单由脚本确定，不交给模型自由裁决。
- 不写入或输出密钥、凭据和敏感数据，不绕过安全、审阅与验证门禁，不将占位实现作为交付。
- 行为变更配套回归测试，运行与改动相关的检查。明确报告失败、未执行项和剩余风险，不用结构检查宣称真实模型效果。
- 删除、迁移、部署、回滚等高影响操作按用户明确授权的范围执行。

## 规则维护

- 修改 Skill 前读取其 SKILL.md，再按任务加载相关 reference，不整树加载。
- 改动规则、路由、所有权或校验契约时，先说明原因、影响层级、目标文件与验证方式。
- 入口负责加载，INDEX 负责导航，叶子负责专题约束，Profile 负责项目事实，State 负责生命周期与审阅记录；每项要求保留一个权威正文。
- 规则须有适用范围、证据与验证依据；新增、删除或移动叶子时同步索引和依赖。升级保留项目定制与批准的删除决定。
- 冲突依据适用的指令、用户批准决定、作用域与来源处理，说明取舍；模板示例不能冒充项目事实。

## 提交门禁

- 用户要求提交后，仅暂存本次已授权范围；检查工作区、暂存差异和 CHANGELOG，展示文件清单与提交草案，确认后提交。
- commit 的 type 使用英文；subject 使用中文动宾结构，不超过 50 字；body 使用中文，包含“改了什么、为什么、影响范围”。此格式适用于所有 Skill 或命令发起的提交。
- feat/fix 必须更新 CHANGELOG.md，并与实现进入同一提交；面向用户的文档变化记入 Changed。
- 推送、修订提交、变基、强制操作或删除分支需要对应授权，不从一次提交授权推断。

## 按需参考

- 开发命令、测试与打包：[CONTRIBUTING-zh.md](CONTRIBUTING-zh.md)。
- Skill 维护：[skills/ai-rulers-init/SKILL.md](skills/ai-rulers-init/SKILL.md)。
- GitHub Issues：`AndersJet/ai-rulers-constructor`，按 [issue-tracker.md](docs/agents/issue-tracker.md) 操作；标签见 [triage-labels.md](docs/agents/triage-labels.md)。配置本身不构成远端写入授权。
- 术语与架构决定：按 [domain.md](docs/agents/domain.md) 读取已有 CONTEXT.md 和相关 ADR；缺失时不生成空文档。
