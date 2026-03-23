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
GET /projects/{project_id}/reports
```
Returns: `{ "items": [...], "total": N }`

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
Returns: `204`

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
