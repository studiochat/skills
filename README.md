# Studio Chat Agent Skills

Skills for [Claude Code](https://claude.ai/code) and other AI agents that follow the [Agent Skills](https://agentskills.io/) specification.

These skills give AI agents deep expertise in analyzing and managing [Studio Chat](https://studiochat.io) projects — the AI-powered customer experience platform.

## Available Skills

### [data-expert](./skills/data-expert/)

Analyze customer conversation data: deflection rates, sentiment distributions, resource quality, trending topics, latency, and more. Includes scripts for batch export with enrichment.

**Use when:** analyzing conversations, reviewing performance, examining trends, computing metrics, or generating reports.

### [studio-chat-admin](./skills/studio-chat-admin/)

Manage project configuration: knowledge bases, playbooks, training, office hours, and API tools. Full CRUD operations via the Studio Chat API.

**Use when:** creating or editing KBs, updating playbook instructions, configuring schedules, or managing API integrations.

## Installation

### Claude Code

```bash
# Install all skills
claude skill add studiochat/skills

# Or copy individual skills
cp -r skills/data-expert ~/.claude/skills/
cp -r skills/studio-chat-admin ~/.claude/skills/
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

### Getting an API Key

API keys are available by request. Contact the Studio Chat team:

- **Email**: hey@studiochat.io
- **Website**: [studiochat.io](https://studiochat.io)

Once you have a key, set the environment variables before using the skills:

```bash
export STUDIO_API_TOKEN="sbs_your_api_key_here"
export STUDIO_PROJECT_ID="your-project-uuid"
```

### API Key Permissions

| Permission | data-expert | studio-chat-admin |
|------------|:-----------:|:-----------------:|
| Read conversations | Yes | Yes |
| Read configuration | Yes | Yes |
| Write configuration | No | Yes (requires approval) |
| Export data | Yes | No |

## Skill Structure

Each skill follows the [Agent Skills specification](https://agentskills.io/specification):

```
skill-name/
├── SKILL.md              # Required — Instructions + YAML frontmatter
├── LICENSE.txt            # License terms
├── scripts/              # Executable Python scripts (no external deps)
└── references/           # Detailed API reference docs
```

- `SKILL.md` is the entry point — agents read the frontmatter to decide when to activate
- `scripts/` contain zero-dependency Python utilities (stdlib only)
- `references/` hold detailed specs loaded on demand (progressive disclosure)
