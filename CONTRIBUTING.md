# Contributing

**English** · [简体中文](CONTRIBUTING-zh.md) · [Back to README](README.md)

Rulers Constructor maintains the rules layer of an AI coding harness. Contributions should make project conventions easier to express, find, update, and verify.

An evidence-backed deletion, a narrower loading scope, or a test that reproduces a state error is a useful contribution. When adding a rule, explain the problem it addresses and why the framework should own it.

## Start with a concrete problem

Use [GitHub Issues](https://github.com/AndersJet/ai-rulers-constructor/issues) to describe the task, expected behavior, and actual result. For model behavior, include sanitized instructions, loaded context, and relevant output. For scripts, include reproduction commands, the environment, and the error.

| Contribution | Useful evidence |
| --- | --- |
| Rule content | A recurring failure and why existing instructions did not address it |
| Progressive loading | Content that was missed, misapplied, or loaded for an unrelated task |
| Lifecycle and recovery | Inputs that invalidate reviews, overwrite work, or prevent recovery |
| Project adaptation | A greenfield decision, brownfield fact, or module boundary that the workflow cannot express clearly |
| Documentation | The step where a reader gets stuck or where instructions differ from actual behavior |

For larger changes to rule authority, state structures, or public commands, discuss the proposal and compatibility impact in an Issue first. Focused fixes can go straight to a PR. Use synthetic reproductions and remove customer code, credentials, and internal addresses.

## Choose the right place to change

This repository develops and distributes `ai-rulers-init`. Its template sources and a target project's installed rules have different roles.

| Location | Responsibility |
| --- | --- |
| [SKILL.md](skills/ai-rulers-init/SKILL.md) | A short Skill entry point and task router |
| [references/](skills/ai-rulers-init/references/) | Task-specific discovery, generation, maintenance, and migration instructions |
| [templates/runtime/](skills/ai-rulers-init/templates/runtime/) | Current generated defaults; start here to change new installations |
| [scripts/rulers_lib/](skills/ai-rulers-init/scripts/rulers_lib/) | Planning, state, validation, transactions, loading, and module synchronization |
| [tests/](tests/) | Automated regressions, including real temporary Git submodules |
| [evals/](skills/ai-rulers-init/evals/) | Live model evaluation scenarios, separate from script tests |
| [scripts/](scripts/) | Package building, disposable project fixtures, and context-budget reports |

Terms are defined in [CONTEXT.md](CONTEXT.md); read relevant architectural decisions from `docs/adr/` when present. When working with an agent, read the root [AGENTS.md](AGENTS.md), then follow its task-specific routes.

Run installation checks in disposable target projects. Do not generate an installation Profile, State, or managed Skill entry in this development repository.

## Design boundaries

**Separate judgment from execution.** Models can find evidence, draft rules, and explain conflicts. Scripts should determine hashes, path checks, state transitions, transactions, and load lists. Structural validation does not replace content review.

**Give every rule an owner.** Entries route tasks; indexes provide navigation; leaves contain specific constraints; profiles hold facts; State records lifecycle and reviews. Copying rule bodies across files makes the next change harder.

**Make removal part of maintenance.** Consider editing, disabling, and deleting alongside creation. Upgrades preserve project customizations and deletion decisions. Conflicts should preserve human work and provide an actionable resolution path.

**Keep loading proportional to the task.** Explain why all tasks need any new resident content. Put task-specific detail behind conditional routes. Add detail in response to observed failures, with explicit loading conditions.

**Keep one lifecycle.** Approved greenfield decisions and observed brownfield facts share schema 3. Module workflows reuse State and transactions; a parent's accepted snapshot does not copy the child's entire lifecycle state.

Before changing rules, routing, ownership, or validation contracts, record the affected layers, files, and checks under the root [AGENTS.md](AGENTS.md) maintenance rules, including the reasoning for resolving authority conflicts.

## Default entry and underlying commands

The user-facing initialization entry is `init-plan` / `init-apply`. The existing `plan/apply`, rule-maintenance, and module commands remain underlying capabilities. When changing them, check that consolidated rehearsal and application still call them correctly.

Initialization regressions cover discovery, default inclusion and exclusions, uninitialized modules, consolidated parent/child review, repeated no-op runs, ownership conflicts, and rechecking every source after interruption. Run `tests.test_auto_initialization` against both source and the extracted distribution.

When initialization changes, check the README, Skill routes, initialization reference, and evaluation scenarios together. The greenfield/brownfield diagrams show internal single-project stages; captions must explain the default orchestration so readers do not infer a manual setup for every repository.

## Local development and checks

Use Python 3.11+ and Git on macOS, Linux, or WSL. Runtime scripts use the Python standard library. Run the following commands from this repository's root.

Validate templates first, then run tests relevant to the change:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 skills/ai-rulers-init/scripts/validate_rulers.py --mode template
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_scaffold_lifecycle
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_module_workflows tests.test_auto_initialization
```

Lifecycle changes should also cover `tests.test_ai_rulers_unified_plans`, `tests.test_ai_rulers_unified_transactions`, `tests.test_ai_rulers_unified_context`, and `tests.test_ai_rulers_unified_upgrade_repair`.

Prefer public CLI behavior tests in temporary projects. Check resulting files, effective rules, conflicts, rollback, and zero-diff runs. Module tests create real local Git repositories without business remotes. Fixture review identities are test data, not actual approvals.

After changing resident content or loading logic, measure a generated project's context:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m scripts.report_context_budget \
  --check --format json --domain backend
```

The report validates the disposable installation and executes 20 actual zero-diff reconciles. Byte counts check loading budgets. Model task performance requires a separate evaluation and cannot be inferred from file size.

## Check the distribution users receive

After changing Skill sources or templates, build a candidate package:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m scripts.package_skill \
  --skill-root skills/ai-rulers-init --output /tmp/ai-rulers-init-candidate.skill
```

For module changes, extract it into a new temporary directory, point `RULERS_TEST_SKILL_ROOT` at the extracted `ai-rulers-init`, and run the same public workflows:

```bash
RULERS_TEST_SKILL_ROOT=/absolute/path/to/extracted/ai-rulers-init \
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_module_workflows tests.test_auto_initialization
```

Once the source is final, rebuild the tracked distribution and run the full suite:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m scripts.package_skill --skill-root skills/ai-rulers-init
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

The suite includes `test_package_parity`, reproducible builds, and source/distribution consistency checks. Root README or CONTRIBUTING edits alone do not require rebuilding the Skill package; check links, commands, and the relevant documentation tests.

## Release identity

`RELEASE_VERSION` in `skills/ai-rulers-init/scripts/rulers_lib/version.py` is the single release-version source.
Query it with `python3 skills/ai-rulers-init/scripts/rulers_init.py --version`. The entry template renders this value through a placeholder; do not maintain a second literal version.
State records the installed release in `template.version`. Schema and other data protocol versions change only when their contracts change, independently of product releases.

For a release, update the single source, move pending CHANGELOG entries into the matching release, rebuild, and run the full checks.
Match the Git tag and Release title to the CLI output, then verify the uploaded package SHA-256. Do not replace existing official tags or assets.

## Make the PR easy to review

Lead with the concrete problem and resulting behavior, then provide verification results. Identify the affected rule layers, existing-project compatibility, and anything not tested. For model-effectiveness claims, include the task, model, actual loaded content, and observed result.

Commit conventions in this repository:

- Use an English type such as `feat`, `fix`, or `docs`.
- Write a Chinese verb-object subject, no longer than 50 characters.
- Write the body in Chinese, covering what changed, why, and the impact scope.
- Record features, fixes, and user-facing documentation changes under the appropriate category in [CHANGELOG.md](CHANGELOG.md). Feature and fix entries belong in the same commit as the implementation.

```text
docs: 重写规范框架介绍与贡献指南

- 改了什么：围绕规范生成、维护和验证重写双语文档
- 为什么：让使用者理解 Skill 的价值与适用边界
- 影响范围：README、CONTRIBUTING 与变更记录
```

When an agent commits on your behalf, follow the [commit gate](AGENTS.md#提交门禁): show the exact files and message draft, then obtain confirmation. A worthwhile improvement may make a rule shorter—or make it unnecessary.
