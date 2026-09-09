# 默认初始化：先发现，再集中审阅

用户说“初始化当前项目”或再次初始化时进入本流程。无需让用户列出模块名或描述 Git 拓扑。
脚本决定结构、差异、状态和写入范围；Agent 根据证据准备规则内容、判断语义和提出取舍。

## 1. 自动发现

将当前会话项目根绑定为绝对 ROOT；后续切换 shell 目录仍使用该根。运行：

```bash
python3 scripts/rulers_init.py init-plan --project-root ROOT
```

读取摘要的 mode、root_scope、status、plan_path、review_path 和 preparation_count。
摘要最多显示六个待处理项，其余从 plan_path 按需读取。脚本从当前根的 .gitmodules 和
Git gitlink 发现一层直接子模块；默认全选。子模块内部可以有多个领域，不再登记第二层。
已有受管入口中的规则目录会被识别；特殊目录可显式传 --rulers-dir。

- 没有子模块：按单项目准备。
- 未初始化：标记 unavailable，保留登记，不拉取代码，不阻塞其他可准备模块。
- 新模块或规则源不完整：列为 prepare-source，由 Agent 继续准备。
- 已有规则源：自动比较本地来源与已采纳内容，普通编码不会调用此检查。
- `--exclude-module NAME` 可重复；排除决定在批准后保存，后续初始化沿用；已从 Git 拓扑移除的历史排除名会自动清理。用
  `--include-all-modules` 重新纳入全部模块。排除只停止本次初始化管理，不删除已有快照。

首次运行仅写 .rulers-work 中的计划/审阅产物，准备期间不安装或改写主、子工程有效规则。

## 本地工作目录与 Git

默认初始化会把当前 ROOT 的 `/.rulers-work/` 忽略规则纳入同一份审阅计划；init-plan 不提前修改真实 .gitignore，批准后由 init-apply 使用事务写入。
已有 .gitignore 内容与换行格式保留；已有效配置时不重复追加。若后续否定规则可能恢复该目录，会在末尾追加明确规则，并展示实际差异。

.gitignore 应随正式规则提交，.rulers-work 中的本机候选、计划和执行记录不提交。其他开发者 clone 后不需要该目录即可加载正式规则；维护时会在自己的工作区重新生成。
仅配置本次会话根：主工程初始化不替子仓库修改忽略文件，子仓库独立初始化时配置自己的根目录。已跟踪文件不会被自动取消跟踪，初始化也不删除工作目录或修改 Git 索引。
.gitignore 为符号链接或非普通文件时，先处理路径问题，避免覆盖其他文件。

## 2. 准备候选，不逐项打断

根据 discovery/generation references 检查代码、现有规则和已批准设计。主体事实按
observed / approved 记录。主工程负责组合约束，子工程负责可移植规则源。

在主工程 `.rulers-work/` 中准备候选，再提供一个 JSON 描述文件。例如：

```json
{
  "projects": {
    "workspace": {"profile": ".rulers-work/candidates/workspace-profile.md"},
    "server": {
      "profile": ".rulers-work/candidates/server-profile.md",
      "domains": {"backend": ".rulers-work/candidates/server-backend"},
      "export_manifest": ".rulers-work/candidates/server-export.json"
    }
  }
}
```

项目键来自计划：主工程使用 root_scope（通常为 workspace；与模块重名时自动避让），
模块使用 Git 名称。所有候选路径相对主工程 ROOT，领域目录包含完整 INDEX 与叶子候选。
只填写需要变化的项目/字段；已有有效内容会复用。export_manifest 沿用 module-workflows
的显式导出契约。候选画像或领域文件不应直接写入已安装规则目录。

```bash
python3 scripts/rulers_init.py init-plan --project-root ROOT \
  --candidates .rulers-work/candidates.json
```

脚本在隔离副本中调用现有 plan/apply、规则维护、审阅/激活和同步机制，再输出真实写入差异。
隔离副本的候选审阅标记仅用于预演；实际身份在 init-apply 时记录，不得把预演当作用户批准。
预演复制本地参与工程的普通文件，忽略 Git 元数据、依赖缓存、.plans、.transactions 和
.rulers-work；声明的候选另行复制。大项目的初始化成本取决于本地文件规模，不属于日常加载成本。

新安装默认 project-native；已有策略保留，显式 --policy 可选择新安装策略。
已有安装的策略切换仍按 lifecycle 的明确升级流程处理，不绕过底层策略门禁。

## 3. 比较归属与处理冲突

脚本检查主工程与模块中同领域、同名叶子，以及正文完全相同的叶子，输出重复或潜在冲突。
这只是一轮结构比较；Agent 仍需检查不同文件名下的语义重叠，不能用脚本未报错证明没有冲突。

先提出去重和拆分方案，修改对应候选和 INDEX。需要保留不同作用域的同名规则时，在候选
描述的 resolutions 中说明理由：

```json
{
  "projects": {},
  "resolutions": [{
    "module": "server",
    "workspace_rule": "backend/ARCHITECTURE.md",
    "module_rule": "backend/ARCHITECTURE.md",
    "decision": "keep-scoped",
    "reason": "主工程约束服务间契约，模块规则约束内部实现"
  }]
}
```

批准后的决定绑定双方正文；后续任一方变化会重新要求检查。主工程组合调整可通过该模块
候选的 adjustments 字段提供，格式与 module-workflows 相同，路径仍相对主工程。

未解决的模块冲突保留旧来源和已采纳快照，不将该模块候选写入实际工程。若冲突涉及正在
改变的主工程规则，则整批保持 preparation，先完成主工程取舍。把问题集中列出供审阅，
不要逐条打断，也不要在不确定归属时静默覆盖。

## 4. 一次审阅后应用

status=preparation 时继续准备可用模块的候选，只有语义决定缺失才集中向用户提出问题。
status=noop 时报告零差异及仍未初始化的模块，直接结束。
status=review 时读取 review_path，汇总主、子工程的文件变更、状态、来源命令、相关证据、
待处理项和风险。用户可以批准其中已准备好的范围；必须明确哪些模块仍不会接入。

```bash
python3 scripts/rulers_init.py init-apply --plan ROOT/.rulers-work/init-PLAN.json \
  --reviewed-by REVIEWER --evidence EVIDENCE
```

身份与证据来自此次真实批准。该批准涵盖计划中列出的主、子工程文件写入和适用性审阅，
不涵盖任何 Git 网络操作或生产动作。计划绑定候选、原工程文件、Git 拓扑与实现；输入变动
要求重新计划。脚本逐工程使用事务，先写子来源，最后采纳主工程快照。

.rulers-work 中的 execution.json 保存本次执行内容，发生中断后重跑同一个 init-apply。
执行内容从批准计划确定性生成，仅替换本次审阅元数据及对应来源哈希；恢复时逐字节核对，不能通过改写执行记录重新定义规则。恢复须沿用首次 reviewer/evidence。
恢复前检查所有参与工程：未写来源必须仍匹配原输入，已写工程必须匹配预期结果；只恢复
属于本批次的事务。其他写入者、人工修改或未知事务需要单独处理。不要编辑执行记录。
跨仓库没有原子 Git 提交；重跑可识别已完成工程并继续剩余写入。

完成后验证所选模块与领域的 load/Context，并报告 changed_files 和 preparation。
存在待处理项时，只能声明已列明范围完成，不能把整个工作区说成全部接入。

## 重复初始化

重复运行同一默认入口即可发现新增模块、消失的登记、本地规则和相关证据变化。
既有候选无需重复提供；新的内容维护才传 --candidates。无变化不会重建有效规则。
缺失的登记保留快照并标记不可用，后续显式维护决定如何退休；不自动删文件或更新 gitlink。
