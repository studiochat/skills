# Studio Chat Agent Skills

Skills for [Claude Code](https://claude.ai/code), Claude Desktop, Codex CLI, OpenCode, Gemini CLI and any other agent that follows the [Agent Skills](https://agentskills.io/) specification.

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

| Surface | How to install | Works with these skills? |
|---|---|---|
| **Claude Desktop / claude.ai / Cowork** | Add this repo as a plugin marketplace | **Yes, if network egress allows `api.studiochat.io`** — see below |
| **Claude Code** | `/plugin marketplace add studiochat/skills` | **Yes.** Skills get the same network access as any program on your machine |
| **Claude API** (`/v1/skills`) | Upload via the Skills API | **No.** API skills run in a container with **no network access at all** |
| **Codex CLI, OpenCode, Gemini CLI** | Filesystem — copy the folder | **Yes.** Local CLIs, full network access |
| **Other agents** | Copy the folder | Depends on the agent |

This repository is a **plugin marketplace**: it ships one plugin, `studiochat`, that bundles all
five skills. Installing the plugin is the recommended route on every Claude surface, because
updates arrive by syncing the marketplace instead of re-copying folders.

### Claude Desktop, claude.ai and Cowork

**1. Add the marketplace.** Go to **Customize → Plugins**, click **Add**, then **Add marketplace**,
and enter:

```
studiochat/skills
```

**2. Install the plugin.** Find **Studio Chat** in the marketplace and click **Add**. All five skills
appear, each with its own toggle.

**3. Allow the API domain.** This is the step that actually decides whether they work:

| Plan | Default network egress | What you need to do |
|---|---|---|
| Free / Pro / Max | All domains | Nothing — it works |
| **Team** | **Package managers only** | An owner must allow `api.studiochat.io` in **Organization settings → Capabilities** |
| **Enterprise** | **Disabled** | An owner must enable network egress *and* allow `api.studiochat.io` |

Without that, the scripts fail on every call with a connection error, even though the skills load
and look fine.

**4. Supply credentials.** There are no environment variables in this sandbox, so `STUDIO_API_TOKEN`
and `STUDIO_PROJECT_ID` cannot be preset the way they can in a terminal. Export them at the start of
the conversation and they persist for that conversation's container:

> Run `export STUDIO_API_TOKEN="sbs_…"` and `export STUDIO_PROJECT_ID="…"`, then use the builder
> skill to…

Treat that conversation as holding a live credential.

**On a Team or Enterprise plan** you don't need to be an admin to add the marketplace, as long as
the owner hasn't turned off **User-created skills** (or **Skills** altogether) in **Organization
settings → Plugins & skills → Policy**. If **Add marketplace** doesn't appear in your **Add** menu,
that's why — ask an owner. Code execution must also be on: **Settings → Capabilities → Code
execution and file creation** on individual plans, **Organization settings → Plugins & skills →
Policy** on Team and Enterprise.

<details>
<summary>Without the plugin: upload a single skill as a zip</summary>

Package each skill as its own zip, with the skill folder at the **root** of the archive:

```bash
cd skills
zip -r builder.zip builder -x '*__pycache__*' '*.DS_Store'
```

Then **Customize → Skills → + → Upload a skill**. An uploaded skill is private to your account, and
`continuous-improvement` needs `builder` uploaded too, because it calls `builder`'s script.

</details>

### Claude Code

```
/plugin marketplace add studiochat/skills
/plugin install studiochat@studiochat
```

Or from your shell: `claude plugin marketplace add studiochat/skills` and
`claude plugin install studiochat@studiochat`. Get updates with `/plugin marketplace update studiochat`.

Plugin skills are namespaced, so you invoke them as `/studiochat:builder`, `/studiochat:data-expert`
and so on — or just describe the task and Claude loads the matching skill by its `description`.
Export `STUDIO_API_TOKEN` and `STUDIO_PROJECT_ID` in the shell you start Claude Code from.

If you'd rather not use a plugin, copy the folders instead:

```bash
# Personal — available in all your projects
cp -r skills/* ~/.claude/skills/

# Or per-project, committed so your team gets them
mkdir -p .claude/skills && cp -r skills/* .claude/skills/
```

Skills do **not** sync across surfaces, except that Claude Code can load plugins installed in your
claude.ai account. Install them wherever you want them.

### Claude API

**Not supported.** Skills uploaded through the Skills API run in a sandboxed container with no
network access and no runtime package installation, so a skill whose entire job is calling
`api.studiochat.io` cannot function there.

If you are building on the API, call the Studio Chat REST API directly — the `references/`
directory in each skill is a complete, current endpoint reference you can use as the specification.

### Codex CLI, OpenCode, Gemini CLI

`SKILL.md` is an open, cross-agent format, so these skills work unchanged in any agent that
implements it. All three are local CLIs, so — like Claude Code — they get normal network access
and read `STUDIO_API_TOKEN` from your shell. No zip, no upload, no domain allow-list.

**`.agents/skills/` is the interoperable path**: Codex CLI, OpenCode and Gemini CLI all read it.
Install there once and every one of them picks the skills up.

```bash
# Personal — works in Codex CLI, OpenCode and Gemini CLI at once
mkdir -p ~/.agents/skills
cp -r skills/* ~/.agents/skills/

# Or per-repository, committed for the team
mkdir -p .agents/skills && cp -r skills/* .agents/skills/
```

Per-tool paths, if you'd rather be explicit:

| Tool | Personal | Repository |
|---|---|---|
| **Codex CLI** | `~/.agents/skills/` | `.agents/skills/` |
| **OpenCode** | `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/` | `.opencode/skills/`, `.claude/skills/`, `.agents/skills/` |
| **Gemini CLI** | `~/.gemini/skills/` or `~/.agents/skills/` | `.gemini/skills/` or `.agents/skills/` |

**OpenCode reads Claude Code's directories directly**, so if you already installed into
`~/.claude/skills/` there is nothing more to do.

Discovery works the same everywhere: the agent sees each skill's `name` and `description`, and
loads the body only when your request matches. Codex also takes an explicit `$skill-name`.

Note that `AGENTS.md` and `GEMINI.md` are a different mechanism — always-on repository
conventions, loaded into every request. These skills are the opposite: on-demand expertise that
stays out of context until it is needed. Don't paste them into `AGENTS.md`.

### Other agents

Each skill is a self-contained directory with a `SKILL.md` entry point plus `scripts/` and
`references/`. Copy the folder into your agent's skill directory.

The frontmatter carries `name` and `description` on every skill, `name` matches the directory
name, and the scripts are stdlib-only Python 3 with nothing to install — which is what the
stricter loaders check for.

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
See [Installation](#claude-desktop-claudeai-and-cowork).

### What a key can do

Every endpoint these skills document accepts an `sbs_` key. Two things narrow what happens next:

- **A per-user key inherits its owner's account role.** A key minted for a non-admin can read but not configure — writes answer `403`. A legacy account-wide key is unaffected.
- **Some writes queue for a human.** Changes that reach production behaviour (assistant content and settings, skills, active version, deploys, training, in-use API tools and pills, segments, project settings) answer **`202` with an `approval_id`** instead of executing. Everything else — knowledge bases, reports, alerts, monitors, evals, example blocks, schedules, saved filters — is direct. The `builder` skill has the full list, and it matters: **creating a knowledge base is direct, but the training that makes it searchable is queued.**

## MCP server

There is also a hosted MCP server at **`mcp.studiochat.io`** covering the same ground as these skills — close to 90 tools across configuration, analytics, QA, reports and media — with no API key to manage.

Any active member of the account can connect; what the connection can do is resolved from the member's account role on **every request**, so promoting or demoting someone takes effect immediately with no reconnect. Admins get the full surface; members get the read tools.

In Claude Code: add the server, then `/mcp` and authenticate through the browser flow.

The MCP is the better door when an agent is doing exploratory work, and it does a few things these skills don't (a JMESPath tuner, structured tag filters, run-to-run eval diffs, and managing the media library — the images and files an assistant can send — where it is enabled for your account). The REST API these skills wrap is the better door for scripted, reproducible automation and for anything running without a human to consent.

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
