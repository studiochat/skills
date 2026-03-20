#!/usr/bin/env python3
"""Reports API client for Studio Chat.

Manage report definitions, trigger runs, and check results.

Usage:
    reports.py list
    reports.py get <report_id>
    reports.py create --name NAME --instructions INSTR [options]
    reports.py update <report_id> [options]
    reports.py delete <report_id>
    reports.py run <report_id> [--window N]
    reports.py runs <report_id> [--limit N]
    reports.py run-status <run_id>
    reports.py artifact <run_id>
    reports.py playbooks

Examples:
    # List all reports
    reports.py list

    # Create a manual report for one playbook
    reports.py create --name "Daily CX" \
      --instructions "Analyze conversations. Show deflection rate, sentiment, top topics." \
      --playbooks abc-123 --window 1

    # Create a weekly scheduled report with Slack delivery
    reports.py create --name "Weekly Summary" \
      --instructions "Full weekly analysis with recommendations." \
      --schedule cron --cron "0 12 * * 1" \
      --playbooks abc-123,def-456 --slack "#reports"

    # Trigger a run
    reports.py run REPORT_ID --window 3

    # Check run status and logs
    reports.py run-status RUN_ID

    # List available playbooks (to get base_ids)
    reports.py playbooks
"""

import argparse
import json
import os
import sys
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError


API_URL = os.environ.get("STUDIO_API_URL", "https://api.studiochat.io")
API_TOKEN = os.environ.get("STUDIO_API_TOKEN", "")
PROJECT_ID = os.environ.get("STUDIO_PROJECT_ID", "")


def _request(method, path, body=None, params=None):
    """Make an authenticated API request."""
    url = urljoin(API_URL.rstrip("/") + "/", path.lstrip("/"))
    if params:
        url += "?" + urlencode(params)

    headers = {"Content-Type": "application/json"}
    if API_TOKEN.startswith("sbs_") or API_TOKEN.startswith("kps_"):
        headers["X-API-Key"] = API_TOKEN
    else:
        headers["Authorization"] = f"Bearer {API_TOKEN}"

    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, headers=headers, method=method)

    try:
        with urlopen(req) as resp:
            if resp.status == 204:
                return None
            return json.loads(resp.read().decode())
    except HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"Error {e.code}: {body_text}", file=sys.stderr)
        sys.exit(1)


def _print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_list():
    result = _request("GET", f"/projects/{PROJECT_ID}/reports")
    reports = result.get("items", [])
    if not reports:
        print("No reports found.")
        return
    for r in reports:
        schedule = r.get("cron_expression") or "manual"
        slack = f" → {r['slack_channel']}" if r.get("slack_channel") else ""
        last_run = r.get("last_run_at") or "never"
        print(f"  {r['id'][:8]}  {r['name']:<30} {schedule:<20} last_run={last_run}{slack}")


def cmd_get(report_id):
    _print_json(_request("GET", f"/reports/{report_id}"))


def cmd_create(args):
    body = {
        "name": args.name,
        "instructions": args.instructions,
        "schedule_type": args.schedule or "manual",
    }
    if args.cron:
        body["cron_expression"] = args.cron
    if args.playbooks:
        body["playbook_base_ids"] = [p.strip() for p in args.playbooks.split(",")]
    if args.window is not None:
        body["time_window_days"] = args.window
    if args.slack:
        body["slack_channel"] = args.slack

    result = _request("POST", f"/projects/{PROJECT_ID}/reports", body=body)
    print(f"Created report: {result['id']}")
    _print_json(result)


def cmd_update(report_id, args):
    body = {}
    if args.name:
        body["name"] = args.name
    if args.instructions:
        body["instructions"] = args.instructions
    if args.schedule:
        body["schedule_type"] = args.schedule
    if args.cron:
        body["cron_expression"] = args.cron
    if args.playbooks:
        body["playbook_base_ids"] = [p.strip() for p in args.playbooks.split(",")]
    if args.window is not None:
        body["time_window_days"] = args.window
    if args.slack:
        body["slack_channel"] = args.slack
    if args.remove_slack:
        body["slack_channel"] = None

    if not body:
        print("Nothing to update.", file=sys.stderr)
        sys.exit(1)

    result = _request("PATCH", f"/reports/{report_id}", body=body)
    print(f"Updated report: {result['id']}")
    _print_json(result)


def cmd_delete(report_id):
    _request("DELETE", f"/reports/{report_id}")
    print(f"Deleted report: {report_id}")


def cmd_run(report_id, window=None):
    body = {"time_window_days": window} if window else None
    result = _request("POST", f"/reports/{report_id}/run", body=body)
    print(f"Run triggered: {result['id']} (status: {result['status']})")


def cmd_runs(report_id, limit=10):
    result = _request("GET", f"/reports/{report_id}/runs", params={"limit": limit})
    runs = result.get("items", [])
    if not runs:
        print("No runs found.")
        return
    for r in runs:
        duration = ""
        if r.get("started_at") and r.get("completed_at"):
            from datetime import datetime
            s = datetime.fromisoformat(r["started_at"].replace("Z", "+00:00"))
            e = datetime.fromisoformat(r["completed_at"].replace("Z", "+00:00"))
            duration = f" ({int((e - s).total_seconds())}s)"
        print(f"  {r['id'][:8]}  {r['status']:<25} {r.get('trigger_type', ''):<10} {r.get('started_at', '-')}{duration}")


def cmd_run_status(run_id):
    result = _request("GET", f"/reports/runs/{run_id}")
    print(f"Status: {result['status']}")
    logs = result.get("execution_log") or []
    if logs:
        print("\nExecution log:")
        for entry in logs:
            print(f"  {entry['ts'][:19]}  [{entry['step']}] {entry.get('detail', '')}")
    if result.get("error_message"):
        print(f"\nError: {result['error_message']}")


def cmd_artifact(run_id):
    result = _request("GET", f"/reports/runs/{run_id}/artifact")
    # Try to pretty-print if it's JSON
    try:
        doc = json.loads(result.get("markdown_content", ""))
        _print_json(doc)
    except (json.JSONDecodeError, TypeError):
        print(result.get("markdown_content", ""))


def cmd_playbooks():
    result = _request("GET", f"/projects/{PROJECT_ID}/playbooks")
    if not result:
        print("No playbooks found.")
        return
    for pb in result:
        print(f"  {pb['base_id']}  {pb['name']}")


def main():
    parser = argparse.ArgumentParser(description="Studio Chat Reports API client")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all reports")

    p_get = sub.add_parser("get", help="Get report details")
    p_get.add_argument("report_id")

    p_create = sub.add_parser("create", help="Create a report")
    p_create.add_argument("--name", required=True)
    p_create.add_argument("--instructions", required=True)
    p_create.add_argument("--schedule", choices=["manual", "cron"], default="manual")
    p_create.add_argument("--cron", help="Cron expression (min 30 min interval)")
    p_create.add_argument("--playbooks", help="Comma-separated playbook base_ids")
    p_create.add_argument("--window", type=int, help="Time window in days")
    p_create.add_argument("--slack", help="Slack channel for PDF delivery (e.g. #reports)")

    p_update = sub.add_parser("update", help="Update a report")
    p_update.add_argument("report_id")
    p_update.add_argument("--name")
    p_update.add_argument("--instructions")
    p_update.add_argument("--schedule", choices=["manual", "cron"])
    p_update.add_argument("--cron")
    p_update.add_argument("--playbooks")
    p_update.add_argument("--window", type=int)
    p_update.add_argument("--slack", help="Slack channel (e.g. #reports)")
    p_update.add_argument("--remove-slack", action="store_true", help="Remove Slack delivery")

    p_delete = sub.add_parser("delete", help="Delete a report (requires approval)")
    p_delete.add_argument("report_id")

    p_run = sub.add_parser("run", help="Trigger a manual run")
    p_run.add_argument("report_id")
    p_run.add_argument("--window", type=int, help="Override time window (days)")

    p_runs = sub.add_parser("runs", help="List runs for a report")
    p_runs.add_argument("report_id")
    p_runs.add_argument("--limit", type=int, default=10)

    p_status = sub.add_parser("run-status", help="Get run status and logs")
    p_status.add_argument("run_id")

    p_artifact = sub.add_parser("artifact", help="Get report artifact")
    p_artifact.add_argument("run_id")

    sub.add_parser("playbooks", help="List available playbooks")

    args = parser.parse_args()

    if not API_TOKEN:
        print("Error: STUDIO_API_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    if not PROJECT_ID and args.command in ("list", "create", "playbooks"):
        print("Error: STUDIO_PROJECT_ID not set", file=sys.stderr)
        sys.exit(1)

    if args.command == "list":
        cmd_list()
    elif args.command == "get":
        cmd_get(args.report_id)
    elif args.command == "create":
        cmd_create(args)
    elif args.command == "update":
        cmd_update(args.report_id, args)
    elif args.command == "delete":
        cmd_delete(args.report_id)
    elif args.command == "run":
        cmd_run(args.report_id, args.window)
    elif args.command == "runs":
        cmd_runs(args.report_id, args.limit)
    elif args.command == "run-status":
        cmd_run_status(args.run_id)
    elif args.command == "artifact":
        cmd_artifact(args.run_id)
    elif args.command == "playbooks":
        cmd_playbooks()


if __name__ == "__main__":
    main()
