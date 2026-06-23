<div align="center">

<img src="logo.png" alt="Rulers Template" width="120">

# Rulers Template

**Universal AI Coding Standards Template — Progressive Guardrails for AI-Powered Development**

> Standards are not final drafts, but living systems symbiotic with the business. Calibrated in practice, evolved through feedback — no silver bullet, only iterative convergence toward truth.

<div align="center">

<a href="./README-zh.md">简体中文</a> |
<strong>English</strong>

</div>

[![Version](https://img.shields.io/badge/version-v1.0.6-blue)](https://github.com/AndersJet/ai-rulers-constructor/releases)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/AndersJet/ai-rulers-constructor/pulls)

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
- [Template Directory Reference](#template-directory-reference)
- [Key Conventions](#key-conventions)
- [FAQ](#faq)
- [Star History](#star-history)

---

## 🎯 The Problem

AI coding assistants are powerful but unpredictable. Without clear boundaries, they can:

- Violate your project's security, data, or deployment policies
- Generate code in inconsistent styles across sessions
- Apply generic patterns that don't match your tech stack
- Perform high-risk operations (database migrations, auth changes) without review

**Every project needs guardrails. Writing them from scratch is tedious and easy to get wrong.**

## 💡 The Solution

Rulers Template gives your AI assistants a **project-specific rulebook** — automatically generated from your actual codebase, not copied from a blog post.

- **Evidence-driven** — Rules are generated from your project's real files, configs, and commands, never fabricated
- **Progressive loading** — AI only loads rules relevant to the current task
- **Activation gates** — Four security levels (Level 0-3) prevent AI from doing dangerous work before human review
- **Domain routing** — Backend, database, frontend — each domain gets its own constraints
- **One-command init** — The `ai-rulers-init` skill scans your project and generates everything automatically

### How It Works

```text
1. Copy the template into your project
2. AI scans your codebase and generates PROJECT_PROFILE.md
3. AI creates domain-specific rules for your tech stack
4. Rules are activated level-by-level after human review
5. Every future AI session follows these rules automatically
```

<details>
<summary><strong>Full initialization flow (click to expand)</strong></summary>

| Step | Action | Output |
|------|--------|--------|
| 1. Confirm name | Ask whether to rename `rulers` directory; replace `{{RULERS_DIR}}` placeholders if renamed | Correct directory name and paths |
| 2. Migrate entry | Copy `AGENTS.md` to project root | Root `AGENTS.md` |
| 3. Project discovery | Scan 9 dimensions: repo structure, tech stack, commands, security, persistence, API contracts, frontend, CI/CD, high-risk areas | Discovery records |
| 4. Generate profile | Fill `PROJECT_PROFILE.template.md` with confirmed facts, cite evidence sources | `PROJECT_PROFILE.md` |
| 5. Generate rules | Create `INDEX.md` + leaf rules for each existing domain, delete unused templates | Domain `INDEX.md` + leaf rules |
| 6. Validate | Run `validate_rulers.py`, fix structural issues (max 3 retries) | Validation passed |
| 7. Activate | Activate domains level by level per activation gates | Working AI standards system |

</details>

---

## 🚀 Quick Start

### Method 1: Copy + AI Auto-Init

```bash
# 1. Clone this repo
git clone https://github.com/AndersJet/ai-rulers-constructor.git

# 2. Copy rulers/ into your target project
cp -r ai-rulers-constructor/documents/rulers /path/to/your-project/documents/
```

**3. Open your project in an AI coding assistant and send:**

> Please load `documents/rulers/AGENTS.md` into context, then follow the initialization flow to complete the standards initialization for this project.

### Method 2: Install Skill + One-Command Init (Recommended)

```bash
# 1. Clone this repo
git clone https://github.com/AndersJet/ai-rulers-constructor.git

# 2. Install the skill
#    Claude Code:
cp -r ai-rulers-constructor/skills/ai-rulers-init/ ~/.claude/skills/ai-rulers-init/

#    Other platforms (Cursor, Copilot, etc.):
#    Import ai-rulers-constructor/skills/ai-rulers-init.skill
```

**3. Open your target project, send to AI:**

> Initialize AI rulers for this project using the ai-rulers-init skill.

| | Method 1 (Copy) | Method 2 (Skill) |
|---|---|---|
| **Setup** | Copy directory manually | Install skill once |
| **Init** | Send AI: "load AGENTS.md, follow init flow" | Send AI: "init rulers using skill" |
| **Incremental** | Manual re-copy + re-init | Re-run skill, auto-detects new domains |
| **Best for** | One-off use, trying it out | Multiple projects, team onboarding |

<details>
<summary><strong>Deploy with <code>ruler</code> CLI (optional)</strong></summary>

After initialization, you can optionally use the [`ruler`](https://github.com/intellectronica/ruler) CLI for tighter AI assistant integration.

**Prerequisites:** Node.js + `npm install -g @intellectronica/ruler`

```bash
# In your target project root:
ruler init                           # Creates .ruler/ directory
cp AGENTS.md .ruler/AGENTS.md       # Copy generated AGENTS.md

# Deploy to your environment:
ruler apply --agents claude         # Claude Code
ruler apply --agents codex          # GitHub Copilot / Codex
# Other supported agents: kilocode, opencode, trae
```

> The `ruler` CLI is an optional companion. You can continue using the rulers template directly through `AGENTS.md` without it.

</details>

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
AGENTS.md → core/* → {{RULERS_DIR}}/PROJECT_PROFILE.md → domain INDEX.md → matched leaf rules
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

The ai-rulers-init skill runs validation automatically during initialization. Manual validation is useful when editing rules directly.

Validates:
- Markdown link validity (no external references)
- Every authoritative document has `metadata` (`applies_to`, `trigger_keywords`, `must_load_with`)
- `must_load_with` paths are resolvable and within template scope
- Each `INDEX.md` covers all sibling leaf documents
- `AGENTS.md` references all 5 core rules
- `ACTIVATION_LEVELS.md` defines Level 0-3
- High-risk documents contain Level 2 or Level 3 activation language

---

## 📁 Template Directory Reference

The template (`documents/rulers/`) contains:

| Path | Description |
|------|-------------|
| `AGENTS.md` | AI collaboration protocol entry — start here |
| `INDEX.md` | Template navigation |
| `PROJECT_PROFILE.template.md` | Project profile template |
| `core/` | Global resident rules: hard constraints, workflow, governance, maintenance, commit convention |
| `backend/` | Backend domain specs: architecture, API security, data access, observability, testing |
| `database/` | Database specs: schema design, migration, review checklist, seed & backfill |
| `frontend/` | Frontend specs: web + mobile, develop + design subdomains |
| `bootstrap/` | Boot & generation guides: discovery, brownfield rules, activation levels, completeness checklist |
| `scripts/` | `validate_rulers.py` — structural integrity checker |

For the full directory walkthrough, see [`documents/rulers/INDEX.md`](documents/rulers/INDEX.md).

---

## 🔑 Key Conventions

### Conflict Resolution

```
core hard constraints > security rules > activation gates > domain rules > topic rules > examples
```

### Protected Keywords

- `metadata:` / `applies_to` / `trigger_keywords` / `must_load_with` — Machine-parsable metadata keys
- `AI_FILL` — Marks sections requiring AI population
- `Level 0` / `Level 1` / `Level 2` / `Level 3` — Activation level identifiers

### Commit Conventions

- `type`: English (`feat`/`fix`/`docs`/`refactor`/`test`/`chore`/`build`/`ci`)
- `subject`: Chinese, verb-object structure, no trailing period
- `body`: Chinese, explain "what changed" and "why"
- Format: `<type>[optional scope]: <subject>`

See [`core/GIT_COMMIT_CONVENTION.md`](documents/rulers/core/GIT_COMMIT_CONVENTION.md) for the full convention.

---

## ❓ FAQ

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

---

## 🤝 Contributing

Want to modify rules or the skill? See [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=AndersJet/ai-rulers-constructor&type=Date)](https://star-history.com/#AndersJet/ai-rulers-constructor&Date)

---

<div align="center">

### If this project helps you, give us a Star!

Made with ❤️ by [AndersJet](https://github.com/AndersJet)

</div>
