# 模块规则工作流

初始化由 initialization reference 自动发现并编排本工作流；用户单独要求登记、同步、调整或拆分规则时也可使用以下入口。
一个直接 Git submodule 是一个完整模块；内部前后端可有多个规则领域，不再登记第二层。
普通单仓库继续使用 lifecycle/maintenance 工作流。模块计划、导出快照和导出清单分别校验自身协议版本；未知版本须使用兼容 Skill 或重新生成输入，不修改数字绕过检查。

## 绑定入口与所有权

先确认本次会话根 ROOT：组合开发绑定主工程根，独立开发绑定子仓库根。后续每个
命令显式传 `--project-root ROOT`，即使 shell 已进入子目录。根目录来自当前会话，
不能通过寻找父目录决定模式。客户端自动读取嵌套 AGENTS 的能力由客户端控制；
出现主子入口同时注入时先明确有效工作区，不宣称此 Skill 能屏蔽客户端系统指令。

子仓库维护可移植规则源；主工程维护已采纳快照、公共约束和组合调整。
同名领域用模块身份隔离。有效文件位于 `RULERS_DIR/modules/<编码模块名>/effective/`；
该目录是生成结果，调整使用下方候选流程。每个项目的 State 独立；主工程不继承
子工程的激活或批准。组合采纳的批准必须覆盖实际内容和在主工程的适用性。

以下命令路径相对 Skill；默认 RULERS_DIR 为 documents/rulers，自定义时显式传
`--rulers-dir`。计划输出使用项目内新的候选文件名，例如 `.rulers-work/sync-01.json`。
REVIEWER/EVIDENCE 必须来自实际批准，不能照抄示例或自动编造。

## 1. 登记直接子仓库

```bash
python3 scripts/rulers_init.py modules --project-root ROOT
python3 scripts/rulers_init.py module-plan --project-root ROOT --operation register \
  --module server --module ui --output .rulers-work/register-01.json
python3 scripts/rulers_init.py module-apply --plan ROOT/.rulers-work/register-01.json \
  --reviewed-by REVIEWER --evidence EVIDENCE
```

从 `.gitmodules` 与 gitlink 验证名称、路径、仓库地址和本地检出状态。子仓库自定义
规则目录／清单时分别用 `--source-rulers`、`--manifest`，不同来源配置分开登记。
未初始化可以登记为 unavailable，但不能同步。完成标准：选中模块来源正确且未发生
Git 写操作。克隆、fetch、checkout、gitlink 更新、提交、推送均不包含在此工作流中。

## 2. 准备可移植来源

在已安装 Skill 的子仓库填写 `RULERS_DIR/MODULE_EXPORT.json`，明确列出规则、画像
scopes、命令和相关代码证据。草稿规则也可作为待主工程审阅的来源，导出不升级子项目。

```json
{
  "version": 1,
  "rules": [
    {"path": "backend/INDEX.md", "domain": "backend"},
    {"path": "backend/ARCHITECTURE.md", "domain": "backend"}
  ],
  "profile_scopes": ["core", "backend"],
  "commands": [{"name": "test", "argv": ["python3", "-m", "unittest"], "cwd": "."}],
  "evidence": ["README.md"]
}
```

上例仅示意结构，命令和 evidence 必须替换为项目真实依据。规则路径相对子项目规则根，
命令 cwd 与 evidence 相对子项目代码根。每个领域须有 INDEX 且全部叶子可达；必要依赖
也须导出。画像沿用现有 facts/scopes 契约，导出只取选定部分和项目身份。

定制 core 必须逐项处理：将模块约束提取为已导出的叶子，在 `core_decisions` 中以
core 相对路径为键，声明 `{"classification":"module","rules":["backend/ARCHITECTURE.md"],"reason":"实际理由"}`；
确属独立框架偏好则声明 `{"classification":"framework-only","reason":"实际理由"}`。
脚本阻止未分类遗漏，语义完整性仍由审阅确认。原样框架 core、入口与整份 State 不导出。

```bash
python3 scripts/rulers_init.py module-export --project-root MODULE_ROOT \
  --output .rulers-work/export-01.json
```

检查 content_id、source.head、source.dirty、input_hashes 和相关 evidence。未提交或被
Git 忽略的规则均允许正式采纳；HEAD 只作溯源，实际身份由内容哈希确定。
命令声明只随快照保存，不在导出或同步时执行。未暴露到当前子模块工作区的另一个
独立克隆中的未提交修改不可发现；远端版本需要另行明确授权 Git 操作。

## 3. 首次与增量同步

```bash
python3 scripts/rulers_init.py module-plan --project-root ROOT --operation sync \
  --module server --output .rulers-work/sync-01.json
```

先读摘要的 requires_review/conflicts，再读计划 `changes` 的变化规则和事实；需要核对
上下文时读取 captures 的必要依赖，不把所有模块正文灌入上下文。计划绑定来源、当前
代码证据、主工程状态、调整与脚本版本。无变化时 `module-apply --plan PATH` 零写入，
无需再次收集审阅；有变化则先展示增删改、来源和适用依据，经批准后：

```bash
python3 scripts/rulers_init.py module-apply --plan ROOT/.rulers-work/sync-01.json \
  --reviewed-by REVIEWER --evidence EVIDENCE
```

来源或目标已变则重新计划；同步不会写回子仓库。普通编码不调用同步，也不检查远端。
完成标准：采纳后选中模块 load 通过、仅预期文件改变、来源代码和规则均未被写入。

## 4. 主工程调整、停用与冲突

可移植修改优先在来源用 maintenance 工作流维护；本组合专属修改以候选 Markdown
和调整定义保存。候选的引用与 applies_to 使用**子仓库原始坐标**，不是已渲染路径。

```json
{
  "replace": {"backend/ARCHITECTURE.md": ".rulers-work/server-architecture.md"},
  "add": {"backend/CONTRACT.md": {"path": ".rulers-work/server-contract.md", "domain": "backend"}},
  "disable": ["backend/OPTIONAL.md"]
}
```

调整定义描述完整期望调整集合；缺省项为空，移除已有调整时显式给出新的完整集合。
新增叶子须同步替换 INDEX 以提供路由；停用 INDEX 引用自动去除，但被必需依赖的叶子
仍不能删除。`--operation adjust --module NAME --adjustments PATH` 只对已采纳来源调整，
不采纳子项目新规则；应用仍走 module-apply。后续同步保留调整和停用决定。

来源变动触及覆盖／停用项时产生冲突。逐项比较来源和组合意图，更新候选后以
`--operation sync --module NAME --adjustments PATH` 生成重新绑定当前来源的计划。
不自动合并自然语言语义。直接编辑 effective 或 adjustments.json 会阻止加载和同步；
先将人工内容保存在候选中，经审阅恢复原已采纳文件，再以调整流程采纳所需修改。
通用 repair 的 adopt-current 不能代替模块来源／调整审阅。

## 5. 从主到子渐进加载

```bash
python3 ROOT/RULERS_DIR/scripts/validate_rulers.py --mode context --project-root ROOT
python3 ROOT/RULERS_DIR/scripts/validate_rulers.py --mode context --project-root ROOT \
  --module server --domain backend
python3 ROOT/RULERS_DIR/scripts/validate_rulers.py --mode load --project-root ROOT \
  --module server --domain backend --rule backend/ARCHITECTURE.md
```

跨模块时重复 `--module`；叶子可用 `server:backend/ARCHITECTURE.md` 限定身份。
主工程组合规则另用 `--workspace-domain`／`--workspace-rule`。主 core 只加载一次；
所选模块画像按领域投影。验证命令输出 cwd 已映射到各代码根，执行前仍检查任务授权。
Context 超预算或 blocked 时收窄选择／诊断；脚本仅核验已采纳快照、Git 绑定及显式
相关代码证据，不扫描子工程规则更新。子工程独立入口沿用其自己的激活门禁。

## 6. 拆分主工程现有集中规则

先人工分离模块通用规则和组合约束，准备 ROOT 内候选目录，内含
PROJECT_PROFILE.md、MODULE_EXPORT.json 和完整可移植规则树；证据和命令改为子代码根。
主 core／安全约束保留在主工程。完成内容审阅后：

```bash
python3 scripts/rulers_init.py module-migrate-plan --project-root ROOT --module server \
  --candidate-dir .rulers-work/server-source --retire-domain backend \
  --output .rulers-work/migrate-01.json
python3 scripts/rulers_init.py module-migrate-apply --plan ROOT/.rulers-work/migrate-01.json \
  --stage source --reviewed-by REVIEWER --evidence EVIDENCE
python3 scripts/rulers_init.py module-migrate-apply --plan ROOT/.rulers-work/migrate-01.json \
  --stage complete --reviewed-by REVIEWER --evidence EVIDENCE
```

这是明确写入子仓库的迁移，先核对用户已授权具体目标。source 阶段仅在没有已有规则源
时生成独立 draft 安装，主工程旧路由仍有效；已有来源走导出／同步，不覆盖重建。
complete 在主工程一次事务内采纳快照并退休选定领域；旧文件保留，便于人工核查。
`--retire-domain` 以整个领域为单位；仍承担组合约束的领域先完成拆分，不能整体退休。

中断后重跑同一计划：仅恢复本迁移的子事务，保留无关人工修改；主工程事务中断走
lifecycle 的 journal repair 后重试。候选、旧规则、证据或准备后的来源变化会阻止继续。
需改内容时先保留已有来源，退出旧方案并以常规同步／规则维护重新计划，不强行重放。
完成标准：主工程只路由新快照，子仓库保持 draft；独立使用还需 review-profile、
领域登记／激活和 mark-runtime-ready。跨仓库不承诺原子 Git 提交。
