# ai-rulers-init 实施验证记录

日期：2026-10-06。对应[已批准实施方案](2026-10-06-ai-rulers-init-optimization-plan.md)。

本期三个实施阶段已完成，源码全量回归、最终解压包公开 CLI、上下文预算和四类有限 Agent 行为检查通过。验证范围为本工程和一次性合成目标，没有在真实业务仓库安装，没有改动远端分支保护或生产环境。该结果不证明长期收益、真实项目全面适用性或生产推广完成。

本记录的实施测试基于发布准备前的 4.0.4 代码候选。下文 `/private/tmp` 链接为本机保留的原始证据，在 GitHub 上无法直接访问；它们不是发布下载地址。4.1.0 的版本、包身份和发布检查另见文末，不将既有模型观察改写成新版本重新执行的结果。

## 交付内容

- 项目工作流权威指针、按影响选择验证、strict-cn 的范围与授权减法，以及模块协议的条件输出。
- 已采纳项目依赖与真实 must_load_with 闭包；新 CI-only 目标 Level 2 加载；来源不明的旧依赖保留及可审阅升级候选。
- review 内可选准备声明，内容身份与加载闭包绑定，结果只作提示；只准备更新保留正文审阅，并记录本次批准范围引用。
- 单域规则计划的 --activate-on-apply / --readiness-source，批准前态、范围与来源绑定，两段事务、确定性输出、可恢复失败和零写入重跑。
- 回归、评测场景、用户操作说明、CHANGELOG 与更新后的 [Skill 包](../../skills/ai-rulers-init.skill)。

State schema 保持 3；规则维护计划协议为 2。旧命令不带新选项仍只采纳候选，旧未应用计划缺少新绑定时重新计划。没有修改发布版本唯一来源或发布新版本。

## 实际检查结果

| 检查 | 实际结果 | 证据 |
| --- | --- | --- |
| 源码全量 unittest discover | 239 项通过，334.521 秒，退出 0 | [最终源码日志](/private/tmp/ai-rulers-implementation-7ykqsreq/full-tests-final.log) |
| 最终解压包 module/auto/init 套件 | 37 项通过，175.352 秒，退出 0 | [最终包日志](/private/tmp/ai-rulers-implementation-7ykqsreq/package-tests-final.log) |
| 显式切换到最终包的 scaffold CLI | 6 项通过，退出 0 | [包 CLI 日志](/private/tmp/ai-rulers-implementation-7ykqsreq/package-scaffold-final.log) |
| 模板、包可复现及源码字节一致性 | 模板校验和全量中的发布契约通过；112 个成员与源码逐字节一致 | tests/test_ai_rulers_v2_release.py；最终包核对 |
| backend 合成任务加载预算 | Context 663 bytes；固定加载链 6746 / 16000 bytes；1 至 100 个附加文件、20 次零差异 reconcile 增长均为 0 | scripts/report_context_budget.py 的隔离目标实际报告 |
| 四类最终包 Agent 行为检查 | 四类场景的实际产物与范围断言通过 | [分项核验 JSON](/private/tmp/ai-rulers-implementation-7ykqsreq/behavior-evals/final-grading.json) |
| 工作区及源范围 | 暂存区未改变；根 AGENTS/CONTEXT 先前内容保留；无根 State/Profile 或本仓库自安装 | 最终工作区与基线字节核对 |

最终包 SHA-256：`d8c6154119100b0a215f78a5e8bcb8f2a1e84aabc12b1f33ae45d46377bdecd4`。

曾执行的第一次全量共 237 项、7 项失败，均进入初始化重放路径。临时预演中的内部维护执行记录包含预演目录与计划身份，进入输出 State 后造成同输入再次预演不一致。修复为不发布模拟器内部记录，并保留目标原维护记录；原失败相关 10 项定向通过，新增两项重复预演和原记录保留回归通过，随后上述最终全量通过。保留[首次失败日志](/private/tmp/ai-rulers-implementation-7ykqsreq/full-tests.log)，不将单纯重试恢复当作根因证据。

## 方案验收逐项核对

下表的测试文件属于最终 239 项通过的套件；涉及模块与初始化的行为同时用最终解压包验证。测试证明脚本行为，Agent 场景用于观察真实执行路径，两者分别使用。

| 项目 | 主要当前证据 | 判定 |
| --- | --- | --- |
| A01 无关坏域与健康任务 | dependency_loading 的健康加载/独立域检查；backend Agent 实际完成业务修复，未修无关漂移 | 通过 |
| A02 坏域、实际依赖及全局异常 | unified_context / transactions；dependency_loading 的 draft 依赖阻塞 | 通过 |
| A03 单项目与模块协议 | optimization_module_protocol 3 项；最终包 module_workflows | 通过 |
| A04 CI-only 无 security | v2_integration 的新默认激活；CI Agent 实际修改 Job | 通过 |
| A05 旧数字标记不能授信 | optimization_readiness 的 legacy numeric flags；普通无声明不警告 | 通过 |
| A06 自定义路径及同文件多主题 | optimization_readiness / initialization_readiness 的自定义目录和覆盖编译 | 通过 |
| A07 准备引用与同域叶子漂移 | readiness 的外部引用仅提示失效；依赖加载闭包绑定/撤销 | 通过 |
| A08 旧依赖保留或明确解除 | optimization_dependencies 的默认保留、显式升级、候选变化拒绝和 repeat noop | 通过 |
| A09 有效项目依赖贯穿维护路径 | dependencies 的 reconcile 反向失效；维护域依赖降级、plans/upgrade/repair 回归 | 通过 |
| A10 局部维护和完整诊断 | maintenance 的 unrelated bad domain / actual bad dependency；全安装警告与 scope 检查 | 通过 |
| A11 单批准、零差异与准备更新 | maintenance 的 target-only、zero difference、ready-only 与成功重试；恢复 Agent 的 mtime 核对 | 通过 |
| A12 绑定输入变化拒绝 | maintenance 的来源/候选/State/Skill 变化与篡改、自报摘要拒绝 | 通过 |
| A13 两阶段失败、中断及替换 | maintenance 的真实 os._exit、journal 伪造前态拒绝、两段回滚和明确 supersedes | 通过 |
| A14 不扩大依赖方批准、旧 CLI | maintenance 的旧 content-only 和健康 draft 依赖采纳，target-only 激活 | 通过 |
| A15 定制、删除及模块边界 | scaffold / upgrade / 最终包 module、auto、initialization_readiness | 通过 |
| A16 包、预算及全量 | 上述 239 / 37 / 6 项、112 成员字节一致和预算报告 | 通过 |

T00 的分支与原改动归属、T01–T04 入口模板、T05–T08 有效依赖及准备合同、T09–T12 维护编排、T13 源码与包、T14 有限行为检查均有相应当前产物和上述验证。独立复核检出的实际 metadata 依赖遗漏、恢复前态及批准输出绑定缺口已修复，并加入行为回归，未以审计意见代替执行测试。

## 受控 Agent 行为观察

执行者仅得到临时目标中的项目规则和自然任务；构造证明与核验期望在目标之外，核验读取实际产物和命令记录。最终包更新后重新构造并运行四类目标。合成审阅身份均明确为 test-only，不代表真实业务批准。

| 场景 | 实际结果 | 记录 |
| --- | --- | --- |
| 健康 backend 遇无关 security 漂移 | subtotal 由覆盖赋值修为累加，修前复现、修后 2 测试通过；原漂移未改变 | [业务任务](/private/tmp/ai-rulers-implementation-7ykqsreq/behavior-evals/targets/final-backend_drift/outputs/result.md) |
| CI-only 小改 | 只增加 test.timeout=5m，YAML 和前后完整语义比较通过；未虚报远端 CI | [CI 任务](/private/tmp/ai-rulers-implementation-7ykqsreq/behavior-evals/targets/final-ci_only/outputs/result.md) |
| 明确授权的 staged-only 提交推送 | 只提交 tests/test_fixture_data.py，未知未暂存内容 hash 保留；本地 bare upstream ahead/behind 0/0 | [范围任务](/private/tmp/ai-rulers-implementation-7ykqsreq/behavior-evals/targets/final-staged_git/outputs/result.md) |
| 原批准维护恢复 | 只完成剩余激活，backend Level 2、原审阅保留；重复原计划 noop，mtime 和 State 不变 | [恢复任务](/private/tmp/ai-rulers-implementation-7ykqsreq/behavior-evals/targets/final-maintenance_resume/outputs/result.md) |

[静态行为审核页](/private/tmp/ai-rulers-implementation-7ykqsreq/behavior-evals/review.html)汇集这些执行记录和分项核验。平台线程数量有限，同一执行者顺序承担不同类型场景；这是一轮受控正确性观察，不是多样本独立效应估计。旧版夹具已构造，但没有公平旧新版模型对照；Token 用量和成本未知，不以字符或字节替代，不声明因果优势、节省 Token 或长期效益。

行为任务中默认 python3 曾指向 Python 3.9；执行者使用已有的 Python 3.11/3.12 验证，没有安装运行时或改变项目配置。Skill 的 Python 3.11+ 兼容要求保持。真实远端 GitLab/GitHub CI、生产部署、业务数据库与真实目标升级均未执行，也不属于本次实施授权。

## 后续操作边界

本仓库未提交或推送这些实现，也未发布版本。行为场景中的提交和推送仅发生在新建临时工程与其本地 bare origin。真实项目采用时仍须审阅其事实、依赖迁移和准备声明；原明确项目门禁及操作授权保持适用。

## 4.1.0 发布准备

用户已授权提交、推送全部更改及发布新版本。发布版本唯一来源改为 4.1.0，既有待发布条目归入该版本；分发包重建，版本发布检查在提交前执行并记录。规则维护计划协议为 2，旧未应用规则计划须重新规划；已有未完成事务先按原版本和原证据恢复或诊断，不使用新逻辑重放未知写入。

4.1.0 发布准备检查：源码全量 239 项通过（331.552 秒）；CLI 与解压包版本均为 4.1.0，112 个发布成员与源码逐字节一致；上下文预算与增长检查通过。新包 SHA-256：`8efa8f2894caa335c6bbef3e006278a4a4e9309b12b3f12ad80412025ab3ba45`。四类模型观察仍对应前述实施候选，不宣称已在 4.1.0 重新执行。

本段记录提交前的发布准备状态。实际提交、标签和附件身份以 GitHub Release 及交付回复为准；此前实施候选的哈希和行为记录保留为历史证据。
