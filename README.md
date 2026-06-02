<div align="center">

<img src="logo.png" alt="Rulers Template" width="120">

# Rulers Template

**Universal AI Coding Standards Template — Progressive Guardrails for AI-Powered Development**

> Standards are not final drafts, but living systems symbiotic with the business. Calibrated in practice, evolved through feedback — no silver bullet, only iterative convergence toward truth.

<div align="center">

<a href="./README-zh.md">简体中文</a> |
<strong>English</strong>

</div>

[![Version](https://img.shields.io/badge/version-v1.0.0-blue)](https://github.com/AndersJet/ai-rulers-template/releases)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/AndersJet/ai-rulers-template/pulls)

[![Claude Code](https://img.shields.io/badge/AI-Claude%20Code-d97757)](https://claude.ai)
[![Cursor](https://img.shields.io/badge/AI-Cursor-6c4df5)](https://cursor.sh)
[![GitHub Copilot](https://img.shields.io/badge/AI-GitHub%20Copilot-0288d1)](https://github.com/features/copilot)

</div>

---

## 📑 Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Quick Start](#quick-start)
- [Activation Levels](#activation-levels)
- [Daily Usage](#daily-usage)
- [Validation](#validation)
- [Full Initialization Flow](#full-initialization-flow)
- [Template Directory Reference](#template-directory-reference)
- [Key Conventions](#key-conventions)
- [Project Structure](#project-structure)
- [Development Guide](#development-guide)
- [FAQ](#faq)
- [Star History](#star-history)

---

## 🎯 The Problem

AI coding assistants are powerful but unpredictable. Without clear boundaries, they can:

- Make changes that violate your project's security, data, or deployment policies
- Generate code in inconsistent styles across different sessions
- Apply generic patterns that don't match your tech stack
- Perform high-risk operations (database migrations, auth changes) without review

**Every project needs guardrails. Writing them from scratch is tedious and easy to get wrong.**

## 💡 The Solution

Rulers Template gives your AI assistants a **project-specific rulebook** — automatically generated from your actual codebase, not copied from a blog post.

- **Evidence-driven** — Rules are generated from your project's real files, configs, and commands, never fabricated
- **Progressive loading** — AI only loads the rules relevant to the current task, not the entire tree
- **Activation gates** — Four security levels (Level 0-3) prevent AI from doing dangerous work before rules are reviewed by a human
- **Domain routing** — Backend, database, frontend — each domain gets its own set of constraints
- **One-command init** — The `ai-rulers-init` skill scans your project and generates everything automatically

### How It Works

```text
1. Template placed in your project
2. AI scans your codebase (9 dimensions: tech stack, security, database, CI/CD, etc.)
3. AI generates PROJECT_PROFILE.md with confirmed facts
4. Domain-specific rules are generated for each area your project uses
5. Rules are activated level-by-level after human review
6. Every future AI session automatically follows these rules
```

---

## 🚀 Quick Start

Two ways to get started — pick the one that fits your workflow.

### Method 1: Copy + AI Auto-Init

Copy the template into your project, then send an explicit instruction to your AI assistant.

```bash
# 1. Clone this repo
git clone https://github.com/AndersJet/ai-rulers-template.git

# 2. Copy rulers/ into your target project
cp -r ai-rulers-template/documents/rulers /path/to/your-project/documents/
```

**3. Open your project in an AI coding assistant (Claude Code, Cursor, Copilot, etc.) and send:**

> Please load `documents/rulers/AGENTS.md` into context, then follow the initialization flow to complete the standards initialization for this project.

The AI will read AGENTS.md and automatically walk through: directory confirmation → placeholder replacement → AGENTS.md migration → 9-dimension project discovery → PROJECT_PROFILE.md generation → domain rule generation → validation → activation.

### Method 2: Install Skill + One-Command Init (Recommended)

>[!TIP]
> **Recommended for most users** — install once, use across all your projects.

The [ai-rulers-init](skills/ai-rulers-init/) skill automates the entire initialization process.

**Download & Install:**

```bash
# 1. Clone this repo
git clone https://github.com/AndersJet/ai-rulers-template.git

# 2. Install the skill
#    Claude Code
cp -r ai-rulers-template/skills/ai-rulers-init/ ~/.claude/skills/ai-rulers-init/

#    Other platforms (Cursor, Copilot, etc.)
#    Import ai-rulers-template/skills/ai-rulers-init.skill
```

**3. Open your target project, send to AI:**

> Initialize AI rulers for this project using the ai-rulers-init skill.

The skill handles every step automatically. Supports incremental re-runs — when you add a new platform later (e.g., mobile), re-run the skill and it auto-detects new domains without touching existing active rules. See [SKILL.md](skills/ai-rulers-init/SKILL.md) for the complete workflow.

| | Method 1 (Copy) | Method 2 (Skill) |
|---|---|---|
| **Setup** | Copy directory manually | Install skill once |
| **Init** | Send AI: "load AGENTS.md, follow init flow" | Send AI: "init rulers using skill" |
| **Incremental** | Manual re-copy + re-init | Re-run skill, auto-detects new domains |
| **Best for** | One-off use, trying it out | Multiple projects, team onboarding |

---

## 🔒 Activation Levels

Controls what AI is permitted to do at each stage:

| Level | Status | Permitted |
|-------|--------|-----------|
| **Level 0** | Template placed, no profile | Project discovery only |
| **Level 1** | Profile reviewed | Read-only analysis, low-risk docs, small local fixes |
| **Level 2** | Domain rules reviewed | Work within activated domains |
| **Level 3** | Release gates reviewed | Production-impacting work |

**High-risk minimum requirements:**

| Work Type | Minimum Level |
|-----------|---------------|
| Auth / security-sensitive changes | Level 2 |
| Database schema / migration / seed / backfill | Level 2 |
| External payment / messaging / notification integration | Level 2 or 3 |
| Release / deploy / CI/CD changes | Level 3 |

---

## 📋 Daily Usage

After initialization, AI loads rules in this order for every session:

```text
AGENTS.md → core/* → PROJECT_PROFILE.md → domain INDEX.md → matched leaf rules
```

Simply reference the relevant domain in your AI prompt:

- Backend development → AI loads `backend/INDEX.md` + leaf rules
- Database changes → AI loads `database/INDEX.md` + leaf rules
- Frontend development → AI loads `frontend/INDEX.md` + platform-specific rules

---

## ✅ Validation

```bash
python3 documents/rulers/scripts/validate_rulers.py
```

>[!NOTE]
> The ai-rulers-init skill runs validation automatically during initialization. Manual validation is useful when editing rules directly.

Validates:
- Markdown link validity (no external references)
- Every authoritative document has `metadata` (applies_to, trigger_keywords, must_load_with)
- `must_load_with` paths are resolvable and within template scope
- Each `INDEX.md` covers all sibling leaf documents
- `AGENTS.md` references all 5 core rules
- `ACTIVATION_LEVELS.md` defines Level 0-3
- High-risk documents contain Level 2 or Level 3 activation language

---

## 🔄 Full Initialization Flow

When AI executes the initialization (via either method), the complete flow is:

```text
Confirm directory name → Replace placeholders → Copy AGENTS.md to root → Project discovery → Generate PROJECT_PROFILE.md → Generate domain rules → Validate → Activate by level
```

| Step | Action | By | Output |
|------|--------|-----|--------|
| 1. Confirm name | Ask whether to rename `rulers` directory; if renamed, replace all `{{RULERS_DIR}}` placeholders | AI + Human | Correct directory name and paths |
| 2. Migrate entry | Copy AGENTS.md from template dir to project root (keep copy in template for validation) | AI/auto | Root `AGENTS.md` |
| 3. Project discovery | Scan 9 dimensions: repo structure, tech stack, commands, security, persistence, API contracts, frontend, CI/CD, high-risk areas | AI + Human | Discovery records |
| 4. Generate profile | Fill `PROJECT_PROFILE.template.md` with confirmed facts, cite evidence sources | AI + Human review | `PROJECT_PROFILE.md` |
| 5. Generate rules | Generate `INDEX.md` + leaf rules for each existing domain, delete unused domain templates | AI + Human review | Domain `INDEX.md` + leaf rules |
| 6. Validate | Run `validate_rulers.py`, fix structural issues (max 3 retries) | AI/auto | Validation passed |
| 7. Activate | Activate domains level by level per activation gates | Human review | Working AI standards system |

---

## 📁 Template Directory Reference

The template (`documents/rulers/`) contains:

### Entry Files

| File | Description |
|------|-------------|
| `AGENTS.md` | AI collaboration protocol entry — AI reads this to start initialization |
| `INDEX.md` | Template navigation |
| `PROJECT_PROFILE.template.md` | Project profile template |

### core/ — Global Resident Rules

| File | Description |
|------|-------------|
| `HARD_CONSTRAINTS.md` | Global hard constraints |
| `WORKFLOW.md` | Implementation workflow & reasoning order |
| `DOC_GOVERNANCE.md` | Rules document governance |
| `RULER_MAINTENANCE.md` | Rule maintenance decision tree |
| `GIT_COMMIT_CONVENTION.md` | Git commit convention |

### backend/ — Backend Specs

Architecture, API security, data access, configuration, observability, testing.

### database/ — Database Specs

Schema design, migration, review checklist, seed & backfill.

### frontend/ — Frontend Specs

- `common/`: Shared design tokens, styles, accessibility baseline
- `web/develop/`: Web architecture, API integration, authorization, state management, testing
- `web/design/`: Web visual system, component patterns, accessibility
- `app/develop/`: Mobile architecture, UI patterns, testing
- `app/design/`: Mobile tokens, layout, components, interaction, accessibility, examples

### bootstrap/ — Bootstrap Guides

| File | Description |
|------|-------------|
| `PROJECT_DISCOVERY.md` | Project discovery process |
| `BROWNFIELD_RULE_GENERATION.md` | Brownfield rule generation guide |
| `ACTIVATION_LEVELS.md` | Four-level activation gate definitions |
| `RULES_COMPLETENESS_CHECKLIST.md` | Completeness checklist |

### scripts/

`validate_rulers.py` — Structural integrity checker.

---

## 🔑 Key Conventions

### Protected Content

- `metadata:` / `applies_to` / `trigger_keywords` / `must_load_with` — Machine-parsable metadata keys
- `AI_FILL` — Marks sections requiring AI population
- `PROJECT_PROFILE.md` / `PROJECT_PROFILE.template.md` / `AGENTS.md` / `INDEX.md` — Protocol filenames
- `Level 0` / `Level 1` / `Level 2` / `Level 3` — Activation level identifiers

### trigger_keywords Strategy

Each rule file uses bilingual trigger keywords for cross-model hit rate:

```yaml
trigger_keywords:
  - git
  - commit
  - conventional commits
  - 提交
  - 提交规范
```

### Conflict Resolution

```
core hard constraints > security rules > activation gates > domain rules > topic rules > examples
```

### Commit Conventions

- `type`: English (feat/fix/docs/refactor/test/chore/build/ci)
- `subject`: Chinese, verb-object structure, no trailing period
- `body`: Chinese, explain "what changed" and "why"
- Format: `<type>[optional scope]: <subject>`

---

## 🏗️ Project Structure

```text
ai-rulers-template/
├── README.md                        # This file (English)
├── README-zh.md                     # Chinese version
├── AGENTS.md                        # Template maintenance AI entry
├── logo.png
├── LICENSE
├── skills/                          # Packaged skills (deliverables)
│   ├── ai-rulers-init.skill         # Portable skill package
│   └── ai-rulers-init/              # Unpacked skill
│       ├── SKILL.md
│       └── templates/               # Embedded rulers template
├── documents/
│   └── rulers/                      # Rulers template (the product)
│       ├── AGENTS.md
│       ├── INDEX.md
│       ├── PROJECT_PROFILE.template.md
│       ├── core/                    # Global resident rules
│       ├── backend/                 # Backend domain specs
│       ├── database/                # Database domain specs
│       ├── frontend/                # Frontend domain specs
│       │   ├── common/
│       │   ├── web/
│       │   └── app/
│       ├── bootstrap/               # Boot & generation guides
│       └── scripts/                 # Validation scripts
└── docs/
    └── superpowers/
        ├── specs/                   # Design specs
        └── plans/                   # Implementation plans
```

---

## 🛠️ Development Guide

### Modifying Template Rules

1. Load `documents/rulers/core/DOC_GOVERNANCE.md` for governance before modifying
2. Run ruler impact assessment (see `documents/rulers/core/RULER_MAINTENANCE.md`)
3. Run validation after changes: `python3 documents/rulers/scripts/validate_rulers.py`
4. Follow commit conventions (see `documents/rulers/core/GIT_COMMIT_CONVENTION.md`)

### Modifying the ai-rulers-init Skill

1. Edit `skills/ai-rulers-init/SKILL.md` for workflow changes
2. Edit `skills/ai-rulers-init/templates/` for template updates
3. Re-package: `python -m scripts.package_skill skills/ai-rulers-init` (requires skill-creator)
4. Replace `skills/ai-rulers-init.skill` with the new package

### Commit Conventions

- `type`: English (feat/fix/docs/refactor/test/chore/build/ci)
- `subject`: Chinese, verb-object structure, no trailing period
- `body`: Chinese, explain "what changed" and "why"
- Format: `<type>[optional scope]: <subject>`

---

## ❓ FAQ

<details>
<summary><strong>Do I need all domains?</strong></summary>

No. Delete unused domains (e.g., no mobile app → remove `frontend/app/`) and update `AGENTS.md` and `INDEX.md` routing. The ai-rulers-init skill handles this automatically.

</details>

<details>
<summary><strong>Can I write code at Level 0?</strong></summary>

No. Level 0 permits project discovery only. A reviewed `PROJECT_PROFILE.md` is required before any implementation work.

</details>

<details>
<summary><strong>What if validation fails?</strong></summary>

Fix errors one at a time. Common issues: broken links, missing metadata, INDEX missing leaf documents. The ai-rulers-init skill auto-fixes most validation errors. If manual, check error messages and fix accordingly.

</details>

<details>
<summary><strong>How do I update already-activated rules?</strong></summary>

Run ruler impact assessment first (see `core/RULER_MAINTENANCE.md`). The ai-rulers-init skill supports incremental re-runs — it will detect changes and only regenerate what's needed.

</details>

<details>
<summary><strong>What if I add a new platform later (e.g., mobile)?</strong></summary>

**Skill:** Re-run the ai-rulers-init skill. **Manual:** Copy missing domain templates from this repo, then tell AI: "load AGENTS.md, a new domain was added, perform project discovery for the new domain."

</details>

<details>
<summary><strong>How do I install the skill?</strong></summary>

**Claude Code:** Copy `skills/ai-rulers-init/` to `~/.claude/skills/ai-rulers-init/`
**Other platforms:** Import `skills/ai-rulers-init.skill`

</details>

<details>
<summary><strong>What if the AI doesn't auto-start initialization after copy?</strong></summary>

Send the explicit instruction: "Please load `documents/rulers/AGENTS.md` into context, then follow the initialization flow to complete the standards initialization for this project."

</details>

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=AndersJet/ai-rulers-template&type=Date)](https://star-history.com/#AndersJet/ai-rulers-template&Date)

---

<div align="center">

### If this project helps you, give us a Star!

Made with ❤️ by [AndersJet](https://github.com/AndersJet)

</div>
