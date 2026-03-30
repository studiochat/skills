---
name: report-builder
description: >
  Create and configure automated reports in Studio Chat. Use when asked to set up a new report,
  schedule recurring reports, define report instructions, select which assistants/playbooks to include,
  configure Slack delivery, or manage existing report definitions. Expert at crafting report instructions
  that produce structured, high-quality output using the Block Kit format.
---

# Report Builder

Create, configure, and manage automated reports via the Studio Chat Reports API. Reports are executed by SAMI in a sandbox with the `data-expert` skill — this skill focuses on *defining* reports, not executing them.

## Key Terminology

**Assistants and playbooks are the same concept.** Users say "assistant" — the API uses "playbook."
The `playbook_base_ids` field in report configuration filters by assistant.

## Setup

Uses the same environment variables as other Studio Chat skills:

```bash
export STUDIO_API_TOKEN="sbs_your_api_key_here"
export STUDIO_PROJECT_ID="your-project-uuid"
```

## Scripts

### reports.py — Reports API client

```bash
# List all reports
python3 scripts/reports.py list

# Get a specific report
python3 scripts/reports.py get <report_id>

# Create a report
python3 scripts/reports.py create --name "Weekly CX Report" \
  --instructions "Analyze conversations..." \
  --playbooks PLAYBOOK_BASE_ID_1,PLAYBOOK_BASE_ID_2 \
  --schedule manual --window 7 \
  --slack "#reports" --email "user@company.com,boss@company.com"

# Update a report
python3 scripts/reports.py update <report_id> --name "New Name" --slack "#new-channel" --email "new@company.com"

# Delete a report
python3 scripts/reports.py delete <report_id>

# Trigger a manual run
python3 scripts/reports.py run <report_id> [--window 7]

# List runs for a report
python3 scripts/reports.py runs <report_id>

# Get run status and logs
python3 scripts/reports.py run-status <run_id>
```

## Important: Do Not Run Unless Asked

**Creating a report does NOT mean running it.** By default, only create the report definition. Do NOT trigger a run unless the user explicitly asks to execute or run it.

- "Create a weekly report" → create the definition only
- "Create and run a report" → create + trigger run
- "Generate a report right now" → create + trigger run
- "Set up a report for me" → create the definition only

## Workflows

### Create a Report Definition

Default workflow — create the definition without executing:

1. **Discover** — List playbooks to identify which assistants to include
2. **Design** — Craft instructions based on what the user wants to analyze
3. **Create** — Create the report definition
4. **Confirm** — Tell the user the report was created and how to run it (from the UI or by asking)

### One-Off Report (only when user asks to run)

Only when the user explicitly asks to generate/run/execute a report now:

1. **Create** — Create a manual report definition
2. **Run** — Trigger a manual run
3. **Monitor** — Poll `run-status` until completed (check every 15–20 seconds)
4. **Deliver** — Share the result: the report is viewable in the Reports UI

```bash
# Create + run (only when explicitly requested)
python3 scripts/reports.py create --name "Ad-hoc: Last 7 days" \
  --instructions "..." --window 7 --playbooks BASE_ID
# Note the report ID from output, then:
python3 scripts/reports.py run REPORT_ID --window 7
# Monitor:
python3 scripts/reports.py run-status RUN_ID
```

### Recurring Report

When the user wants a scheduled report:

1. **Discover** — List playbooks
2. **Design** — Craft instructions based on what the user wants
3. **Create** — Create with `--schedule cron --cron "EXPRESSION"` and optionally `--slack "#channel"`
4. **Confirm** — Tell the user the report is scheduled. Do NOT trigger a test run unless asked.

## Report Configuration

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name for the report |
| `instructions` | Yes | What SAMI should analyze and report on |
| `schedule_type` | No | `manual` (default) or `cron` |
| `cron_expression` | No | Cron schedule (min interval: 30 min). E.g. `0 9 * * 1-5` |
| `playbook_base_ids` | No | Filter to specific assistants. Empty = all |
| `time_window_days` | No | Lookback window for manual reports (default: 7) |
| `slack_channel` | No | Slack channel for PDF delivery. E.g. `#reports` |
| `email_recipients` | No | List of email addresses for PDF delivery. E.g. `["a@b.com"]` |

### Schedule Presets

| Description | Cron |
|-------------|------|
| Weekdays at 9 AM (ART) | `0 12 * * 1-5` |
| Weekly Friday 3 PM (ART) | `0 18 * * 5` |
| Weekly Monday 9 AM (ART) | `0 12 * * 1` |
| Daily at 6 PM (ART) | `0 21 * * *` |
| Monthly on the 1st (ART) | `0 12 1 * *` |

**Note:** Cron reports auto-calculate the time window from the interval (daily = 1 day, weekly = 7 days). Manual reports use the `time_window_days` field.

## Writing Good Instructions

The report sandbox already has the `data-expert` skill loaded. This means SAMI already knows how to fetch conversations, compute metrics, call the analytics API, and process data. **Do not include API endpoints, scripts, or fetch instructions in the report instructions.**

Instructions define **what** to analyze and **what output** to produce — never **how** to get the data.

### Instruction Principles

1. **Describe the analysis, not the implementation** — "Show deflection rate by playbook" is correct. "Call GET /projects/.../analytics" is wrong — the data-expert skill handles that.
2. **Be specific about metrics** — Name the KPIs: deflection rate, sentiment distribution, handoff rate, response time, conversation volume
3. **Specify comparisons** — "Compare to the previous period" gives context to the numbers
4. **Name the playbooks** — Even if filtered via `playbook_base_ids`, mention them by name for clarity
5. **Ask for actionable insights** — "Identify top 3 issues" is better than "analyze everything"
6. **Structure the output** — "Start with key metrics, then breakdown by topic, then recommendations"
7. **Never include technical details** — No URLs, no script paths, no API tokens. The execution environment handles all of that.

### Example Instructions

**Daily Operations Report:**
```
Analyze all conversations from the time window.

1. Start with key metrics: total conversations, deflection rate, average response time, sentiment breakdown.
2. Break down by playbook: show each assistant's volume, deflection rate, and sentiment.
3. Identify the top 5 topics customers asked about.
4. Flag any conversations with very negative sentiment — summarize what went wrong.
5. End with 3 actionable recommendations for the CX team.
```

**Weekly Performance Summary:**
```
Generate a weekly performance summary.

1. Key metrics overview with week-over-week comparison.
2. Deflection rate trend — is it improving?
3. Sentiment distribution: what percentage of conversations are positive/neutral/negative?
4. Top 10 topics by volume with sentiment breakdown per topic.
5. Handoff analysis: which topics cause the most escalations?
6. Knowledge base gaps: are there topics where the AI consistently fails?
7. Recommendations for playbook improvements.
```

**Playbook-Specific Analysis:**
```
Deep dive into the Cotizador assistant.

1. Volume and deflection rate for this playbook only.
2. Most common questions customers ask.
3. Conversations where the assistant gave incorrect pricing — flag for review.
4. Average conversation length and response quality.
5. Comparison to previous period: is performance improving?
```

## API Reference

Full endpoint documentation: [references/api-reference.md](references/api-reference.md)
