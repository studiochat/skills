# Studio Chat Agent Skills

Skills for [Claude Code](https://claude.ai/code) and other AI agents that follow the [Agent Skills](https://agentskills.io/) specification.

These skills give AI agents deep expertise in analyzing and managing [Studio Chat](https://studiochat.io) projects — the AI-powered customer experience platform.

## Available Skills

### [builder](./skills/builder/)

Build and configure assistants: instructions, knowledge bases, skills (casuísticas), tasks, example blocks, API tools, toolkit actions, alerts, monitors, schedules and trending topics. Full CRUD via the Studio Chat API.

**Use when:** creating or editing an assistant, wiring up macros and the objects they reference, connecting a toolkit, or changing any part of a project's configuration.

### [continuous-improvement](./skills/continuous-improvement/)

The proactive loop for shipping a behaviour change: clarify the policy → decide where it belongs (base instruction vs casuística vs KB vs example) → minimal draft → validate with in-memory overrides → ship via approvals → eval coverage.

**Use when:** the request is "the assistant needs to do X", or a trend in the data justifies a change. Orchestrates the other three skills; it has no API of its own.

### [data-expert](./skills/data-expert/)

Analyze conversation data: deflection rates, sentiment distributions, resource quality, trending topics, follow-up funnels, KB search gaps, API-tool failures, latency. Includes scripts for batch export with enrichment.

**Use when:** analyzing conversations, reviewing performance, examining trends, or computing metrics.

### [quality-engineer](./skills/quality-engineer/)

Test and evaluate assistant behavior. Create test cases with assertions, run evaluations against playbook versions, analyze pass/fail results, simulate conversations, and debug a real conversation end to end.

**Use when:** creating QA suites, running evals, comparing versions, or investigating why an assistant answered the way it did.

### [report-builder](./skills/report-builder/)

Create and configure automated reports — scheduled or one-off — including instructions, assistant scope, Slack delivery and the Block Kit output format.

**Use when:** setting up a recurring report, or running a one-off question through the report pipeline.

## Installation

### Claude Code

```bash
# Copy the skills you want into your skills directory
cp -r skills/builder ~/.claude/skills/
cp -r skills/data-expert ~/.claude/skills/
```

### Claude.ai

Upload the `SKILL.md` file from any skill folder to your project knowledge.

### Other Agents

Each skill is a self-contained directory with a `SKILL.md` entry point. Copy the skill folder into your agent's skill/tool directory.

## Authentication

All API calls require an API key. The scripts read credentials from environment variables:

| Variable | Description |
|----------|-------------|
| `STUDIO_API_TOKEN` | API key (starts with `sbs_`) |
| `STUDIO_PROJECT_ID` | UUID of the project to analyze/manage |
| `STUDIO_API_URL` | Optional. Defaults to `https://api.studiochat.io` |

An `sbs_` key travels in the `X-API-Key` header (the scripts handle this) and is **bound to one project** — the project it was minted for. `STUDIO_PROJECT_ID` has to be that project.

### Getting an API Key

API keys are available by request. Contact the Studio Chat team:

- **Email**: hey@studiochat.io
- **Website**: [studiochat.io](https://studiochat.io)

Once you have a key, set the environment variables before using the skills:

```bash
export STUDIO_API_TOKEN="sbs_your_api_key_here"
export STUDIO_PROJECT_ID="your-project-uuid"
```

### What a key can do

Every endpoint these skills document accepts an `sbs_` key. Two things narrow what happens next:

- **A per-user key inherits its owner's account role.** A key minted for a non-admin can read but not configure — writes answer `403`. A legacy account-wide key is unaffected.
- **Some writes queue for a human.** Changes that reach production behaviour (assistant content and settings, skills, active version, deploys, training, in-use API tools and pills, segments, project settings) answer **`202` with an `approval_id`** instead of executing. Everything else — knowledge bases, reports, alerts, monitors, evals, example blocks, schedules, saved filters — is direct. The `builder` skill has the full list, and it matters: **creating a knowledge base is direct, but the training that makes it searchable is queued.**

## MCP server

There is also a hosted MCP server at **`mcp.studiochat.io`** covering the same ground as these skills — roughly 75 tools across configuration, analytics, QA and reports — with no API key to manage.

Any active member of the account can connect; what the connection can do is resolved from the member's account role on **every request**, so promoting or demoting someone takes effect immediately with no reconnect. Admins get the full surface; members get the read tools.

In Claude Code: add the server, then `/mcp` and authenticate through the browser flow.

The MCP is the better door when an agent is doing exploratory work, and it does a few things these skills don't (live API-tool dry runs, a JMESPath tuner, structured tag filters, run-to-run eval diffs). The REST API these skills wrap is the better door for scripted, reproducible automation and for anything running without a human to consent.

## Skill Structure

Each skill follows the [Agent Skills specification](https://agentskills.io/specification):

```
skill-name/
├── SKILL.md              # Required — Instructions + YAML frontmatter
├── scripts/              # Executable Python scripts (no external deps)
└── references/           # Detailed API reference docs
```

- `SKILL.md` is the entry point — agents read the frontmatter to decide when to activate
- `scripts/` contain zero-dependency Python utilities (stdlib only)
- `references/` hold detailed specs loaded on demand (progressive disclosure)

`continuous-improvement` is `SKILL.md` only — it is a decision workflow over the other skills, with no API surface of its own.
