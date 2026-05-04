---
name: data-expert
description: >
  Analyze customer conversation data, compute metrics, identify patterns, and generate reports
  using the Studio Chat Analytics API. Use when asked to analyze conversations, review performance,
  understand trends, examine deflection rates, sentiment distributions, handoff patterns, API tool
  usage, toolkit usage, resource analytics, sparklines, or any data analysis task involving
  platform activity.
---

# Data Expert

Fetch data from the Studio Chat API, process it with Python, and produce actionable analysis. All API calls are authenticated automatically via environment variables. The API base URL (`https://api.studiochat.io`) is hardcoded in the scripts.

## Key Terminology

**Assistants and playbooks are the same concept.** In the API, the term "playbook" is used
everywhere — but users refer to them as "assistants." When the user says "assistant," "bot,"
or "agent," they mean a playbook. Use `playbook_base_id` to filter by assistant (all versions)
or `playbook_id` for a specific version.

## Setup

Set the following environment variables before using the scripts:

```bash
export STUDIO_API_TOKEN="sbs_your_api_key_here"
export STUDIO_PROJECT_ID="your-project-uuid"
```

API keys are available by request from the Studio Chat team at hey@studiochat.io.

## Tools

### fetch.py — Single API call

```bash
python3 scripts/fetch.py <path> [--params key=value ...] [-o file.json]
python3 scripts/fetch.py <path> --method POST [--body '{}'] [-o file.json]
```

### export_conversations.py — Batch export with all metadata

```bash
python3 scripts/export_conversations.py \
  --start YYYY-MM-DD --end YYYY-MM-DD [filters] [--messages] \
  [--sentiment negative,neutral,positive] [--resources irrelevant,partial,relevant] \
  [--min-messages N] [--max-messages N] [--sort-by field] [--sort-order asc|desc] \
  [--format json|csv] -o output.json
```

Every conversation includes all metadata inline: summary, sentiment (label + reason),
resources (label + reason), user_intent, sentiment_shift, deflection_quality, handoff_reason,
recontact_risk (each with label + reason), skills, tags, handoff status, message count, latency, model.
Use `--messages` to also fetch full message history (one API call per conversation).

## Workflow

1. **Fetch** — Pull data from the API
2. **Save** — Write raw JSON to a working directory for reference
3. **Process** — Use Python to parse, filter, aggregate, compute
4. **Report** — Write findings to markdown or CSV

Always save intermediate data to files. This enables re-processing without re-fetching.

## API Endpoints

Full specifications: [references/api-reference.md](references/api-reference.md)

### High-Level Metrics

| Endpoint | Returns |
|----------|---------|
| `GET /projects/{pid}/conversations/analytics` | Totals, deflection rate, time series, breakdowns by playbook/tag |
| `GET /account/conversations/analytics` | Account-wide totals across all projects |
| `GET /projects/{pid}/conversations/metrics/aggregate` | Sentiment, resource-quality, sentiment shift, deflection quality, handoff reason, and recontact risk distributions (filterable by tags, inbox_id, playbook_base_id) |

### Conversation Data

| Endpoint | Returns |
|----------|---------|
| `GET /projects/{pid}/conversations` | Paginated list with all metadata inline: summary, user_intent, sentiment (label+reason), resources (label+reason), sentiment_shift, deflection_quality, handoff_reason, recontact_risk (each with label+reason), skills, tags, handoff, message_count, latency, model, **playbooks_info** (all participating playbooks). Filters: playbook (matches any participant, not just last active), date, handoff, tags, winback, inbox, search, sentiment, resources, message count, sorting |
| `GET /projects/{pid}/conversations/summaries` | Lightweight summaries for batch scanning: summary, sentiment, resources, user_intent, sentiment_shift, deflection_quality, handoff_reason, recontact_risk, tags, has_handoff, message_count, skills |
| `GET /projects/{pid}/conversations/{cid}` | **Full detail**: all metadata + complete message history with per-message token usage/cost + tool calls + citations. Each assistant message includes `playbook_id`, `playbook_name`, `playbook_version` in metadata (for multi-playbook conversations) |
| `POST /projects/{pid}/conversations/batch` | **Batch detail**: same as above for up to 50 conversations in a single request. Body: `{"conversation_ids": [...]}` |
| `GET /projects/{pid}/conversations/{cid}/messages` | Message history + citations (without metadata — prefer the detail endpoint above) |
| `GET /projects/{pid}/conversations/{cid}/metrics` | Sentiment, resource quality, summary for one conversation |
| `POST /projects/{pid}/conversations/{cid}/metrics/analyze` | Trigger scoring for an unscored conversation |

### AI Insights

| Endpoint | Returns |
|----------|---------|
| `GET /projects/{pid}/conversations/insights/trending-topics/status` | Cached topic analysis |
| `POST /projects/{pid}/conversations/insights/trending-topics/generate` | Start new topic analysis |
| `GET /projects/{pid}/conversations/insights/trending-topics/job/{jid}` | Poll job progress |
| `GET /projects/{pid}/conversations/insights/trending-topics/analysis/{aid}` | Completed topic analysis |

### Resource Analytics

| Endpoint | Returns |
|----------|---------|
| `GET /projects/{pid}/analytics/api-tools` | API tool usage: totals, success/fail, avg duration, time series, recent calls |
| `GET /projects/{pid}/analytics/api-tools/sparklines` | Lightweight per-tool daily counts for sparklines (trailing N days) |
| `GET /projects/{pid}/analytics/toolkits` | Toolkit usage: totals, success/fail, by-action breakdown, param breakdown, time series, recent calls |
| `GET /projects/{pid}/analytics/toolkit-calls/sparklines` | Lightweight per-toolkit daily counts for sparklines (trailing N days) |
| `GET /projects/{pid}/analytics/skills` | Skill usage: totals, success/fail, time series, recent loads. Filters: skill_name, date range, search |
| `GET /projects/{pid}/analytics/skills/sparklines` | Lightweight per-skill daily counts for sparklines (trailing N days) |
| `GET /projects/{pid}/analytics/kbs` | KB citation usage: total citations, by-source breakdown, time series, recent. Filters: kb_id, item_id, source, date range, search |
| `GET /projects/{pid}/analytics/kbs/sparklines` | Lightweight per-KB daily citation counts for sparklines (trailing N days) |
| `GET /projects/{pid}/analytics/kbs/{kb_id}/items` | Per-item citation traffic for a specific KB: item_id, count, sorted by most-cited. Use to find top FAQ/article/snippet items |

### Customer Outcomes (CSAT & Conversion)

| Endpoint | Returns |
|----------|---------|
| `GET /projects/{pid}/csat/analytics` | CSAT dashboard: KPIs (CSAT/DSAT %, response rate), 1–5 rating distribution, time series, paginated ratings table with remarks. Sourced from Intercom CSAT enrichment. Filters: date range, tags, `tag_filter`, `playbook_base_id`, `max_rating` (drill-down on the table only) |
| `GET /projects/{pid}/conversion-metrics` | List all custom conversion metric definitions for a project (id, slug, name, value_label, enabled, last_event_at). Read-only — definitions are managed from the FE Enrichments view |
| `GET /projects/{pid}/conversion-metrics/{slug}` | Get a single definition + last_event_at (heartbeat) |
| `GET /projects/{pid}/conversion-metrics/{slug}/analytics` | Per-metric dashboard: total_events, total_value, avg_value, converting_conversations, eligible_conversations, conversion_rate_pct, time series, paginated events table. Filters: date range, tags, `tag_filter`, `playbook_base_id` |

> Definitions and event ingest are intentionally not exposed here — they are managed from the FE / external ingest service.

### Configuration Context

| Endpoint | Returns |
|----------|---------|
| `GET /projects/{pid}/playbooks` | All playbooks (instructions, KB links, versions) |
| `GET /playbooks/{id}` | Full playbook content |
| `GET /playbooks/{id}/history` | Version history |
| `GET /playbooks/{id}/versions/{n}` | Specific historical version |
| `GET /playbooks/{base_id}/active` | Currently active version |
| `GET /playbooks/{base_id}/active/history` | Deployment timeline |
| `GET /playbooks/{id}/settings` | Kill switch, winback, URL shortener |
| `GET /projects/{pid}/knowledgebases` | All KBs with types and status |
| `GET /knowledgebases/{id}` | Full KB content |
| `GET /knowledgebases/{id}/items/{item_id}` | Individual item metadata |
| `GET /projects/{pid}/schedule` | Office hours, timezone, overrides |
| `GET /projects/{pid}/api-tools` | Custom HTTP integrations |
| `GET /projects/{pid}/settings` | Project personality tone |

### Quality Testing

| Endpoint | Returns |
|----------|---------|
| `GET /playbooks/{base_id}/eval-cases` | Test cases for a playbook |
| `GET /playbooks/{base_id}/eval-runs` | Test run history (paginated) |
| `GET /eval-runs/{run_id}` | Full run results with per-case scores |
| `GET /playbooks/{base_id}/eval-cases/export-yaml` | All cases in YAML format |

---

## Fetching Patterns

### 1. Aggregate Overview (fast, no pagination)

```bash
# High-level totals + breakdowns
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/analytics" \
  --params start_date=2025-01-01T00:00:00Z end_date=2025-02-01T00:00:00Z \
  -o analytics.json

# Sentiment + resource quality distributions
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/metrics/aggregate" \
  --params start_date=2025-01-01T00:00:00Z end_date=2025-02-01T00:00:00Z \
  -o metrics_agg.json
```

### 2. Filtered Analytics (by playbook, tag)

```bash
# Analytics for a specific playbook (use base_id for all versions)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/analytics" \
  --params start_date=2025-01-01T00:00:00Z end_date=2025-02-01T00:00:00Z \
    playbook_base_ids=PLAYBOOK_BASE_UUID \
  -o playbook_analytics.json

# Analytics filtered by tags (AND logic)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/analytics" \
  --params start_date=2025-01-01T00:00:00Z end_date=2025-02-01T00:00:00Z \
    tags=billing,refund \
  -o billing_refund_analytics.json
```

### 3. Conversation Listing with Filters

```bash
# Only handoff conversations
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations" \
  --params start_date=2025-01-01T00:00:00Z end_date=2025-02-01T00:00:00Z \
    has_handoff=true limit=100 \
  -o handoffs.json

# Filter by sentiment (server-side, no enrichment needed)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations" \
  --params sentiment=negative limit=100 \
  -o negative_convos.json

# Filter by resource quality
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations" \
  --params resources=irrelevant limit=100 \
  -o irrelevant_resources.json

# Short conversations sorted by message count
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations" \
  --params max_messages=3 sort_by=message_count sort_order=asc limit=100 \
  -o short_convos.json

# Lightweight summaries for batch scanning
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/summaries" \
  --params sentiment=negative limit=50 \
  -o negative_summaries.json
```

### 3b. Conversation Deep Dive (single or batch)

**Note on conversation IDs:** The `conversation_id` is the **external platform ID** — the one
assigned by the messaging platform (e.g., Chatwoot, Intercom). It is NOT an internal database
primary key. This is the same ID visible in the platform UI and in webhook payloads.

```bash
# Full detail for a single conversation — metadata + messages + tool calls + citations
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/CONVERSATION_ID" \
  -o conversation_detail.json

# Batch detail for multiple conversations (up to 50) — single API call
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/batch" \
  -X POST --body '{"conversation_ids": ["conv-1", "conv-2", "conv-3"]}' \
  -o batch_detail.json
```

Each conversation in the detail response includes:
- All metadata (same as the list endpoint)
- Complete message history with all tool calls (name, arguments, results)
- Message metadata (reasoning explanation, labels, handoff info, latency)
- KB citations extracted from search tool calls

### 4. Batch Export (all conversations with metadata)

```bash
# Export all conversations — summary, sentiment, resources, skills, tags come inline
python3 scripts/export_conversations.py \
  --start 2025-01-01 --end 2025-02-01 -o all_conversations.json

# Export with full message history (slower — one call per conversation)
python3 scripts/export_conversations.py \
  --start 2025-01-01 --end 2025-02-01 --messages -o full_export.json

# Export only negative sentiment as CSV
python3 scripts/export_conversations.py \
  --start 2025-01-01 --end 2025-02-01 --sentiment negative --format csv -o negative.csv

# Export handoff conversations only
python3 scripts/export_conversations.py \
  --start 2025-01-01 --end 2025-02-01 --handoff true -o handoffs.json
```

### 5. Single Conversation Deep Dive

```bash
# Get full message history
python3 scripts/fetch.py "/projects/$STUDIO_PROJECT_ID/conversations/CONV_ID/messages" -o messages.json

# Get quality metrics
python3 scripts/fetch.py "/projects/$STUDIO_PROJECT_ID/conversations/CONV_ID/metrics" -o metrics.json

# Trigger scoring for an unscored conversation
python3 scripts/fetch.py "/projects/$STUDIO_PROJECT_ID/conversations/CONV_ID/metrics/analyze" --method POST
```

### 6. Trending Topics Analysis

```bash
# Check if analysis exists
python3 scripts/fetch.py "/projects/$STUDIO_PROJECT_ID/conversations/insights/trending-topics/status"

# Start new analysis
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations/insights/trending-topics/generate" \
  --method POST --body '{"tags": ["billing"]}'

# Poll job until complete
python3 scripts/fetch.py "/projects/$STUDIO_PROJECT_ID/conversations/insights/trending-topics/job/JOB_ID"
```

### 7. Resource Analytics — API Tools & Toolkits

```bash
# API tool usage overview (all tools)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/api-tools" \
  --params start_date=2025-01-01 end_date=2025-02-01 \
  -o api_tool_usage.json

# API tool usage for a specific tool
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/api-tools" \
  --params api_tool_id=TOOL_UUID start_date=2025-01-01 end_date=2025-02-01 \
  -o api_tool_detail.json

# API tool sparklines (lightweight, trailing 14 days by default)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/api-tools/sparklines" \
  -o api_tool_sparklines.json

# Sparklines with custom window (e.g., 30 days)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/api-tools/sparklines" \
  --params days=30 \
  -o api_tool_sparklines_30d.json

# Toolkit usage overview (all toolkits)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/toolkits" \
  --params start_date=2025-01-01 end_date=2025-02-01 \
  -o toolkit_usage.json

# Toolkit usage for a specific toolkit
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/toolkits" \
  --params toolkit_slug=TOOLKIT_SLUG start_date=2025-01-01 end_date=2025-02-01 \
  -o toolkit_detail.json

# Toolkit usage filtered by action
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/toolkits" \
  --params toolkit_slug=TOOLKIT_SLUG action_name=ACTION_NAME \
  -o toolkit_action_usage.json

# Toolkit usage with param_filter (filter by input param key:value)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/toolkits" \
  --params toolkit_slug=TOOLKIT_SLUG param_filter=ticket_type_id:67 \
  -o toolkit_param_filtered.json

# Toolkit sparklines (lightweight, trailing 14 days by default)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/toolkit-calls/sparklines" \
  -o toolkit_sparklines.json

# Search recent toolkit calls by keyword
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/toolkits" \
  --params toolkit_slug=TOOLKIT_SLUG search=error limit=20 \
  -o toolkit_errors.json
```

### 8. KB Citation Analytics

```bash
# KB citation usage overview (all KBs)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/kbs" \
  --params start_date=2025-01-01 end_date=2025-02-01 \
  -o kb_citation_usage.json

# Citation usage for a specific KB
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/kbs" \
  --params kb_id=KB_UUID start_date=2025-01-01 end_date=2025-02-01 \
  -o kb_detail.json

# Citation usage for a specific item within a KB
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/kbs" \
  --params kb_id=KB_UUID item_id=ITEM_UUID \
  -o kb_item_detail.json

# KB sparklines (lightweight, trailing 14 days by default)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/kbs/sparklines" \
  -o kb_sparklines.json

# Per-item citation traffic for a KB (top items by citation count)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/kbs/KB_UUID/items" \
  --params limit=50 \
  -o kb_item_traffic.json

# Per-item traffic filtered by date range
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/kbs/KB_UUID/items" \
  --params start_date=2025-01-01 end_date=2025-02-01 limit=10 \
  -o kb_top_items.json
```

### 9. Skill Analytics

```bash
# Skill usage overview (all skills)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/skills" \
  --params start_date=2025-01-01 end_date=2025-02-01 \
  -o skill_usage.json

# Skill usage for a specific skill
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/skills" \
  --params skill_name=refund-process start_date=2025-01-01 end_date=2025-02-01 \
  -o skill_detail.json

# Skill sparklines (lightweight, trailing 14 days by default)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/skills/sparklines" \
  -o skill_sparklines.json

# Search recent skill loads by keyword
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/skills" \
  --params search=error limit=20 \
  -o skill_errors.json
```

### 10. CSAT Analytics

CSAT is sourced from the Intercom CSAT enrichment. If the project has no config yet,
the response is `{"is_configured": false, ...}` with empty/zeroed fields — surface this
to the user as "CSAT is not configured for this project" instead of reporting 0%.

Defaults: when `start_date` / `end_date` are omitted the window is the last 7 days
ending now. Always pass the dates explicitly so the report's window is reproducible.

```bash
# CSAT dashboard payload — KPIs, distribution, time series, ratings table
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/csat/analytics" \
  --params start_date=2026-04-01T00:00:00Z end_date=2026-05-01T00:00:00Z \
  -o csat.json

# Filter to one assistant (all versions)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/csat/analytics" \
  --params start_date=2026-04-01T00:00:00Z end_date=2026-05-01T00:00:00Z \
    playbook_base_id=PLAYBOOK_BASE_UUID \
  -o csat_assistant.json

# Filter by tags (AND logic)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/csat/analytics" \
  --params start_date=2026-04-01T00:00:00Z end_date=2026-05-01T00:00:00Z \
    tags=billing,refund \
  -o csat_billing_refund.json

# Drill-down: only show 1–2 ★ ratings in the table (KPIs/time series stay unfiltered)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/csat/analytics" \
  --params start_date=2026-04-01T00:00:00Z end_date=2026-05-01T00:00:00Z \
    max_rating=2 ratings_limit=50 \
  -o csat_dsat_table.json

# Page through the ratings table
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/csat/analytics" \
  --params start_date=2026-04-01T00:00:00Z end_date=2026-05-01T00:00:00Z \
    ratings_limit=50 ratings_offset=50 \
  -o csat_page2.json
```

Key fields:

| Field | Meaning |
|-------|---------|
| `is_configured` | False when the project has no Intercom CSAT config — short-circuit the rest |
| `total_rated` | Number of conversations with a CSAT rating in the window |
| `csat_score_pct` | % of rated convos with rating in {4, 5} |
| `dsat_score_pct` | % of rated convos with rating in {1, 2} |
| `eligible_deflected` | Deflected conversations in window — denominator for `response_rate_pct` |
| `response_rate_pct` | % of eligible convos that were rated |
| `rating_distribution` | Map of `"1"…"5"` → count |
| `time_series[].csat_pct` | Per-bucket CSAT % (null when empty) |
| `time_series[].response_rate_pct` | Per-bucket response rate (null when `eligible=0`) |
| `ratings[]` | Paginated rows: `conversation_id`, `rating`, `remark`, `rated_at`, `tags`, `first_message_at` |

### 11. Conversion Metrics

Custom conversion metrics track external conversion events (e.g. sales) tied to a
conversation. Definitions and event ingest live in the FE / an upstream cron — from
the data-expert skill we only **read** them and pull analytics.

```bash
# List all custom conversion metrics for the project
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversion-metrics" \
  -o conversion_metrics.json

# Get a single definition (find its slug from the list above)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversion-metrics/SLUG" \
  -o metric_def.json

# Per-metric analytics dashboard for a date range
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversion-metrics/SLUG/analytics" \
  --params start_date=2026-04-01T00:00:00Z end_date=2026-05-01T00:00:00Z \
  -o metric_analytics.json

# Filter to one assistant
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversion-metrics/SLUG/analytics" \
  --params start_date=2026-04-01T00:00:00Z end_date=2026-05-01T00:00:00Z \
    playbook_base_id=PLAYBOOK_BASE_UUID \
  -o metric_assistant.json

# Page through the events table for a metric
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversion-metrics/SLUG/analytics" \
  --params start_date=2026-04-01T00:00:00Z end_date=2026-05-01T00:00:00Z \
    events_limit=100 events_offset=0 \
  -o metric_events.json
```

Key fields:

| Field | Meaning |
|-------|---------|
| `is_configured` | False when no metric with that slug exists — short-circuit the rest |
| `definition` | Echo of the metric definition (`name`, `slug`, `value_label`, `enabled`, `last_event_at`) |
| `total_events` | Total ingested events in the window |
| `total_value` | Sum of `value` across events (use `definition.value_label` for the unit, e.g. USD) |
| `avg_value` | Mean event value |
| `converting_conversations` | Distinct conversations with at least one event in window |
| `eligible_conversations` | Deflected conversations with `last_message_at` in window — denominator for `conversion_rate_pct` |
| `conversion_rate_pct` | `converting_conversations / eligible_conversations × 100` |
| `avg_value_per_conversation` | `total_value / converting_conversations` |
| `time_series[]` | `{date, event_count, total_value, converting_conversations}` per bucket |
| `events[]` | Paginated table rows: `conversation_id`, `value`, `occurred_at`, `metadata`, `tags` |

The `last_event_at` timestamp on the definition is the integration heartbeat — if it's
hours/days old when the upstream cron is supposed to run more often, flag it as a
likely broken ingest pipeline rather than reporting "0 conversions".

---

## Analysis Recipes

### Deflection Rate Analysis

```python
import json

with open("analytics.json") as f:
    data = json.load(f)

print(f"Total conversations: {data['total_conversations']}")
print(f"Deflection rate: {data['deflection_rate']:.1f}%")
print(f"Handoffs: {data['conversations_with_handoff']}")
print(f"AI-resolved: {data['conversations_without_handoff']}")

print("\nBy Playbook:")
for pb in data.get("by_playbook", []):
    print(f"  {pb['playbook_name']}: {pb['deflection_rate']:.1f}% deflection "
          f"({pb['total_conversations']} convs)")
```

### Sentiment Deep Dive

```python
import json

with open("metrics_agg.json") as f:
    agg = json.load(f)

total_scored = agg["total_scored_conversations"]
sent = agg["sentiment_distribution"]

print(f"Scored: {total_scored}/{agg['total_conversations']} ({agg['coverage_percentage']:.1f}% coverage)")
print(f"\nSentiment:")
for label in ["positive", "neutral", "negative"]:
    count = sent.get(label, 0)
    pct = (count / total_scored * 100) if total_scored else 0
    print(f"  {label}: {count} ({pct:.1f}%)")
```

### Conversation Signal Analysis

```python
import json

with open("metrics_agg.json") as f:
    agg = json.load(f)

total = agg["total_scored_conversations"]

# Deflection quality — how well bot-resolved conversations actually went
defl = agg.get("deflection_quality_distribution", {})
print("Deflection Quality:")
for label in ["resolved", "partial", "actioned", "no_response"]:
    count = defl.get(label, 0)
    pct = (count / total * 100) if total else 0
    print(f"  {label}: {count} ({pct:.1f}%)")

# Handoff reasons — why conversations were escalated
ho = agg.get("handoff_reason_distribution", {})
print("\nHandoff Reasons:")
for label in ["policy", "user_request", "frustration", "bot_limitation"]:
    count = ho.get(label, 0)
    pct = (count / total * 100) if total else 0
    print(f"  {label}: {count} ({pct:.1f}%)")

# Recontact risk — likelihood of customer returning
risk = agg.get("recontact_risk_distribution", {})
print("\nRecontact Risk:")
for label in ["low", "medium", "high"]:
    count = risk.get(label, 0)
    pct = (count / total * 100) if total else 0
    print(f"  {label}: {count} ({pct:.1f}%)")

# Sentiment shift — did the bot make things better or worse?
shift = agg.get("sentiment_shift_distribution", {})
print("\nSentiment Shift:")
for label in ["improved", "stable", "degraded"]:
    count = shift.get(label, 0)
    pct = (count / total * 100) if total else 0
    print(f"  {label}: {count} ({pct:.1f}%)")
```

### API Tool Usage Analysis

```python
import json

with open("api_tool_usage.json") as f:
    data = json.load(f)

print(f"Total calls: {data['total_calls']}")
print(f"Success: {data['successful_calls']} | Failed: {data['failed_calls']}")
if data['avg_duration_ms']:
    print(f"Avg duration: {data['avg_duration_ms']:.0f}ms")

success_rate = (data['successful_calls'] / data['total_calls'] * 100) if data['total_calls'] else 0
print(f"Success rate: {success_rate:.1f}%")

print("\nDaily trend:")
for pt in data.get("time_series", []):
    print(f"  {pt['date']}: {pt['count']} calls ({pt['success_count']} ok)")
```

### Toolkit Action Breakdown

```python
import json

with open("toolkit_usage.json") as f:
    data = json.load(f)

print(f"Total calls: {data['total_calls']}")
print(f"Success: {data['successful_calls']} | Failed: {data['failed_calls']}")

print("\nBy Action:")
for action in data.get("by_action", []):
    rate = (action['success_count'] / action['count'] * 100) if action['count'] else 0
    print(f"  {action['action_name']}: {action['count']} calls ({rate:.0f}% success)")

print("\nRecent failures:")
for item in data.get("recent", []):
    if not item['success']:
        print(f"  [{item['created_at']}] {item['action_name']}: {item.get('error_message', 'unknown')}")
```

### Skill Usage Analysis

```python
import json

with open("skill_usage.json") as f:
    data = json.load(f)

print(f"Total skill loads: {data['total_calls']}")
print(f"Success: {data['successful_calls']} | Failed: {data['failed_calls']}")

success_rate = (data['successful_calls'] / data['total_calls'] * 100) if data['total_calls'] else 0
print(f"Success rate: {success_rate:.1f}%")

print("\nRecent loads:")
for item in data.get("recent", []):
    status = "ok" if item['success'] else f"FAIL: {item.get('error_message', 'unknown')}"
    print(f"  [{item['created_at']}] {item['skill_name']}: {status}")
```

### KB Citation & Top Items Analysis

```python
import json

# Step 1: List all KBs to get names
with open("kbs.json") as f:
    kbs = json.load(f)
kb_names = {kb["id"]: kb["title"] for kb in kbs}

# Step 2: Get per-item traffic for a specific KB
with open("kb_item_traffic.json") as f:
    data = json.load(f)

print(f"Top {data['total_items_cited']} cited items:")
for item in data["items"]:
    print(f"  {item['item_id']}: {item['count']} citations")

# Step 3: Resolve item names by fetching item metadata
# For each item_id, call GET /knowledgebases/{kb_id}/items/{item_id}
# to get item_type, title, and url
```

**Common query: "Top 10 most cited Intercom articles"**

```bash
# 1. Find the Intercom KB id
python3 scripts/fetch.py "/projects/$STUDIO_PROJECT_ID/knowledgebases" -o kbs.json
# Look for kb_type=intercom in the output

# 2. Get top items by citation count
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/analytics/kbs/INTERCOM_KB_ID/items" \
  --params limit=10 \
  -o top_intercom_items.json

# 3. Resolve item titles
python3 scripts/fetch.py "/knowledgebases/INTERCOM_KB_ID" -o intercom_kb.json
```

```python
import json

with open("top_intercom_items.json") as f:
    traffic = json.load(f)

with open("intercom_kb.json") as f:
    kb = json.load(f)

# Build item_id -> title lookup from intercom_items
item_titles = {item["id"]: item["title"] for item in kb.get("intercom_items", [])}

print("Top 10 most cited Intercom articles:")
for i, entry in enumerate(traffic["items"][:10], 1):
    title = item_titles.get(entry["item_id"], entry["item_id"])
    print(f"  {i}. {title} — {entry['count']} citations")
```

### Sparkline Overview (All Resources at a Glance)

```python
import json

with open("api_tool_sparklines.json") as f:
    sparklines = json.load(f)

print("API Tool activity (last 14 days):")
for tool_id, item in sorted(sparklines.items(), key=lambda x: x[1]['total'], reverse=True):
    trend = " ".join(str(pt['count']) for pt in item['series'][-7:])
    print(f"  {tool_id}: {item['total']} total | last 7d: [{trend}]")

with open("toolkit_sparklines.json") as f:
    sparklines = json.load(f)

print("\nToolkit activity (last 14 days):")
for slug, item in sorted(sparklines.items(), key=lambda x: x[1]['total'], reverse=True):
    trend = " ".join(str(pt['count']) for pt in item['series'][-7:])
    print(f"  {slug}: {item['total']} total | last 7d: [{trend}]")

with open("skill_sparklines.json") as f:
    sparklines = json.load(f)

print("\nSkill activity (last 14 days):")
for name, item in sorted(sparklines.items(), key=lambda x: x[1]['total'], reverse=True):
    trend = " ".join(str(pt['count']) for pt in item['series'][-7:])
    print(f"  {name}: {item['total']} total | last 7d: [{trend}]")
```

### Conversation Metadata Analysis (inline fields)

```python
import json

# All metadata comes inline — no separate enrichment calls needed
with open("all_conversations.json") as f:
    data = json.load(f)

convs = data["conversations"]
print(f"Total: {len(convs)} conversations\n")

# Sentiment breakdown (from inline sentiment_label)
sentiments = {}
for c in convs:
    label = c.get("sentiment_label") or "unscored"
    sentiments[label] = sentiments.get(label, 0) + 1
print("Sentiment:")
for label, count in sorted(sentiments.items()):
    print(f"  {label}: {count}")

# Skills usage (from inline skills field)
skill_counts = {}
for c in convs:
    for skill in c.get("skills") or []:
        skill_counts[skill] = skill_counts.get(skill, 0) + 1
print("\nSkills loaded:")
for skill, count in sorted(skill_counts.items(), key=lambda x: -x[1]):
    print(f"  {skill}: {count} conversations")

# Handoff conversations with negative sentiment
bad_handoffs = [c for c in convs if c.get("has_handoff") and c.get("sentiment_label") == "negative"]
print(f"\nNegative handoffs: {len(bad_handoffs)}")
for c in bad_handoffs[:5]:
    print(f"  [{c['conversation_id']}] {c.get('summary', 'no summary')[:80]}")

# Deflection quality breakdown (non-handoff only)
defl_counts = {}
for c in convs:
    dq = c.get("deflection_quality")
    if dq:
        defl_counts[dq] = defl_counts.get(dq, 0) + 1
print("\nDeflection Quality:")
for label, count in sorted(defl_counts.items()):
    print(f"  {label}: {count}")

# Handoff reasons (handoff only)
ho_counts = {}
for c in convs:
    hr = c.get("handoff_reason")
    if hr:
        ho_counts[hr] = ho_counts.get(hr, 0) + 1
print("\nHandoff Reasons:")
for label, count in sorted(ho_counts.items()):
    print(f"  {label}: {count}")

# High recontact risk conversations
high_risk = [c for c in convs if c.get("recontact_risk") == "high"]
print(f"\nHigh recontact risk: {len(high_risk)}")
for c in high_risk[:5]:
    print(f"  [{c['conversation_id']}] {c.get('user_intent', 'no intent')}: {c.get('recontact_risk_reason', '')[:80]}")
```

### CSAT Score & Distribution

```python
import json

with open("csat.json") as f:
    csat = json.load(f)

if not csat["is_configured"]:
    print("CSAT is not configured for this project — skipping.")
else:
    print(f"Rated conversations: {csat['total_rated']}")
    print(f"CSAT (4–5 ★): {csat['csat_score_pct']:.1f}%")
    print(f"DSAT (1–2 ★): {csat['dsat_score_pct']:.1f}%")
    print(f"Response rate: {csat['response_rate_pct']:.1f}% "
          f"({csat['total_rated']}/{csat['eligible_deflected']} eligible)")

    print("\nRating distribution:")
    dist = csat["rating_distribution"]
    for r in ["5", "4", "3", "2", "1"]:
        count = dist.get(r, 0)
        pct = (count / csat["total_rated"] * 100) if csat["total_rated"] else 0
        bar = "█" * int(pct / 2)
        print(f"  {r}★: {count:>4} ({pct:5.1f}%) {bar}")

    # Daily CSAT trend
    print("\nDaily CSAT % (skipping empty buckets):")
    for pt in csat["time_series"]:
        if pt["csat_pct"] is None:
            continue
        print(f"  {pt['date']}: {pt['csat_pct']:5.1f}% over {pt['total']} ratings")
```

### DSAT Drill-Down (low-rating remarks)

When CSAT looks bad, the cheapest explanation usually lives in the verbatim remarks
attached to 1–2 ★ ratings. Pull them with `max_rating=2` and group by tag.

```python
import json
from collections import Counter

with open("csat_dsat_table.json") as f:
    csat = json.load(f)

ratings = csat["ratings"]
print(f"Showing {len(ratings)} of {csat['total_rated']} low-rating reviews\n")

tag_counts = Counter()
for r in ratings:
    for t in r.get("tags") or []:
        tag_counts[t] += 1

print("Top tags among 1–2★ ratings:")
for tag, count in tag_counts.most_common(10):
    print(f"  {tag}: {count}")

print("\nRecent verbatims (with remark):")
for r in ratings[:15]:
    if not r.get("remark"):
        continue
    print(f"  [{r['conversation_id']}] {r['rating']}★: {r['remark'][:140]}")
```

### Conversion Metric — Topline + Trend

```python
import json

with open("metric_analytics.json") as f:
    m = json.load(f)

if not m["is_configured"]:
    print("Metric not found — check the slug.")
else:
    defn = m["definition"]
    unit = defn["value_label"]
    print(f"Metric: {defn['name']} (slug={defn['slug']})")
    if defn.get("last_event_at"):
        print(f"Last event ingested: {defn['last_event_at']}")

    print(f"\nEvents: {m['total_events']}")
    print(f"Total value: {m['total_value']:.2f} {unit}")
    print(f"Avg value: {m['avg_value']:.2f} {unit}")
    print(f"Converting conversations: {m['converting_conversations']}")
    print(f"Eligible (deflected) conversations: {m['eligible_conversations']}")
    print(f"Conversion rate: {m['conversion_rate_pct']:.2f}%")
    print(f"Avg value per converting convo: {m['avg_value_per_conversation']:.2f} {unit}")

    print("\nDaily trend:")
    for pt in m["time_series"]:
        print(f"  {pt['date']}: {pt['event_count']} events, "
              f"{pt['total_value']:.2f} {unit}, "
              f"{pt['converting_conversations']} convos")
```

### Conversion Funnel by Assistant

To compare conversion across assistants, fetch the per-metric analytics once per
`playbook_base_id` and tabulate the rates side-by-side. The list of bases comes
from `GET /projects/{pid}/playbooks`.

```python
import json
import subprocess

with open("playbooks.json") as f:
    playbooks = json.load(f)

bases = {pb["base_id"]: pb["name"] for pb in playbooks}

rows = []
for base_id, name in bases.items():
    out = f"metric_{base_id}.json"
    subprocess.run([
        "python3", "scripts/fetch.py",
        f"/projects/{__import__('os').environ['STUDIO_PROJECT_ID']}/conversion-metrics/SLUG/analytics",
        "--params",
        "start_date=2026-04-01T00:00:00Z",
        "end_date=2026-05-01T00:00:00Z",
        f"playbook_base_id={base_id}",
        "-o", out,
    ], check=True)
    with open(out) as f:
        m = json.load(f)
    if not m["is_configured"]:
        continue
    rows.append({
        "assistant": name,
        "eligible": m["eligible_conversations"],
        "converting": m["converting_conversations"],
        "rate": m["conversion_rate_pct"],
        "value": m["total_value"],
    })

rows.sort(key=lambda r: r["rate"], reverse=True)
print(f"{'Assistant':<30} {'Eligible':>10} {'Convert':>10} {'Rate':>8} {'Value':>12}")
for r in rows:
    print(f"{r['assistant']:<30} {r['eligible']:>10} {r['converting']:>10} "
          f"{r['rate']:>7.2f}% {r['value']:>12.2f}")
```

---

## Reference

### Query Dimensions

Every conversation query supports these filter dimensions. All filters are server-side — no client-side post-filtering needed.

| Dimension | Parameter | Type | Logic | Example |
|-----------|-----------|------|-------|---------|
| **Date range** | `start_date`, `end_date` | ISO 8601 string | Range on `last_message_at` | `start_date=2025-01-01T00:00:00Z` |
| **Assistant / Playbook (version)** | `playbook_id` | UUID | Exact match on specific version | `playbook_id=abc-123` |
| **Assistant / Playbook (all versions)** | `playbook_base_id` | UUID | All versions of an assistant | `playbook_base_id=def-456` |
| **Inbox / Channel** | `inbox_id` | UUID | Exact match (Website, WhatsApp, etc.) | `inbox_id=inbox-789` |
| **Handoff** | `has_handoff` | bool | `true` = escalated, `false` = AI-resolved | `has_handoff=true` |
| **Winback** | `has_winback` | bool | `true` = winback sent, `false` = not sent | `has_winback=true` |
| **Tags** | `tags` | comma-separated | **AND** logic — must have ALL tags | `tags=billing,refund` |
| **Sentiment** | `sentiment` | comma-separated | **OR** logic — any of the values | `sentiment=negative,neutral` |
| **Resources** | `resources` | comma-separated | **OR** logic — any of the values | `resources=irrelevant,partial` |
| **Sentiment Shift** | `sentiment_shift` | comma-separated | **OR** logic | `sentiment_shift=degraded` |
| **Deflection Quality** | `deflection_quality` | comma-separated | **OR** logic (non-handoff only) | `deflection_quality=actioned,no_response` |
| **Handoff Reason** | `handoff_reason` | comma-separated | **OR** logic (handoff only) | `handoff_reason=frustration,bot_limitation` |
| **Recontact Risk** | `recontact_risk` | comma-separated | **OR** logic | `recontact_risk=high` |
| **Message count** | `min_messages`, `max_messages` | int | Range filter | `min_messages=5&max_messages=20` |
| **Skill** | `skill_name` | string | Conversations that loaded this skill | `skill_name=refund-process` |
| **Search** | `search` | string | Substring match on conversation ID | `search=12345` |
| **Exact IDs** | `conversation_ids` | list (POST body) | Exact match on a list of IDs | Used by batch endpoint |

### Sorting

| Parameter | Values | Default |
|-----------|--------|---------|
| `sort_by` | `last_message_at`, `first_message_at`, `message_count` | `last_message_at` |
| `sort_order` | `desc`, `asc` | `desc` |

### Date Ranges & Timezones

Always scope queries with `start_date` and `end_date` in ISO 8601 format.

**Timezone handling:**
- **UTC is the default.** If no timezone offset is provided, the timestamp is treated as UTC.
- **Timezone-aware timestamps are supported.** You can pass any valid ISO 8601 offset.
- The `export_conversations.py` script accepts short form dates and appends `T00:00:00Z` (UTC).

| Format | Example | Timezone |
|--------|---------|----------|
| Full UTC | `2025-01-01T00:00:00Z` | UTC |
| With offset | `2025-01-01T00:00:00-03:00` | ART (Argentina) |
| With offset | `2025-01-01T00:00:00-05:00` | EST |
| Short form (scripts) | `2025-01-01` | Converted to `2025-01-01T00:00:00Z` (UTC) |

**Important:** Date filters apply to `last_message_at` (last activity in the conversation), not the creation time. This ensures the filter matches what's displayed in the UI.

### Metric Labels

| Type | Values | Meaning |
|------|--------|---------|
| Sentiment | `negative`, `neutral`, `positive` | Customer emotional state (LLM-scored) |
| Resources | `irrelevant`, `partial`, `relevant` | How well KBs/tools served the conversation |
| Sentiment Shift | `improved`, `stable`, `degraded` | How sentiment changed during conversation |
| Deflection Quality | `resolved`, `partial`, `actioned`, `no_response` | Resolution quality for non-handoff conversations |
| Handoff Reason | `policy`, `user_request`, `frustration`, `bot_limitation` | Why conversation was escalated (handoff only) |
| Recontact Risk | `low`, `medium`, `high` | Likelihood of user returning with same issue |

**Conditional signals:**
- `deflection_quality` is only present when `has_handoff=false` (bot-resolved conversations)
- `handoff_reason` is only present when `has_handoff=true` (escalated conversations)
- `resources` is only present when tool calls were used in the conversation
- All other signals (sentiment, sentiment_shift, recontact_risk, user_intent, summary) are always present when scored

**Free text signals:**
- `user_intent` — short phrase describing what the user wanted (e.g., "cancel subscription", "pricing for enterprise plan")
- `summary` — 2-3 sentence summary of the full conversation flow including tools/KBs used

### Deflection Rate

`deflection_rate = conversations_without_handoff / total_conversations x 100`

Higher = better (more conversations resolved by AI without human escalation).

### Combining Dimensions

All filters can be combined. Examples:

```bash
# Negative sentiment conversations that used the refund skill in January
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations" \
  --params start_date=2025-01-01T00:00:00Z end_date=2025-02-01T00:00:00Z \
    sentiment=negative skill_name=refund-process limit=100 \
  -o negative_refund.json

# Handoff conversations with billing tag, sorted by message count
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations" \
  --params has_handoff=true tags=billing sort_by=message_count sort_order=desc \
  -o billing_handoffs.json

# Long conversations (10+ messages) with irrelevant resources
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations" \
  --params min_messages=10 resources=irrelevant limit=50 \
  -o long_irrelevant.json

# Conversations where bot created a follow-up action (ticket, email, etc.)
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations" \
  --params deflection_quality=actioned limit=100 \
  -o actioned.json

# Handoffs caused by frustration
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations" \
  --params handoff_reason=frustration limit=100 \
  -o frustration_handoffs.json

# High recontact risk conversations
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations" \
  --params recontact_risk=high limit=100 \
  -o high_risk.json

# Conversations where sentiment degraded
python3 scripts/fetch.py \
  "/projects/$STUDIO_PROJECT_ID/conversations" \
  --params sentiment_shift=degraded limit=100 \
  -o degraded.json
```
