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

These skills are **HTTP clients** — every one of them works by calling `https://api.studiochat.io`.
That single fact decides where they can run, because each Claude surface sandboxes network access
differently:

| Surface | How skills are installed | Works with these skills? |
|---|---|---|
| **Claude Code** | Filesystem — copy the folder | **Yes.** Skills get the same network access as any program on your machine |
| **Claude Desktop / claude.ai** | Upload a `.zip` in settings | **Yes, if network egress allows `api.studiochat.io`** — see below |
| **Claude API** (`/v1/skills`) | Upload via the Skills API | **No.** API skills run in a container with **no network access at all** |
| **Other agents** | Copy the folder | Depends on the agent |

Skills do **not** sync across surfaces. Install them separately wherever you want them.

### Claude Code

Filesystem-based, no upload and no packaging.

```bash
# Personal — available in all your projects
cp -r skills/builder ~/.claude/skills/
cp -r skills/data-expert ~/.claude/skills/

# Or per-project, committed so your team gets them
mkdir -p .claude/skills && cp -r skills/* .claude/skills/
```

You can also point Claude Code at a checkout of this repo without copying anything:

```bash
claude --add-dir /path/to/studiochat-skills
```

Claude loads a skill automatically when your request matches its `description`, or you can invoke
one directly with `/builder`, `/data-expert`, and so on.

### Claude Desktop and claude.ai

Same account, same settings — the steps below cover both.

**1. Turn on code execution.** Skills do not appear at all without it.

- Free / Pro / Max: **Settings → Capabilities → Code execution and file creation**
- Team / Enterprise: an owner enables **Organization settings → Skills**, both *Code execution and
  file creation* **and** *Skills*

**2. Package each skill as its own zip.** The skill folder must be the **root** of the archive, not
nested inside another folder:

```bash
cd skills
zip -r builder.zip builder -x '*__pycache__*' '*.DS_Store'
zip -r data-expert.zip data-expert -x '*__pycache__*' '*.DS_Store'
# …one zip per skill you want
```

**3. Upload.** Go to **Customize → Skills** (on some builds, **Settings → Features**), click **+**,
then **Create skill**, and upload the zip. The skill appears in your list with a toggle.

**4. Allow the API domain.** This is the step that actually decides whether they work:

| Plan | Default network egress | What you need to do |
|---|---|---|
| Free / Pro / Max | All domains | Nothing — it works |
| **Team** | **Package managers only** | An owner must allow `api.studiochat.io` in **Organization settings → Capabilities** |
| **Enterprise** | **Disabled** | An owner must enable network egress *and* allow `api.studiochat.io` |

Without that, the scripts fail on every call with a connection error, even though the skill loads
and looks fine.

**5. Supply credentials.** There are no environment variables in this sandbox, so `STUDIO_API_TOKEN`
and `STUDIO_PROJECT_ID` cannot be preset the way they can in a terminal. Export them at the start of
the conversation and they persist for that conversation's container:

> Run `export STUDIO_API_TOKEN="sbs_…"` and `export STUDIO_PROJECT_ID="…"`, then use the builder
> skill to…

Treat that conversation as holding a live credential.

**Two limits worth knowing:** an uploaded skill is **private to your own account** — each teammate
uploads their own copy, and claude.ai has no org-wide distribution for custom skills. And a skill
uploaded here is not available in Claude Code or the API.

### Claude API

**Not supported.** Skills uploaded through the Skills API run in a sandboxed container with no
network access and no runtime package installation, so a skill whose entire job is calling
`api.studiochat.io` cannot function there.

If you are building on the API, call the Studio Chat REST API directly — the `references/`
directory in each skill is a complete, current endpoint reference you can use as the specification.

### Other agents

Each skill is a self-contained directory with a `SKILL.md` entry point plus `scripts/` and
`references/`. Copy the folder into your agent's skill directory. The scripts are stdlib-only
Python 3 with no dependencies to install.

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

In Claude Desktop / claude.ai there is no shell to export from ahead of time — ask Claude to run
those two exports as the first step of the conversation instead, and they hold for the rest of it.
See [Installation](#claude-desktop-and-claudeai).

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
