#!/usr/bin/env python3
"""Quality engineering CLI for Studio Chat eval system.

Manages test cases, triggers eval runs, reads results, and simulates
conversations with playbook assistants.

All `qa.py chat` conversations are flagged as evals (is_eval=true), so they
are excluded from the production chat log, analytics, and sticky-model
assignment — with or without playbook-override / tool-mocks flags.

Usage:
    qa.py cases list PLAYBOOK_BASE_ID
    qa.py cases create PLAYBOOK_BASE_ID --body '{...}'
    qa.py cases batch PLAYBOOK_BASE_ID --body '{"cases": [...]}'
    qa.py cases get CASE_ID
    qa.py cases update CASE_ID --body '{...}'
    qa.py cases delete CASE_ID
    qa.py runs create PLAYBOOK_BASE_ID --playbook-id ID [--context '{}']
                                       [--case-ids id1,id2,...] [--concurrency N]
                                       [--model M] [--simulator-model M] [--judge-model M]
                                       [--instructions-file FILE | --instructions TEXT]
                                       [--skills-file FILE] [--examples-file FILE]
                                       [--kb-ids id1,id2] [--api-tools t1,t2]
    qa.py runs list PLAYBOOK_BASE_ID [--page N] [--page-size N]
    qa.py runs status RUN_ID
    qa.py runs results RUN_ID [-o file.json]
    qa.py runs cancel RUN_ID
    qa.py chat PLAYBOOK_BASE_ID --message "text" [--conversation-id ID] [--context '{}']
                                [--instructions-file FILE | --instructions TEXT]
                                [--skills-file FILE] [--examples-file FILE]
                                [--kb-ids id1,id2] [--api-tools t1,t2]
                                [--tool-mocks-file FILE]
                                [--verbose]
    qa.py dry-run start PLAYBOOK_BASE_ID --playbook-id ID --case '{...}'
                                         [--instructions-file FILE | --instructions TEXT]
                                         [--skills-file FILE] [--examples-file FILE]
    qa.py dry-run status DRY_RUN_ID
    qa.py dry-run cancel DRY_RUN_ID

Playbook override flags (chat and runs create):
    Pass any subset of the flags below to test instructions / skills WITHOUT
    saving them as a new playbook version. Each override flag replaces the
    corresponding field on the active (or named) playbook version in memory
    for this call only. Conversations are forced into preview+eval mode so
    they never pollute production analytics or chatlogs.

      --instructions TEXT         Inline replacement for the main instructions.
      --instructions-file FILE    Same, read from a file (use for long prompts).
      --skills-file FILE          JSON file with a list of skill objects:
                                  [{"name", "description", "trigger", "content",
                                    "examples"?, "order"?}, ...]
                                  Pass an empty list ([]) to disable all skills.
      --examples-file FILE        JSON file with a list of example dicts.
      --kb-ids id1,id2            Comma-separated KB IDs to use (replaces playbook's).
      --api-tools t1,t2           Comma-separated API tool IDs (replaces playbook's).
      --tool-mocks-file FILE      JSON file with {tool_name: ToolMockSpec | [...]}.
                                  Stubs specific tool calls with canned responses
                                  for this chat/run, mirroring EvalCase.tool_mocks
                                  semantics. Forces preview+eval mode so the
                                  conversation does NOT pollute production analytics
                                  or chatlogs. Mocked calls surface with
                                  is_mocked=true in the response's tool_calls.

Requires the auth token to have admin or API-key privileges.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlencode, urljoin


BASE_URL = os.environ.get("STUDIO_API_URL", "https://api.studiochat.io")


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


def _read_text_file(path):
    """Read a UTF-8 text file; abort the CLI with a clear error if it's missing."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(1)


def _read_json_file(path):
    """Read a JSON file (the skill ships override skills / examples as JSON)."""
    raw = _read_text_file(path)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def _parse_csv_list(value):
    """Split a comma-separated CLI value into a list of trimmed strings.

    An empty value (``""``) returns an explicit empty list so the caller
    can pass ``--kb-ids ""`` to *disable* all KBs (vs. omitting the flag,
    which keeps the playbook's KBs).
    """
    if value is None:
        return None
    return [chunk.strip() for chunk in value.split(",") if chunk.strip()] if value else []


def build_playbook_override(
    instructions=None,
    instructions_file=None,
    skills_file=None,
    examples_file=None,
    kb_ids=None,
    api_tools=None,
    enrichment_tool_ids=None,
):
    """Assemble a PlaybookOverride wire dict from skill-level CLI inputs.

    Returns ``None`` if none of the inputs were supplied — used as the
    sentinel by the request shaper to *omit* the field entirely (so the
    saved playbook content is used as-is).

    The shape mirrors ``app.models.PlaybookOverride`` on the BE side; each
    non-None key replaces the corresponding field on the playbook in
    memory. ``skills`` / ``kb_ids`` / ``api_tools`` set to ``[]`` are kept
    explicit so the BE actually disables them instead of falling back to
    the saved values.
    """
    override: dict = {}

    if instructions is not None and instructions_file is not None:
        print(
            "Error: --instructions and --instructions-file are mutually exclusive",
            file=sys.stderr,
        )
        sys.exit(1)
    if instructions_file:
        override["content"] = _read_text_file(instructions_file)
    elif instructions is not None:
        override["content"] = instructions

    if skills_file:
        skills = _read_json_file(skills_file)
        # Two accepted shapes, forwarded verbatim to the BE:
        #   * list[skill] → full replace (drop saved skills, use exactly these).
        #   * dict with add/replace/remove → surgical patch on top of saved.
        # Discrimination matches the BE's PlaybookOverride.skills union, so
        # the file the user authors mirrors the wire shape.
        if not isinstance(skills, (list, dict)):
            print(
                f"Error: --skills-file {skills_file} must contain a JSON list (full replace) "
                "or a patch object with add/replace/remove keys.",
                file=sys.stderr,
            )
            sys.exit(1)
        if isinstance(skills, dict):
            allowed = {"add", "replace", "remove"}
            unknown = set(skills.keys()) - allowed
            if unknown:
                print(
                    f"Error: --skills-file {skills_file} patch object has unknown keys: "
                    f"{sorted(unknown)}. Allowed: add, replace, remove.",
                    file=sys.stderr,
                )
                sys.exit(1)
        override["skills"] = skills

    if examples_file:
        examples = _read_json_file(examples_file)
        if not isinstance(examples, list):
            print(
                f"Error: --examples-file {examples_file} must contain a JSON list",
                file=sys.stderr,
            )
            sys.exit(1)
        override["examples"] = examples

    if kb_ids is not None:
        override["kb_ids"] = _parse_csv_list(kb_ids)
    if api_tools is not None:
        override["api_tools"] = _parse_csv_list(api_tools)
    if enrichment_tool_ids is not None:
        override["enrichment_tool_ids"] = _parse_csv_list(enrichment_tool_ids)

    return override or None


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


def _load_tool_mocks_file(path):
    """Read a tool_mocks JSON file and validate the top-level shape.

    Accepts the same wire shape as ``EvalCase.tool_mocks`` and the chat
    endpoint's ``tool_mocks`` field: a dict keyed by tool name (the
    string that appears in ``ToolCallTrace.name`` — uppercase
    ``TOOLKIT_ACTION`` for Composio tools, snake_case for built-ins
    and custom API tools), with values that are either a single
    ToolMockSpec or a list of them. The BE does the Pydantic
    validation; we just sanity-check the wrapper shape so an obviously
    malformed file doesn't pollute the request.
    """
    if not path:
        return None
    mocks = _read_json_file(path)
    if not isinstance(mocks, dict):
        print(
            f"Error: --tool-mocks-file {path} must contain a JSON object "
            "({tool_name: ToolMockSpec | [ToolMockSpec, ...]}).",
            file=sys.stderr,
        )
        sys.exit(1)
    return mocks


def cmd_runs_create(
    base_id,
    playbook_id,
    context=None,
    playbook_override=None,
    case_ids=None,
    concurrency=None,
    model=None,
    simulator_model=None,
    judge_model=None,
    tool_mocks=None,
):
    body = {"playbook_id": playbook_id}
    if context:
        body["user_context"] = context
    if playbook_override is not None:
        body["playbook_override"] = playbook_override
    # Optional EvalRunCreate tunables — only forwarded when set so the BE
    # falls back to its defaults (use-playbook-default model, run-all-enabled,
    # concurrency=1) when the operator doesn't supply them.
    if case_ids:
        body["case_ids"] = case_ids
    if concurrency is not None:
        body["concurrency"] = concurrency
    if model:
        body["model"] = model
    if simulator_model:
        body["simulator_model"] = simulator_model
    if judge_model:
        body["judge_model"] = judge_model
    # NOTE: run-level tool_mocks are NOT supported by the BE — per-case
    # tool_mocks live on the case body itself (``EvalCase.tool_mocks``).
    # If the QA caller wants to mock during a run, the right place is the
    # case definition, not the run trigger. We forward ``tool_mocks`` only
    # for the chat path. This branch stays for symmetric flag parsing in
    # main(); if someone passes ``--tool-mocks-file`` to ``runs create``
    # we surface a clear error here rather than silently ignoring it.
    if tool_mocks is not None:
        print(
            "Error: --tool-mocks-file is only valid on `qa.py chat`. For runs, "
            "put tool_mocks on the individual case body (see `qa.py cases create`).",
            file=sys.stderr,
        )
        sys.exit(1)
    data = _request("POST", f"/playbooks/{base_id}/eval-runs", body=body)
    print(f"Run started: {data['id']} (status: {data['status']})", file=sys.stderr)
    if playbook_override is not None:
        print(
            f"  ↳ using playbook override "
            f"(fields: {', '.join(sorted(playbook_override.keys()))})",
            file=sys.stderr,
        )
    if case_ids:
        print(f"  ↳ running {len(case_ids)} selected case(s)", file=sys.stderr)
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


# === Dry-run (per-case ephemeral "Simulate") ===
#
# Runs a single unsaved EvalCase against a playbook version, with optional
# playbook_override applied for the duration. State lives in process for
# ~30 minutes and is polled by dry_run_id. Nothing is persisted to
# ``eval_cases`` or ``eval_runs`` — ideal for de-risking a case definition
# before committing it, or for validating an instructions/skills change
# against a specific scenario without bumping a version.


def cmd_dry_run_start(base_id, playbook_id, case, playbook_override=None):
    body = {"playbook_id": playbook_id, "case": case}
    if playbook_override is not None:
        body["playbook_override"] = playbook_override
    data = _request("POST", f"/playbooks/{base_id}/eval-cases/dry-run", body=body)
    print(f"Dry-run started: {data['dry_run_id']}", file=sys.stderr)
    if playbook_override is not None:
        print(
            f"  ↳ using playbook override "
            f"(fields: {', '.join(sorted(playbook_override.keys()))})",
            file=sys.stderr,
        )
    _print_json(data)


def cmd_dry_run_status(dry_run_id):
    data = _request("GET", f"/eval-cases/dry-run/{dry_run_id}")
    _print_json(data)


def cmd_dry_run_cancel(dry_run_id):
    data = _request("POST", f"/eval-cases/dry-run/{dry_run_id}/cancel")
    print(f"Dry-run {dry_run_id} cancelled", file=sys.stderr)
    _print_json(data)


# === Chat ===


def cmd_chat(
    base_id,
    message,
    conversation_id=None,
    context=None,
    verbose=False,
    playbook_override=None,
    tool_mocks=None,
):
    if not conversation_id:
        import uuid

        conversation_id = f"qa_{uuid.uuid4().hex[:12]}"

    body = {
        "conversation_id": conversation_id,
        "user_message": message,
        "include_citations": True,
        # QA chat is a testing tool — its conversations must never land in the
        # production chat log, analytics, or sticky-model assignment. Mark every
        # ad-hoc chat as an eval so the BE excludes it (the chatlog/metrics
        # queries filter out is_eval=True by default). playbook_override /
        # tool_mocks additionally force is_preview server-side, but a plain
        # `qa.py chat --message ...` with neither would otherwise persist as a
        # production conversation — so the flag has to be set here, always.
        "is_eval": True,
    }
    if context:
        body["context"] = context
    if playbook_override is not None:
        body["playbook_override"] = playbook_override
    if tool_mocks is not None:
        body["tool_mocks"] = tool_mocks

    data = _request("POST", f"/playbooks/{base_id}/active/chat", body=body)

    # -- Header --
    elapsed = data.get("elapsed_time_ms")
    elapsed_str = f" ({elapsed}ms)" if elapsed else ""
    print(f"conversation_id: {conversation_id}{elapsed_str}", file=sys.stderr)
    print(
        "  ↳ eval mode — conversation excluded from the production chat log, "
        "analytics, and sticky-model assignment",
        file=sys.stderr,
    )
    if playbook_override is not None:
        print(
            f"  ↳ playbook override active "
            f"(fields: {', '.join(sorted(playbook_override.keys()))})",
            file=sys.stderr,
        )
    if tool_mocks is not None:
        print(
            f"  ↳ tool mocks active (tools: {', '.join(sorted(tool_mocks.keys()))})",
            file=sys.stderr,
        )

    # -- Events --
    events = data.get("events", [])
    for event in events:
        etype = event.get("event_type", "")
        edata = event.get("data", {})
        if etype == "message":
            content = edata.get("content", "")
            if content:
                print(f"\nAssistant: {content}")
        elif etype == "label":
            print(f"  [label] {edata.get('label', '?')}", file=sys.stderr)
        elif etype == "note":
            print(f"  [note] {edata.get('content', '')[:120]}", file=sys.stderr)
        elif etype in ("handoff_agent", "handoff_team"):
            target = edata.get("agent_id") or edata.get("team_id") or "?"
            reason = edata.get("reason", "")
            print(f"  [{etype}] → {target}  reason: {reason}", file=sys.stderr)
        elif etype == "priority":
            print(f"  [priority] {edata.get('priority', '?')}", file=sys.stderr)

    # -- Tool calls --
    tool_calls = data.get("tool_calls", [])
    if tool_calls:
        print(f"\n--- Tool calls ({len(tool_calls)}) ---", file=sys.stderr)
        for tc in tool_calls:
            name = tc.get("name", "?")
            ttype = tc.get("tool_type", "")
            args_raw = tc.get("arguments", "{}")
            result_raw = tc.get("result", "")

            # Parse arguments for readable display
            try:
                args_obj = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except (json.JSONDecodeError, TypeError):
                args_obj = args_raw

            type_tag = f" [{ttype}]" if ttype else ""
            # ``is_mocked=true`` means the wrapper short-circuited the real
            # tool with a canned response from ``tool_mocks``. Flagging this
            # in the output is critical for QA — otherwise it's easy to
            # mistake a stubbed result for a real one and chase a phantom.
            mock_tag = " [MOCKED]" if tc.get("is_mocked") else ""
            print(f"  {name}{type_tag}{mock_tag}", file=sys.stderr)

            # Show key arguments
            if isinstance(args_obj, dict):
                for k, v in args_obj.items():
                    val = str(v)[:200]
                    print(f"    {k}: {val}", file=sys.stderr)

            # Show result summary
            if verbose and result_raw:
                result_str = str(result_raw)
                if len(result_str) > 500:
                    result_str = result_str[:500] + "…"
                print(f"    → {result_str}", file=sys.stderr)
            elif result_raw and name == "search_knowledge_base":
                # Always show KB search result summary
                try:
                    result_obj = json.loads(result_raw) if isinstance(result_raw, str) else result_raw
                    if isinstance(result_obj, dict):
                        results = result_obj.get("results", [])
                        print(f"    → {len(results)} result(s)", file=sys.stderr)
                        for r in results[:5]:
                            score = r.get("relevance_score", "")
                            title = r.get("item_title", "")
                            kb_type = r.get("kb_type", "")
                            snippet = (r.get("content", ""))[:100].replace("\n", " ")
                            score_str = f" ({score:.2f})" if isinstance(score, (int, float)) else ""
                            print(f"      [{kb_type}] {title}{score_str}: {snippet}", file=sys.stderr)
                except (json.JSONDecodeError, TypeError):
                    pass
            elif result_raw and name == "load_skill":
                result_str = str(result_raw)
                print(f"    → loaded ({len(result_str)} chars)", file=sys.stderr)

    # -- Citations --
    citations = data.get("citations") or []
    if citations:
        print(f"\n--- Citations ({len(citations)}) ---", file=sys.stderr)
        for c in citations:
            cid = c.get("citation_id", "?")
            kb_id = c.get("kb_id", "?")
            item_id = c.get("item_id", "")
            fname = c.get("file_name", "")
            snippet = (c.get("content", ""))[:120].replace("\n", " ")
            source = fname or item_id or kb_id
            print(f"  [{cid}] {source}: {snippet}", file=sys.stderr)

    # -- Explanation --
    explanation = data.get("explanation", "")
    if explanation:
        print(f"\n--- Explanation ---", file=sys.stderr)
        print(f"  {explanation}", file=sys.stderr)

    # -- Raw JSON output (verbose) --
    if verbose:
        print(f"\n--- Full response ---", file=sys.stderr)
        _print_json(data)


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
            playbook_override = build_playbook_override(
                instructions=get_flag("--instructions"),
                instructions_file=get_flag("--instructions-file"),
                skills_file=get_flag("--skills-file"),
                examples_file=get_flag("--examples-file"),
                kb_ids=get_flag("--kb-ids"),
                api_tools=get_flag("--api-tools"),
                enrichment_tool_ids=get_flag("--enrichment-tools"),
            )
            # --case-ids accepts a comma-separated list to stay ergonomic
            # — shells make quoting JSON arrays painful, and these are
            # always opaque UUIDs.
            case_ids_raw = get_flag("--case-ids")
            case_ids = None
            if case_ids_raw:
                case_ids = [c.strip() for c in case_ids_raw.split(",") if c.strip()]
            concurrency_raw = get_flag("--concurrency")
            concurrency = int(concurrency_raw) if concurrency_raw else None
            cmd_runs_create(
                args[2],
                playbook_id,
                context,
                playbook_override,
                case_ids=case_ids,
                concurrency=concurrency,
                model=get_flag("--model"),
                simulator_model=get_flag("--simulator-model"),
                judge_model=get_flag("--judge-model"),
                tool_mocks=_load_tool_mocks_file(get_flag("--tool-mocks-file")),
            )
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
            print("Usage: qa.py chat PLAYBOOK_BASE_ID --message 'text' [--verbose]", file=sys.stderr)
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
        verbose = "--verbose" in args or "-v" in args
        playbook_override = build_playbook_override(
            instructions=get_flag("--instructions"),
            instructions_file=get_flag("--instructions-file"),
            skills_file=get_flag("--skills-file"),
            examples_file=get_flag("--examples-file"),
            kb_ids=get_flag("--kb-ids"),
            api_tools=get_flag("--api-tools"),
            enrichment_tool_ids=get_flag("--enrichment-tools"),
        )
        cmd_chat(
            base_id,
            message,
            conversation_id,
            context,
            verbose=verbose,
            playbook_override=playbook_override,
            tool_mocks=_load_tool_mocks_file(get_flag("--tool-mocks-file")),
        )

    elif group == "dry-run":
        # Dry-run starts an ephemeral simulator+judge run for a single
        # unsaved case. Use this to validate a candidate case definition
        # (does the simulator generate plausible turns? Does termination
        # fire? Do the assertions grade right?) before persisting it via
        # ``qa.py cases create``. State expires after ~30 min.
        if action == "start" and len(args) >= 3:
            playbook_id = get_flag("--playbook-id")
            if not playbook_id:
                print("Error: --playbook-id is required", file=sys.stderr)
                sys.exit(1)
            case_raw = get_flag("--case")
            if not case_raw:
                print(
                    "Error: --case is required (JSON object matching EvalCaseCreate)",
                    file=sys.stderr,
                )
                sys.exit(1)
            try:
                case = json.loads(case_raw)
            except json.JSONDecodeError as e:
                print(f"Error: invalid JSON in --case: {e}", file=sys.stderr)
                sys.exit(1)
            playbook_override = build_playbook_override(
                instructions=get_flag("--instructions"),
                instructions_file=get_flag("--instructions-file"),
                skills_file=get_flag("--skills-file"),
                examples_file=get_flag("--examples-file"),
                kb_ids=get_flag("--kb-ids"),
                api_tools=get_flag("--api-tools"),
                enrichment_tool_ids=get_flag("--enrichment-tools"),
            )
            cmd_dry_run_start(args[2], playbook_id, case, playbook_override=playbook_override)
        elif action == "status" and len(args) >= 3:
            cmd_dry_run_status(args[2])
        elif action == "cancel" and len(args) >= 3:
            cmd_dry_run_cancel(args[2])
        else:
            print(f"Unknown dry-run action: {action}", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Unknown group: {group}. Use 'cases', 'runs', 'chat', or 'dry-run'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
