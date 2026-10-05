# ai-rulers-init 优化实施方案与计划

状态：审核通过，实施及本期工程和受控行为验证完成。日期：2026-10-06。

本方案记录 `skills/ai-rulers-init` 的兼容优化：减少无关阻塞和重复确认，按项目消费分支与 CI 约定，区分规则激活和规则准备状态，并完成一次批准后的单域维护编排。实施分为三个阶段，各自验证，最终合并验收。七项目标原则和数据接口细化已审核通过；实际验证结果另列，不以方案文本代替完成证据。

## 审核范围和执行边界

建议审核本文件后，一次授权本工程内列明的源码、模板、文档、回归测试和候选分发包修改，以及临时合成项目验证。默认按阶段连续执行，通过一阶段再进入下一阶段；不因进入下一阶段重复申请同范围授权。改变目标原则、扩大实际影响范围或需要不兼容协议迁移时，先提出具体修订供审核。

本次授权范围不包含真实业务仓库安装或升级、远端分支保护修改、生产操作、Git 提交推送、创建 PR/MR 或版本发布。用户之后要求这些操作时，按对应项目约定和明确授权执行。本仓库根 AGENTS.md 中的提交门禁保持适用。

建议重点审核三项细化选择：

| 选择 | 推荐设计 | 取舍 |
| --- | --- | --- |
| 准备状态的唯一审阅来源 | 在已有采纳范围的 `review` 中增加可选 `readiness` 引用与摘要，派生结果用于提示 | 不新增第二份人类审批账本；不提供准备声明的项目照常工作 |
| 单域维护的激活入口 | `rules-plan` 可显式选择应用后激活，将选择绑定在计划中；旧调用仍只采纳候选 | 保留旧 CLI 行为，避免 apply 执行时扩大批准范围 |
| 维护恢复和幂等记录 | State 增加可选的单条 `maintenance_execution`，仅保存当前或最近一次单域计划 | 避免 `last_operation` 被覆盖导致重放错误；不建设通用历史或恢复平台 |

旧依赖的保留或解除属于目标项目升级计划的具体审阅项。本方案批准不替任何真实目标项目作出该决定。

## 当前基线和问题依据

编制时现场基线：Git HEAD 为 `eb998d59120149842511153228622db9a30184fb`，当前分支 `main`，Skill 发布版本 `4.0.4`。工作区已有上一阶段的 AGENTS.md、CHANGELOG.md、CONTEXT.md 和 ADR 文档变化，实施前须重新核对并保留其归属；不能用本方案覆盖之后的人工修改。

术语遵循 [CONTEXT.md](../../CONTEXT.md)，激活与准备状态的语义已记录在 [ADR 0001](../adr/0001-separate-rule-activation-and-readiness.md)。关联会话为[评估 GitLab CI 三项测试 Job](codex://threads/01a10c73-81e1-7653-ac96-b610f3c42015)。其中单 main、feature 分支、人工观察 CI、分层检查等是该项目的批准决定，用作适配案例，不设为所有项目默认。

| 当前问题 | 已核对的实现依据 | 实施方向 |
| --- | --- | --- |
| 无关领域维修提示扩大成任务前置阻塞 | [入口模板](../../skills/ai-rulers-init/templates/runtime/AGENTS.md.tmpl)要求先处理任何 next_action；Context 已按所选领域派生 blocked | 统一任务阻塞与安装诊断的语义 |
| 普通 CI 和生产准备共用硬前置 | [registry](../../skills/ai-rulers-init/templates/domain-registry.json)、[State 校验](../../skills/ai-rulers-init/scripts/rulers_lib/state.py)、[领域激活](../../skills/ai-rulers-init/scripts/rulers_lib/domain_lifecycle.py)强加 delivery 到 security 的依赖 | 新安装移除框架默认前置；已装依赖经审阅迁移 |
| 只含 INDEX/CI 的 delivery 也能自动获得 Level 3 | 领域激活按注册等级置位；[Context](../../skills/ai-rulers-init/scripts/rulers_lib/validation.py)接受数字等级回退 | 明确审阅依据，停止按数字自动授予准备状态 |
| strict-cn 对明确提交指令追加确认，且固定截断 diff | [提交模板](../../skills/ai-rulers-init/templates/runtime/core/GIT_COMMIT_CONVENTION.md) | 精简步骤，遵循当前授权及项目另设门禁 |
| 维护重新覆盖安装依赖、所有候选错误统一阻断 | [rule_maintenance.py](../../skills/ai-rulers-init/scripts/rulers_lib/rule_maintenance.py) | 使用有效项目依赖；区分本次维护校验和全安装诊断 |
| 激活覆盖 last_operation，使直接串联旧命令失去重复调用依据 | rules-apply 的幂等标记和 activate 的诊断记录共用槽位 | 薄编排绑定原计划、阶段结果及实际输出 |

上一轮独立审核运行了 19 项已有定向回归，并完成三个隔离复现：健康领域仍收到前置维修指令、裁剪 CI 领域仍自动准备、无引用日志变化要求初始化重计划。该结果支持上述具体判断，不代表全量回归或真实模型效果验证。本轮只编制方案，没有重新执行这些测试。

## 已确认原则和保留机制

1. 分支、PR/MR、worktree、CI 和人机分工按项目发现及确认，保留已有权威正文。
2. 全局状态和画像健康时，只阻塞任务所需的无效领域及其实际加载依赖。
3. 普通 Git/CI 与生产部署、发布、回滚按实际任务风险使用门禁。
4. 同一不可变差异及明确适用范围的一次批准，可以覆盖应用、校验和激活编排。
5. Level 3 readiness 表示生产相关规则和准备流程已审阅，不表示具体版本或环境可发布。
6. 应用失败回滚；应用成功、激活失败保留已批准内容为 draft，并支持在原批准范围内恢复。
7. strict-cn 不在已有明确授权且范围不变时追加提交草案确认；项目自身门禁、中文格式、CHANGELOG 和 staged-only 范围仍须遵守。

继续保留 State 单一机器权威、Profile 的 observed/approved 区分、审阅内容身份、路径和符号链接防护、受管文件漂移检查、事务锁与恢复、未知工作保护、项目定制及批准删除保留。脚本负责范围、哈希、依赖、状态和加载清单；模型负责发现证据、提出内容及解释取舍，用户负责真正的语义审阅和操作授权。

本期不拆 CI 新领域，不建设逐叶权限、通用风险分类器、评分或准备覆盖矩阵、强身份签名系统、发布版本与环境证据平台、多套 preset；不重写 State/schema 或全仓快照引擎。保留领域级可信度：同域已采纳叶子漂移，仍使该域需修复。

## 目标行为和实现合同

### 项目工作流和验证范围

发现优先读取已有入口、工作流文档、Git 与 CI 配置以及批准决定。只补充会影响本次任务的缺口；有文档时保存指针，Profile 保存事实与批准决定，不复制第二份工作流。没有证据的分支保护、MR 权限和人机分工保持未决；仅在任务实际需要该决定时确认，不要求所有项目完成统一问卷。

在既有 WORKFLOW 条件参考中消费项目权威指针，优先不新增一份通用 Git 流程正文。项目可采用单主线、Git Flow、其他分支策略；分支命名、同任务复用、worktree、本地 hook、PR/MR 创建、CI 观察和合并责任均依据实际约定。

开发或修复运行受影响的必要检查。commit/push 只执行项目规定的提交门禁，不因 Profile 中存在命令就重跑全套，也不绕过实际 hook 或平台必需检查。CI 修改覆盖被改变的触发、依赖、失败处理和产物路径；取消或重试行为发生变化时才要求对应路径验证。无法执行时报告具体覆盖缺口。

strict-cn 保留中文提交格式与 CHANGELOG 政策，合并重复步骤，去掉越级优先声明和固定差异截断。文件归属不明、范围改变、混合修改无法安全拆分或实际项目门禁要求确认时，展示具体差异再询问。提交、推送、PR/MR、合并和清理按各自授权处理。

模块详细协议条件加载，但必须保留绝对会话根、模块与工作区选择器的区别、已采纳快照消费、来源手动同步及双入口歧义处理。运行态路由只能指向实际安装的文件或 Context 输出；不能指向仅存在于 Skill 源码的 references/module-workflows.md。

### 局部阻塞和完整诊断

任务是否可执行依据已校验的 `blocked`、所选领域及实际依赖，不以任意 next_action 或 issue_count 替代。无关领域维修作为提示；完整 runtime 仍输出所有问题。

| 情况 | 本任务结果 | 完整安装诊断 |
| --- | --- | --- |
| 无关领域漂移，所选领域有效 | 继续任务；不加载坏域 | 保留错误及维修建议 |
| 所选域或实际加载依赖失效 | 阻塞该任务 | 报告具体失效范围 |
| Core、入口、Profile、协议、路径安全或未完成事务异常 | 全局阻塞 | 给出恢复依据 |
| 仅缺少生产规则准备声明或其引用失效 | 普通健康任务继续 | 给出准备状态缺项 |
| 问题无法安全确定作用域 | 保守阻塞，解释原因 | 不按模型猜测放行 |

复用 inspect_project 的 global_blocked、profile_valid、invalid_domains，以及受管路径归属和依赖关系。`requires_active` 与必须加载的 `must_load_with` 构成实际依赖；普通 INDEX 导航链接不能全部转成激活前置。候选链接、metadata、所有权、路径、哈希和 INDEX 可达性仍须校验。

P1 先修正入口与现有 Context 的合同；P3 使维护和恢复采用相同范围判据。完整 runtime 非零可以表明安装其他领域有问题，不应自动推翻本次健康范围的维护成功。

### 有效项目依赖和旧安装迁移

registry 提供新安装默认，State 保存已采纳项目契约。所有激活排序、反向失效、reconcile、repair、规则维护和 Context 使用同一份经校验的有效依赖；不能维护时重新用 registry 覆盖已安装依赖。

新安装取消框架默认 delivery 到 security 的加载前置。旧安装按下表处理：

| 旧数据或项目决定 | 升级行为 |
| --- | --- |
| 有明确保留依赖的项目决定 | 保留，按真实加载依赖处理 |
| 旧值等于旧默认，但无来源证据 | 默认保留，标注来源无法判定 |
| 用户拟解除旧依赖 | 升级计划展示 before/after、范围、理由及影响；批准后解除 |
| 其他项目依赖、定制叶子、批准删除 | 保留，不因本次默认变化覆盖 |
| 非法依赖、未知领域或无法安全分类的契约 | 拒绝自动迁移，报告具体修正项 |

依赖变更及相关契约摘要进入计划；计划后输入变化要求重新计划。保留/解除只作为本次升级决定记录，不追溯全部历史、不新建依赖溯源平台。must_load_with 中的真实安全依赖仍生效，不能靠删除 registry 默认绕过。

### 最小规则准备合同

普通领域审阅与文件完整性满足条件后可进入 Level 2，delivery 也适用。准备状态只作提示，不设普通任务的 blocked，不生成必须先完成的全局 next_action，不授予生产动作权限。

建议在采纳范围已有 `review` 中增加可选 `readiness`：包含明确批准的安全、质量、回滚三项覆盖引用及脚本生成的绑定摘要。引用使用已采纳规则的路径和实际 SHA-256；允许自定义路径、同一文件覆盖多项，不从标题或文件名猜用途。完整人类批准仍只有外层 review 的 reviewer、时间和 evidence。

不需要生产规则准备的项目可以不提供该对象。首版不引入 N/A 分类、评分或通用映射平台。结果区分“未评估”“依据不满足”“依据有效”；对外兼容的 ready 布尔值只在依据有效时为 true。

共享纯判定检查采纳范围、实际加载依赖、相关审阅、引用合法性、文件身份和批准绑定。机器只能证明声明的覆盖已经审阅且未漂移；语义充分性由用户审阅，真实版本 CI、环境和回滚执行结果另行核对。

准备声明随初始化集中计划或规则维护计划展示并绑定；普通 activate-domain 没有明确覆盖输入时只形成 Level 2。P2 建立判定及初始化接入，P3 接入同批准维护。声明更新使用既有计划审阅路径，不另建审批命令。

`readiness_level` 保留为模板分类；旧 `level3_ready` 不独立授信。旧审阅缺少覆盖绑定时报告未评估，不补造批准。activate 返回、Context、load 和完整诊断共享判定。仅作为准备依据的外部引用漂移只撤销准备状态；同域采纳叶子漂移仍使整个域失效。

模块不传播来源 State 或准备标记。首版复用主工程已有模块采纳记录与快照身份；无消费者自身准备依据时不声明准备，不扩展模块导出协议。

### 单域同批准维护编排

rules-plan 已增加 `--activate-on-apply` 和可选 `--readiness-source PATH`。无激活选项的旧调用继续只采纳候选；rules-apply 仅消费计划，不能在执行时追加激活范围。实际计划协议为 plan_version 2；旧未应用计划缺少新的绑定时须重新计划。

`--readiness-source` 必须与计划中的显式激活选择一起使用，否则拒绝。来源文件只声明覆盖引用，不携带审阅身份或自行授予 ready。正文和有效依赖未变、目标已经具有有效 Level 2 时，仅更新准备声明不降级普通规则；跳过正文采纳及依赖降级，按已批准计划更新准备绑定。准备更新失败保留普通规则的原有可信度，不制造新的正文审阅事实。

不可变计划至少绑定项目根、规则目录、目标单域、候选完整 before/after、实际 diff、当前 State 身份、有效依赖、脚本派生受影响域、明确激活范围，以及可选准备声明。候选覆盖来源文件也纳入输入身份。批准范围不让模型自行补写，执行时重新推导一致性。

首期激活范围只能是目标单域。依赖方按真实影响降为 draft，恢复它们需要其适用性进入后续审阅范围。没有正文变化但目标仍 draft 时，明确批准激活的计划仍可执行激活，不能提前返回 noop。

建议增加可选的 `maintenance_execution` 单条记录，保存当前或最近计划摘要、目标与激活范围、原批准、阶段及输出摘要；不保留历史列表。last_operation 继续用于诊断，不承担可靠恢复依据。

新编排不得静默覆盖尚待激活的记录。优先恢复完成原计划；确需替换时，新计划必须展示原计划标识、已应用内容、仍为 draft 的范围和替换恢复依据的影响，得到这项具体差异批准后再执行。该限制只约束会替换记录的维护写入，不使普通健康任务全局阻塞，也不自动回滚旧计划已批准的内容。

| 步骤 | 校验和动作 | 失败结果 |
| --- | --- | --- |
| 预检查 | 核对计划、原输入、候选、有效依赖和批准范围 | 拒绝，原状不变 |
| 第一事务 | 采纳正文，校验本次范围，更新受管清单和删除决定，降级受影响域，同时保存激活待完成记录 | 恢复旧内容、状态和权限 |
| 第二事务 | 核对原批准与已应用结果，激活目标域，并在同一事务保存完成记录 | 第二段回滚；第一段已批准内容保留 draft |
| 再次调用 | 完成且结果一致则 noop；待激活且结果一致只执行第二段 | 任一绑定输入变化则要求重新计划 |

复用现有 mutation、锁、journal、snapshot 和路径检查；不能外套事务导致嵌套，也不能放开同一事务重复写 State 的限制。抽出最小状态转换供第二事务使用，避免复制全部初始化平台。

恢复记录的摘要必须覆盖涉及域状态、受管输出、画像和依赖等执行前提，不能只看 last_operation 或自行重算当前内容后赋予旧批准。脚本生成规范化摘要时排除其自身摘要字段，避免自引用。首期对其他 State 操作采用保守策略：不能证明是原计划自己的输出，就拒绝旧批准并重新计划，不自动合并并发变更。

事务中断按已有恢复检查处理；只恢复有同一计划与事务证据的写入，不能自动处理无关事务。成功重复不重写文件、review 时间或制造新批准。

## 分阶段工作计划

下面为依赖驱动的顺序，不是完成日期承诺。P2 的有效依赖合同必须先于 P3 编排。P1 完成不代表已解除 CI-only 的机器激活限制；该行为在 P2 验收。只有三个阶段和最终收尾全部达到相应标准，才能声明本方案完成。

| 编号 | 任务 | 前置 | 交付和退出标准 |
| --- | --- | --- | --- |
| T00 | 冻结工作区、版本、测试与包基线，确定任务分支及修改归属 | 方案批准 | 记录现有改动；复用或隔离任务工作区，不清理其他工作 |
| T01 | 修正局部阻塞语义及所有常驻相关正文 | T00 | Context 与入口一致；健康域任务继续，核心异常仍阻塞 |
| T02 | 工作流发现和项目指针，精简提交及测试约束 | T00 | 不增加统一问卷；保留实际 hook/平台门禁和本仓库提交约定 |
| T03 | 模块协议条件导航及打包路径验证 | T01 | 单仓库少加载；模块根绑定、选择和入口歧义信息完整 |
| T04 | P1 定向回归和文档检查 | T01–T03 | 记录已验证、未验证和实际差异；无新增状态模型 |
| T05 | 统一有效项目依赖及所有反向失效调用方 | T04 | 维护/reconcile/repair/初始化不再覆盖或遗漏项目依赖 |
| T06 | 实现可审阅升级迁移，保留来源不明依赖 | T05 | 升级差异明确，批准删除、定制和旧 CLI 保留 |
| T07 | 最小 readiness 记录与共享判定，解除默认加载耦合 | T05 | CI-only 可激活；数字标志不能授信；外部准备失效不阻健康域 |
| T08 | P2 初始化/模块边界和升级回归 | T06–T07 | 新旧目标、裁剪规则、自定义路径与采纳范围验证通过 |
| T09 | 扩展单域规则计划及批准绑定 | T08 | 选项、范围、依赖、候选和准备声明进入同一摘要 |
| T10 | 薄编排、单条执行记录、两段事务及重复调用 | T09 | 正确处理零差异激活、阶段失败、中断恢复和 noop |
| T11 | 维护/恢复范围校验和旧调用方接入 | T09–T10 | 无关坏域不回滚本次健康维护；实际依赖和全局风险仍阻塞 |
| T12 | P3 定向回归与编排独立审核 | T10–T11 | 原批准不能扩大；恢复、失败和旧 CLI 无漏项 |
| T13 | 文档、CHANGELOG、候选包、解压包与全量回归 | T12 | 源码/包行为和字节一致，预算及可复现构建通过 |
| T14 | 受控 Agent 行为检查和最终交付 | T13 | 给出执行轨迹与覆盖边界；未执行行为验证明确保留为缺口 |

实施 Agent 负责代码、临时夹具和结果记录；独立审核 Agent 负责权限/批准边界、恢复/幂等和契约一致性。可以并行处理独立模板及测试，registry/State/计划/事务等共享契约先统一再集成，避免多个 Agent 同时覆盖同一文件。用户审核目标和实际迁移差异，不承担内部字段计算。

## 目标文件与调用方

以下路径相对仓库根。核心文件列为预计修改；边界核查文件只有发现必要变化才修改，防止顺带重写。

| 层级 | 核心预计修改 | 边界核查 |
| --- | --- | --- |
| Skill 路由 | SKILL.md；references/discovery.md、generation.md、maintenance.md、activation.md、lifecycle.md | initialization.md、incremental.md、module-workflows.md、root-entry-merge.md |
| runtime 入口和规则 | AGENTS.md.tmpl；core/HARD_CONSTRAINTS.md、WORKFLOW.md、GIT_COMMIT_CONVENTION.md；delivery/CI.md、INDEX.md、RELEASE.md；Web develop/TESTING.md | core/CHANGELOG_MAINTENANCE.md、INDEX.md.tmpl、部署/回滚及其他 TESTING 叶子 |
| 依赖与准备状态 | templates/domain-registry.json；scripts/rulers_lib/domains.py、state.py、validation.py、domain_lifecycle.py、plans.py、reconcile.py、apply.py、rule_maintenance.py | migration.py、module_loading.py、module_sync.py、module_exports.py、initialization_projection.py |
| 新增最小共享逻辑 | 建议 scripts/rulers_lib/readiness.py，仅做引用/审阅绑定和有效性判定 | 不引入第三方运行依赖或通用规则推理器 |
| 编排入口 | scripts/rulers_init.py、rule_maintenance.py、domain_lifecycle.py、validation.py、rule_loading.py | mutations.py、transactions.py、initialization_execution.py、initialization_materialization.py；优先复用，不改变安全底线 |
| 验证与交付 | 相关 tests、evals/evals.json、CHANGELOG.md、skills/ai-rulers-init.skill | README/CONTRIBUTING/CONTEXT/ADR，仅同步必要的用户行为与术语变化 |

前三行的 Skill 路径均位于 `skills/ai-rulers-init/`；runtime 行位于 `templates/runtime/`。新增测试按行为归属并入现有套件或一个聚焦套件，不写仅复述实现的测试。

## 兼容和升级策略

1. 保留 Skill 名称、现有目录和 delivery 域；新安装仍默认 project-native，已有 strict-cn 保留。
2. 保留现有命令及不带新选项的含义。旧 rules-apply 不突然自动激活；旧 activate-domain 不再凭等级推断准备。
3. State schema 3 为兼容目标，新增字段均可选；计划与 Context 有新增合同需验证旧输入及输出消费者。不能以“数字未改”宣称协议兼容。若发现必须作不兼容协议修改，提交明确兼容修订后再实施。
4. 旧未应用计划遇到实现或依赖契约变化应拒绝并重新计划；不承诺历史计划跨任意版本继续执行。升级前存在未完成事务时先按旧证据恢复或诊断，不能用新逻辑重放未知写入。
5. 保留 required_files、removed_files、自定义目录、project-owned 内容和工作区调整。升级模板不能重新生成已批准删除的叶子。
6. 升级不自动重新抓取模块来源，不把源工程审阅和准备状态复制成主工程批准。
7. 完整框架和 State 变化经同一目标计划与事务落地；不混用新 State 与旧脚本。回退在隔离目标验证，并依据原状态及受管写集生成明确恢复差异；后续人工修改不能被旧快照覆盖。
8. 本次交付候选源码、包与 Unreleased 记录，不预设新版本号或发布。发布版本若另获授权，只修改 version.py 的唯一来源并遵守现有发布流程。

## 验收矩阵

自动化用合成项目和公开 CLI 验证，不操作真实业务远端。关键结果在源码和解压候选包各执行一次，避免源码通过但用户包失败。

| 编号 | 场景 | 预期结果 | 主要现有套件 |
| --- | --- | --- | --- |
| A01 | 无关域漂移，context/load 请求健康域 | blocked=false；不要求先维修；全量 runtime 仍有错误 | test_ai_rulers_unified_context、test_skill_runtime_context |
| A02 | 请求坏域、真实依赖异常、Core/Profile/入口/事务异常 | 正确阻塞，无效规则不加载 | unified_context、unified_transactions、review_regressions |
| A03 | 单项目与模块工作区加载 | 无模块不加载详细协议；模块根/选择器/双入口提示完整，无断链 | module_workflows、auto_initialization、v2_structure |
| A04 | 无 security、delivery 只有 INDEX/CI | 新默认能形成 Level 2 并加载；无准备声明不 ready | v2_integration、scaffold_lifecycle |
| A05 | 旧 ready=true 或 readiness_level=3，无绑定覆盖 | 不授予准备状态；普通健康任务不被该缺项阻塞 | unified_context、unified_upgrade_repair |
| A06 | 三项明确覆盖，自定义路径、同文件多用途 | 依据审阅和真实哈希派生；不依赖标题或固定名称 | readiness 聚焦回归、scaffold_lifecycle |
| A07 | 外部准备引用漂移；同域叶子漂移 | 前者仅撤销准备；后者使本域无效 | unified_context、readiness 回归 |
| A08 | 旧依赖来源不明、明确保留、明确解除 | 默认保留；解除进入真实差异且获批准后才执行 | unified_plans、unified_upgrade_repair |
| A09 | 自定义依赖经维护/reconcile/repair | 契约不被默认覆盖；实际依赖方正确降级 | unified_plans、scaffold_lifecycle、review_regressions |
| A10 | 无关坏域与本次健康维护/恢复组合 | 本次成功；全量错误保留；全局及实际依赖错误仍拒绝 | scoped 维护回归、unified_context |
| A11 | 同一批准应用并激活、成功重试、零差异 draft 激活、仅更新准备声明 | 目标域正确激活；完成重试 noop；准备更新保留原 Level 2；无激活选项的准备输入被拒绝 | scaffold_lifecycle、维护编排回归 |
| A12 | 计划后候选/State/依赖/声明/已装输出变化 | 原批准被拒绝，不自动采纳新内容 | review_regressions、unified_plans |
| A13 | 第一段失败、第二段失败、两段间修改和中断、待激活记录被另一编排占用 | 分别回滚旧内容/保留 draft；原范围恢复；并发变化拒绝；记录替换必须有明确差异批准 | unified_transactions、维护编排回归 |
| A14 | 反向依赖被降 draft、普通旧 CLI | 不自动恢复范围外领域；无新选项不改变旧调用 | scaffold_lifecycle、auto_initialization |
| A15 | 裁剪/删除/定制/目录/模块快照升级 | 保留项目决定；来源 ready 不传播；重复计划零差异 | unified_upgrade_repair、module_workflows、auto_initialization |
| A16 | 包一致性、可复现构建、预算、最终全量回归 | 源码和包一致；常驻预算不过限，增长检查通过 | v2_release、version_contracts、repository_boundaries、全套 |

表中套件缩写以 `tests.test_` 为前缀。新增回归必须验证行为、范围和失败路径，不能仅检查出现了某段措辞。

受控 Agent 检查至少覆盖四类场景：健康任务遇到无关漂移、CI 小改选择验证、明确范围的提交授权、同批准维护与失败恢复。记录实际加载、无必要确认、无关维修、授权越界、相关验证和漏步骤。优先复用历史轨迹和隔离场景；若比较旧/新行为，使用同输入、同平台及相同可见上下文，并将验收期望与执行 Agent 隔离。

行为检查只做有限一轮，不开展生产团队 A/B 或统计收益证明。没有可靠 Token 数据时记为未知，不用输出字符或文件字节替代成本。模型/平台能力不支持或场景未执行时列明缺口，保持候选审阅状态；静态和脚本通过不能宣称模型效果已改善或方案已适合推广。

### 执行命令和结果边界

以下为实施后从仓库根运行的现有检查入口，本轮不执行。各阶段先跑相关套件；源码定稿重建分发包后，再完成全量回归。

```bash
PYTHONDONTWRITEBYTECODE=1 python3 skills/ai-rulers-init/scripts/validate_rulers.py --mode template
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_skill_runtime_context tests.test_ai_rulers_unified_context tests.test_review_regressions
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_ai_rulers_unified_plans tests.test_ai_rulers_unified_upgrade_repair tests.test_ai_rulers_v2_integration tests.test_scaffold_lifecycle
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_ai_rulers_unified_transactions tests.test_module_workflows tests.test_auto_initialization
PYTHONDONTWRITEBYTECODE=1 python3 -m scripts.package_skill --skill-root skills/ai-rulers-init --output /private/tmp/ai-rulers-init-candidate.skill
PYTHONDONTWRITEBYTECODE=1 python3 -m scripts.report_context_budget --check --format json --domain backend
```

候选包解压到新临时目录后，显式调用其中 CLI 执行关键验收。现有 `RULERS_TEST_SKILL_ROOT` 可用于 module/auto-initialization 套件；不能假定设置它就使所有 lifecycle 测试都切换到解压包。

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m scripts.package_skill --skill-root skills/ai-rulers-init
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

模板、源码/包、公开 CLI 行为和模型轨迹分别报告。每项结果保留命令、输入范围、退出状态及必要失败证据；同提交重试恢复不能自动认定根因或代码修复。

## 风险和防止范围扩大

| 风险 | 本期处理 |
| --- | --- |
| 准备记录变成填表和标签考核 | 完全可选；复用 review；机器只核验绑定与有效性，不评分 |
| 依赖移除误伤项目决定 | 来源不明保留；明确 before/after 及目标项目审阅 |
| 任务局部放行掩盖全局安全错误 | 统一全局/作用域分类；未知问题保守阻塞；完整诊断保留 |
| 编排重试重复写入或扩大批准 | 独立单条执行绑定；阶段结果原子落地；实际输出不匹配拒绝 |
| 多 Agent 并行覆盖共享契约 | 先完成合同与文件归属；独立任务并行，共享核心顺序集成 |
| 新旧协议或消费者混用 | 验证缺省字段、历史 fixture 和解压包；明确重新计划及整体升级边界 |
| 模板减少但 Agent 误停/漏载增加 | 用代表性执行轨迹检查；预算减少不替代质量判断 |
| 本期再次扩成治理平台 | 只新增必要的小共享判定和单条执行记录；其他范围单独提案 |

全仓快照的无关变更问题已复现，但尚无规模和频率基线。本期保留保护，收集后续案例再评估显式证据读集，不顺带实现性能框架。

## 最终交付和完成标准

最终交付包括源码与模板、公开 CLI 回归、候选及已跟踪分发包一致性、必要用户文档、CHANGELOG、阶段验证记录、独立审核结论，以及真实模型验证的结果或明确缺口。实现变化记入正确的 Changed/Fixed/Added 类别，不能将本方案文档记录冒充功能完成。

工程完成要求 A01–A16 的适用脚本行为、包一致性、预算和全量回归通过，失败与未执行项有明确处置。真实模型验证尚未完成时，只能交付“工程验证通过的候选”，不能宣称完整使用效果或推广验收完成。

交付时展示最终文件清单和保留的既有改动，核对未进入本次授权的真实业务仓库、远端或生产操作。提交、推送和正式发布按后续指令分别处理。

本方案整体范围已审核通过。用户可根据实际验证记录审核交付；尚未通过的检查保持未完成，不以代码已修改或局部测试通过替代最终验收。

本期逐项证据见[实施验证记录](2026-10-06-ai-rulers-init-validation.md)。覆盖本方案的工程和有限行为验证，不代表真实业务仓库、远端 CI 或生产推广验收。
