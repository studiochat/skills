# Reports API Reference

Base URL: `$STUDIO_API_URL` (env var, defaults to `https://api.studiochat.io`)
Auth: `Authorization: Bearer $STUDIO_API_TOKEN`

## Report Definitions

### Create Report
```
POST /projects/{project_id}/reports
```
Body:
```json
{
  "name": "Weekly Report",
  "instructions": "Analyze conversations...",
  "schedule_type": "manual",
  "cron_expression": null,
  "playbook_base_ids": ["uuid1", "uuid2"],
  "time_window_days": 7,
  "slack_channel": "#reports",
  "email_recipients": ["user@company.com"]
}
```
Returns: `201` with report definition.

### List Reports
```
GET /projects/{project_id}/reports?include_one_off=false
```
Returns: `{ "items": [...], "total": N }`

One-off reports are hidden by default (they are not part of the project's report catalog).
Pass `include_one_off=true` to see them.

### Get Report
```
GET /reports/{report_id}
```

### Update Report
```
PATCH /reports/{report_id}
```
Body: any subset of create fields.

### Delete Report (soft delete)
```
DELETE /reports/{report_id}
```
Returns: `204`. **Immediate — not approval-gated**, including for `sbs_` keys.

## Report Runs

### Trigger Manual Run
```
POST /reports/{report_id}/run
```
Optional body:
```json
{ "time_window_days": 7 }
```
- Manual reports: uses body value, falls back to definition default, then 7
- Cron reports: auto-calculated from cron interval (body ignored)

Returns: `202` with run object (status: pending).

### One-off report (define and run in one call)
```
POST /projects/{project_id}/reports/one-off
```
```json
{
  "instructions": "What came in over the last 24 hours, and why did it hand off?",
  "name": "Optional label",
  "playbook_base_ids": ["base_id_1"],
  "time_window_hours": 24
}
```

For the question asked in a thread that wants the report **pipeline** (Sami, the Block Kit
artifact, the branded PDF) and none of the report **lifecycle**. The definition is written with
`is_one_off=true`: it never appears in the project's report list, has no schedule and no
delivery target, and exists only so the run, the artifact and the cost line have something to
point at.

| Field | Type | Description |
|-------|------|-------------|
| `instructions` | string | **Required**, non-empty |
| `name` | string | Optional label (max 255) |
| `playbook_base_ids` | array | Which assistants to include |
| `time_window_days` | int | 1–366 |
| `time_window_hours` | int | 1–744. Exists because "the last 24 hours" is what a person actually asks for |

Pass **one** of `time_window_days` / `time_window_hours`, or neither (defaults to 7 days).
Sending both is a `400`.

Returns `202` with `{report, run}`. Poll the run, then collect the PDF from
`/reports/runs/{run_id}/pdf`.

Same executor, same per-run cost cap and same foreground session as a manual "Run now" — the
only thing this route adds is not having to create, run, and remember to delete.

### Retry a failed run
```
POST /reports/runs/{run_id}/retry
```
Re-runs with the **same** `window_start` / `window_end`. Returns `202`.

Only runs with status `failed` can be retried — anything else is a `400`.

### Cancel an in-flight run
```
POST /reports/runs/{run_id}/cancel
```
Allowed only while the run is `pending` or `running`.

The cancel sends `user.interrupt` and archives the upstream session **before** marking the run
cancelled. If either upstream call fails the endpoint answers `502` rather than misleadingly
reporting the run as cancelled — offer a retry in that case.

### List Runs
```
GET /reports/{report_id}/runs?limit=50&offset=0
```
Returns: `{ "items": [...], "total": N }`

### Get Run
```
GET /reports/runs/{run_id}
```
Response includes `execution_log`: array of `{ ts, step, detail }` entries.

Steps: `started`, `creating_sandbox`, `sandbox_ready`, `executing`, `tool_call`, `tool_error`, `reading_output`, `output_parsed`, `output_invalid`, `fallback`, `completed`, `slack_sending`, `slack_sent`, `slack_failed`, `failed`, `cleanup`

### Get Artifact
```
GET /reports/runs/{run_id}/artifact
```
Returns: `{ "id", "run_id", "markdown_content" }` — `markdown_content` is the Block Kit JSON string.

### Download PDF
```
GET /reports/runs/{run_id}/pdf
```
Returns: PDF binary (`application/pdf`).

## Report Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Created, not yet started |
| `running` | Sandbox active, SAMI executing |
| `completed` | Report generated and artifact stored |
| `completed_with_warnings` | Report generated, but Slack delivery failed |
| `failed` | Execution error |

## Playbooks (for discovery)

To list available playbooks (needed for `playbook_base_ids`):
```
GET /projects/{project_id}/playbooks
```
Each playbook has `base_id` (stable across versions) and `name`.
