#!/usr/bin/env python3
"""Quality engineering CLI for Studio Chat eval system.

Manages test cases, triggers eval runs, reads results, and simulates
conversations with playbook assistants.

Usage:
    qa.py cases list PLAYBOOK_BASE_ID
    qa.py cases create PLAYBOOK_BASE_ID --body '{...}'
    qa.py cases batch PLAYBOOK_BASE_ID --body '{"cases": [...]}'
    qa.py cases get CASE_ID
    qa.py cases update CASE_ID --body '{...}'
    qa.py cases delete CASE_ID
    qa.py runs create PLAYBOOK_BASE_ID --playbook-id ID [--context '{}']
    qa.py runs list PLAYBOOK_BASE_ID [--page N] [--page-size N]
    qa.py runs status RUN_ID
    qa.py runs results RUN_ID [-o file.json]
    qa.py runs cancel RUN_ID
    qa.py chat PLAYBOOK_BASE_ID --message "text" [--conversation-id ID] [--context '{}']
"""

import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlencode, urljoin


BASE_URL = "https://api.studiochat.io"


def _request(method, path, body=None, params=None):
    """Make an authenticated API request."""
    token = os.environ.get("STUDIO_API_TOKEN")
    if not token:
        print("Error: STUDIO_API_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    url = urljoin(BASE_URL.rstrip("/") + "/", path.lstrip("/"))
    if params:
        url = f"{url}?{urlencode(params)}"

    headers = {"Content-Type": "application/json"}
    if token.startswith(("sbs_", "kps_")):
        headers["X-API-Key"] = token
    else:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, headers=headers, method=method, data=data)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            if resp.status == 204:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        try:
            error_json = json.loads(error_body)
            detail = error_json.get("detail", error_body)
        except (json.JSONDecodeError, TypeError):
            detail = error_body
        print(f"Error {e.code}: {detail}", file=sys.stderr)
        sys.exit(1)


def _print_json(data):
    """Pretty-print JSON to stdout."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _write_output(data, output_path):
    """Write JSON to file or stdout."""
    if output_path:
        content = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        with open(output_path, "w") as f:
            f.write(content)
        print(f"Written to {output_path} ({len(content):,} bytes)", file=sys.stderr)
    else:
        _print_json(data)


# === Cases ===


def cmd_cases_list(base_id, enabled_only=False):
    params = {"enabled_only": "true"} if enabled_only else {}
    data = _request("GET", f"/playbooks/{base_id}/eval-cases", params=params)
    _print_json(data)


def cmd_cases_create(base_id, body):
    data = _request("POST", f"/playbooks/{base_id}/eval-cases", body=body)
    _print_json(data)


def cmd_cases_batch(base_id, body):
    data = _request("POST", f"/playbooks/{base_id}/eval-cases/batch", body=body)
    print(f"Created {len(data)} test cases", file=sys.stderr)
    _print_json(data)


def cmd_cases_get(case_id):
    data = _request("GET", f"/eval-cases/{case_id}")
    _print_json(data)


def cmd_cases_update(case_id, body):
    data = _request("PATCH", f"/eval-cases/{case_id}", body=body)
    _print_json(data)


def cmd_cases_delete(case_id):
    _request("DELETE", f"/eval-cases/{case_id}")
    print(f"Deleted case {case_id}", file=sys.stderr)


# === Runs ===


def cmd_runs_create(base_id, playbook_id, context=None):
    body = {"playbook_id": playbook_id}
    if context:
        body["user_context"] = context
    data = _request("POST", f"/playbooks/{base_id}/eval-runs", body=body)
    print(f"Run started: {data['id']} (status: {data['status']})", file=sys.stderr)
    _print_json(data)


def cmd_runs_list(base_id, page=1, page_size=10):
    params = {"page": page, "page_size": page_size}
    data = _request("GET", f"/playbooks/{base_id}/eval-runs", params=params)
    _print_json(data)


def cmd_runs_status(run_id):
    data = _request("GET", f"/eval-runs/{run_id}")
    _print_json(data)


def cmd_runs_results(run_id, output=None):
    data = _request("GET", f"/eval-runs/{run_id}/results")
    _write_output(data, output)


def cmd_runs_cancel(run_id):
    data = _request("POST", f"/eval-runs/{run_id}/cancel")
    print(f"Run {run_id} cancelled", file=sys.stderr)
    _print_json(data)


# === Chat ===


def cmd_chat(base_id, message, conversation_id=None, context=None):
    if not conversation_id:
        import uuid

        conversation_id = f"qa_{uuid.uuid4().hex[:12]}"

    body = {
        "conversation_id": conversation_id,
        "user_message": message,
    }
    if context:
        body["context"] = context

    data = _request("POST", f"/playbooks/{base_id}/active/chat", body=body)

    # Extract assistant messages from events
    print(f"conversation_id: {conversation_id}", file=sys.stderr)
    events = data.get("events", [])
    for event in events:
        if event.get("event_type") == "message":
            content = event.get("data", {}).get("content", "")
            if content:
                print(f"\nAssistant: {content}")

    # Show tool calls if any
    tool_calls = data.get("tool_calls", [])
    if tool_calls:
        print(f"\n[{len(tool_calls)} tool call(s)]", file=sys.stderr)
        for tc in tool_calls:
            print(f"  {tc.get('name', '?')}({tc.get('arguments', '{}')})", file=sys.stderr)


# === Main ===


def main():
    args = sys.argv[1:]

    if len(args) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    group = args[0]
    action = args[1]

    def get_flag(flag, default=None):
        """Get a flag value from args."""
        for i, a in enumerate(args):
            if a == flag and i + 1 < len(args):
                return args[i + 1]
        return default

    def get_body():
        """Parse --body flag as JSON."""
        raw = get_flag("--body")
        if not raw:
            print("Error: --body is required", file=sys.stderr)
            sys.exit(1)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON in --body: {e}", file=sys.stderr)
            sys.exit(1)

    if group == "cases":
        if action == "list" and len(args) >= 3:
            cmd_cases_list(args[2], enabled_only="--enabled-only" in args)
        elif action == "create" and len(args) >= 3:
            cmd_cases_create(args[2], get_body())
        elif action == "batch" and len(args) >= 3:
            cmd_cases_batch(args[2], get_body())
        elif action == "get" and len(args) >= 3:
            cmd_cases_get(args[2])
        elif action == "update" and len(args) >= 3:
            cmd_cases_update(args[2], get_body())
        elif action == "delete" and len(args) >= 3:
            cmd_cases_delete(args[2])
        else:
            print(f"Unknown cases action: {action}", file=sys.stderr)
            sys.exit(1)

    elif group == "runs":
        if action == "create" and len(args) >= 3:
            playbook_id = get_flag("--playbook-id")
            if not playbook_id:
                print("Error: --playbook-id is required", file=sys.stderr)
                sys.exit(1)
            context = None
            context_raw = get_flag("--context")
            if context_raw:
                context = json.loads(context_raw)
            cmd_runs_create(args[2], playbook_id, context)
        elif action == "list" and len(args) >= 3:
            page = int(get_flag("--page", "1"))
            page_size = int(get_flag("--page-size", "10"))
            cmd_runs_list(args[2], page, page_size)
        elif action == "status" and len(args) >= 3:
            cmd_runs_status(args[2])
        elif action == "results" and len(args) >= 3:
            output = get_flag("-o")
            cmd_runs_results(args[2], output)
        elif action == "cancel" and len(args) >= 3:
            cmd_runs_cancel(args[2])
        else:
            print(f"Unknown runs action: {action}", file=sys.stderr)
            sys.exit(1)

    elif group == "chat":
        if len(args) < 2:
            print("Usage: qa.py chat PLAYBOOK_BASE_ID --message 'text'", file=sys.stderr)
            sys.exit(1)
        base_id = args[1]
        message = get_flag("--message")
        if not message:
            print("Error: --message is required", file=sys.stderr)
            sys.exit(1)
        conversation_id = get_flag("--conversation-id")
        context = None
        context_raw = get_flag("--context")
        if context_raw:
            context = json.loads(context_raw)
        cmd_chat(base_id, message, conversation_id, context)

    else:
        print(f"Unknown group: {group}. Use 'cases', 'runs', or 'chat'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
