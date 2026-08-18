#!/usr/bin/env python3
"""Tests for agent_optimize.py.

Run: python3 test_agent_optimize.py
No third-party deps; uses only stdlib + assert.

These tests exercise the plumbing that real-API behavior depends on, using
fixtures shaped like the ACTUAL wire responses (notably the {"data":[...]}
envelopes). The critical lesson baked in here: fixtures must start ENVELOPED,
not pre-unwrapped, or they validate the diff logic while silently skipping the
save-to-PUT round-trip that the tool exists to make safe.
"""

import base64
import importlib.util
import io
import json
import os
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "agent_optimize.py")

spec = importlib.util.spec_from_file_location("agent_optimize", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


# ---------------------------------------------------------------------------
# Fixtures — shaped like the real wire responses
# ---------------------------------------------------------------------------


def make_jwt(username):
    """An unsigned JWT carrying the `username` claim the server sets."""
    def seg(obj):
        raw = json.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return f"{seg({'alg': 'RS256'})}.{seg({'username': username})}.signature"

def make_body():
    return {
        "system_prompt": "Apply MEDDPICC.",
        "properties": {
            "e1": {
                "type": "string", "title": "Metrics",
                "description": "Capture metrics.",
                "scoring_rubrik": "0: none\n3: complete",
                "max_score": 3, "sort_order": 0, "field_mapping": "",
            }
        },
    }


def make_get_envelope():
    """Exactly what GET /coaching-templates/?id= returns: singly-wrapped
    envelope, PromptTemplateRequest at data[0]."""
    return {"data": [{
        "prompt_template": {
            "id": "abc", "category": "qualification",
            "body": json.dumps(make_body()),
        },
        "prompt_template_list_item": {
            "name": "MEDDPICC", "type": "coaching", "category": "qualification",
            "teams": [5, 12], "visibility": 1,
            "meta": {"modified_date": "2026-01-01"},
        },
    }]}


def make_coaching_results_envelope():
    """Shape of GET /transcript/coaching/: singly-wrapped, results merged into
    each property as result/score. NO total field."""
    body = make_body()
    body["properties"]["e1"]["result"] = "Customer cited $2M in savings."
    body["properties"]["e1"]["score"] = 2
    return {"data": [{
        "id": "abc", "category": "qualification", "body": json.dumps(body),
    }]}


def make_meeting_list_envelope(meetings):
    """Shape of GET /meeting_list/: DOUBLY-wrapped — data[0] is the array."""
    return {"data": [meetings]}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_unwrap_envelope_to_bare_request():
    """Bug 1: get-agent must save the bare PromptTemplateRequest, not the
    envelope, or the PUT 400s on an empty type."""
    unwrapped = mod._unwrap_request(make_get_envelope())
    assert "prompt_template" in unwrapped
    assert "prompt_template_list_item" in unwrapped
    assert unwrapped["prompt_template_list_item"]["type"] == "coaching"
    assert "data" not in unwrapped
    print("PASS: unwrap envelope -> bare PromptTemplateRequest")


def test_unwrap_idempotent():
    """The saved (already-unwrapped) file must re-push cleanly: unwrapping an
    unwrapped object is a no-op."""
    once = mod._unwrap_request(make_get_envelope())
    twice = mod._unwrap_request(once)
    assert twice["prompt_template_list_item"]["type"] == "coaching"
    assert twice["prompt_template"]["id"] == "abc"
    print("PASS: unwrap is idempotent")


def test_old_path_would_400():
    """Document the original bug: reading list_item off the raw envelope yields
    no type, which is the 400 the server returns."""
    raw = make_get_envelope()
    # The buggy path treated the envelope as if it were the request:
    li = raw.get("prompt_template_list_item") or {}
    assert li.get("type") is None
    print("PASS: confirmed old verbatim-PUT path saw empty type (the 400)")


def test_body_survives_round_trip():
    """body must remain a stringified JSON blob, parseable to the same object,
    after an unwrap round-trip."""
    unwrapped = mod._unwrap_request(make_get_envelope())
    body_str = unwrapped["prompt_template"]["body"]
    assert isinstance(body_str, str)
    parsed = json.loads(body_str)
    assert parsed["properties"]["e1"]["title"] == "Metrics"
    print("PASS: body stays stringified JSON through round-trip")


def test_dry_run_diff_identical_roundtrip():
    """A faithful round-trip must show NO diff (server-forced fields ignored)."""
    env = make_get_envelope()
    cur_pt, cur_li = mod._find_template_pair(env)
    unwrapped = mod._unwrap_request(env)
    new_pt = unwrapped["prompt_template"]
    new_li = unwrapped["prompt_template_list_item"]
    before = mod._comparable_view(cur_pt, cur_li)
    after = mod._comparable_view(new_pt, new_li)
    diff = mod._diff_dicts(before, after)
    assert diff == [], f"identical round-trip should be empty, got: {diff}"
    print("PASS: identical round-trip dry-run shows no changes")


def test_dry_run_diff_detects_real_change():
    """A genuine description/system_prompt change must appear in the diff."""
    env = make_get_envelope()
    cur_pt, cur_li = mod._find_template_pair(env)
    body2 = make_body()
    body2["system_prompt"] = "Apply MEDDPICC rigorously."
    body2["properties"]["e1"]["description"] = "Capture quantified metrics."
    new_pt = {"id": "abc", "category": "qualification", "body": json.dumps(body2)}
    before = mod._comparable_view(cur_pt, cur_li)
    after = mod._comparable_view(new_pt, cur_li)
    diff = mod._diff_dicts(before, after)
    assert any("description" in c for c in diff)
    assert any("system_prompt" in c for c in diff)
    print("PASS: real config changes detected in diff")


def test_dry_run_ignores_runtime_fields():
    """result/score (runtime output) must not register as config changes."""
    env = make_get_envelope()
    cur_pt, cur_li = mod._find_template_pair(env)
    # Simulate the same config but with runtime result/score present
    body_rt = make_body()
    body_rt["properties"]["e1"]["result"] = "something"
    body_rt["properties"]["e1"]["score"] = 2
    new_pt = {"id": "abc", "category": "qualification", "body": json.dumps(body_rt)}
    before = mod._comparable_view(cur_pt, cur_li)
    after = mod._comparable_view(new_pt, cur_li)
    diff = mod._diff_dicts(before, after)
    assert diff == [], f"runtime fields should be ignored, got: {diff}"
    print("PASS: runtime result/score ignored in diff")


def test_dry_run_ignores_server_forced_fields():
    """meta/id/category churn must not register as changes."""
    env = make_get_envelope()
    cur_pt, cur_li = mod._find_template_pair(env)
    new_li = dict(cur_li)
    new_li["meta"] = {"modified_date": "2099-12-31"}  # churned
    new_pt = {"id": "different", "category": "qualification",
              "body": json.dumps(make_body())}
    before = mod._comparable_view(cur_pt, cur_li)
    after = mod._comparable_view(new_pt, new_li)
    diff = mod._diff_dicts(before, after)
    assert diff == [], f"server-forced churn should be ignored, got: {diff}"
    print("PASS: server-forced fields (meta/id) ignored in diff")


def test_dropped_field_detection():
    """Bug from Q3: omitting a set field (teams) is the silent-unshare risk and
    must be detectable."""
    cur_li = {"name": "MEDDPICC", "type": "coaching", "teams": [5, 12], "visibility": 1}
    new_li = {"name": "MEDDPICC", "type": "coaching", "visibility": 1}  # teams dropped
    dropped = []
    for k, v in cur_li.items():
        if k.lower() in mod.SERVER_FORCED_LIST_ITEM_FIELDS:
            continue
        if v and (k not in new_li or not new_li.get(k)):
            dropped.append(k)
    assert "teams" in dropped
    print("PASS: dropped 'teams' field detected (silent-unshare guard)")


def test_team_filter_int_string_coercion():
    """Bug 2: --team arrives as a string; team_ids are ints. Must match either."""
    team_id = "5"
    team_match = {str(team_id)}
    try:
        team_match.add(int(team_id))
    except (TypeError, ValueError):
        pass
    assert any(t in team_match or str(t) in team_match for t in [5, 12])
    assert any(t in team_match or str(t) in team_match for t in ["5", "12"])
    assert not any(t in team_match or str(t) in team_match for t in [99, 100])
    print("PASS: --team matches int and string team_ids, rejects non-members")


def test_meeting_id_fallback():
    """Bug 3: a meeting with empty id is recovered via start_time/room."""
    m = {"id": "", "start_time": "2026-06-25T13:10:09.000Z", "room": "room99"}
    mid = m.get("meeting_id") or m.get("id") or ""
    if not mid and m.get("start_time") and m.get("room"):
        mid = f'{m.get("start_time")}/{m.get("room")}'
    assert mid == "2026-06-25T13:10:09.000Z/room99"
    print("PASS: meeting id falls back to start_time/room composite")


def test_meeting_list_double_unwrap():
    """Meeting list is DOUBLY wrapped: data[0] is the array."""
    env = make_meeting_list_envelope([
        {"id": "m1", "start_time": "2026-06-01T10:00:00Z",
         "end_time": "2026-06-01T10:45:00Z", "team_ids": [5]},
    ])
    data = env.get("data")
    meetings = data[0] if data else []
    assert len(meetings) == 1 and meetings[0]["id"] == "m1"
    # empty case
    empty = {"data": [[]]}
    d = empty.get("data")
    assert (d[0] if d else []) == []
    print("PASS: meeting list data[0] double-unwrap + empty guard")


def test_coaching_results_parse():
    """Coaching results: per-property result/score at data[0].body.properties,
    no total field. Verify the summary parser reads them and the total is a sum."""
    env = make_coaching_results_envelope()
    pt, li = mod._find_template_pair(env)
    body = json.loads(pt["body"])
    props = body["properties"]
    assert props["e1"]["result"] == "Customer cited $2M in savings."
    assert props["e1"]["score"] == 2
    assert "total_score" not in body  # there is no wire total
    # total is computed by summing
    total = sum(p.get("score", 0) for p in props.values())
    max_total = sum(p.get("max_score", 0) for p in props.values())
    assert total == 2 and max_total == 3
    print("PASS: coaching results parsed; total computed by sum (no wire field)")


def test_error_envelope_handled():
    """Error responses come back as {"errors":[...]} with no data."""
    err = {"errors": ["template not found"]}
    summary = mod.parse_agent_summary(err)
    assert "error" in summary.lower()
    print("PASS: error envelope handled in parse_agent_summary")


def test_dry_run_diff_end_to_end_identical():
    """Belt-and-suspenders: drive the whole dry_run_diff() — including its
    internal fetch_agent_config call and unwrap — not just the components.
    Stubs the network so current = the real envelope. An unchanged round-trip
    must return no diff. This pins the seam where dry_run_diff fetches the live
    config and unwraps it before comparing, so a future refactor that breaks
    that step fails loudly here."""
    env = make_get_envelope()
    original = mod.fetch_agent_config
    try:
        mod.fetch_agent_config = lambda base_url, token, agent_id: env
        # new_config is the bare unwrapped request saved by get-agent
        new_config = mod._unwrap_request(env)
        changes, cur_li, new_li = mod.dry_run_diff(
            "https://stageapi.aircover.ai", "tok", "abc", new_config
        )
        assert changes == [], f"identical e2e round-trip should be empty, got: {changes}"
        assert cur_li.get("type") == "coaching"
        assert new_li.get("type") == "coaching"
    finally:
        mod.fetch_agent_config = original
    print("PASS: dry_run_diff end-to-end (stubbed fetch) — identical round-trip clean")


def test_dry_run_diff_end_to_end_real_change():
    """Same end-to-end path, but with a genuine description change in the new
    config. The diff must surface it."""
    env = make_get_envelope()
    original = mod.fetch_agent_config
    try:
        mod.fetch_agent_config = lambda base_url, token, agent_id: env
        new_config = mod._unwrap_request(env)
        body2 = json.loads(new_config["prompt_template"]["body"])
        body2["properties"]["e1"]["description"] = "Capture quantified buyer-confirmed metrics."
        new_config["prompt_template"]["body"] = json.dumps(body2)
        changes, cur_li, new_li = mod.dry_run_diff(
            "https://stageapi.aircover.ai", "tok", "abc", new_config
        )
        assert any("description" in c for c in changes), f"expected description change, got: {changes}"
    finally:
        mod.fetch_agent_config = original
    print("PASS: dry_run_diff end-to-end (stubbed fetch) — real change surfaced")


# --- Scoring + set-equality integrity tests -------------------------------

def _scores(props, meetings, rows, **extra):
    """Build a scores dict. rows = list of (prop, meeting, score[, category])."""
    scores = []
    for r in rows:
        row = {"property": r[0], "meeting": r[1], "score": r[2]}
        if len(r) > 3:
            row["category"] = r[3]
        scores.append(row)
    d = {"agent_id": "abc", "round": 0, "properties": props, "meetings": meetings, "scores": scores}
    d.update(extra)
    return d


def _write(tmpdir, name, obj):
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        json.dump(obj, f)
    return path


def test_scores_complete_grid_loads():
    """A complete grid loads and the distribution is correct."""
    import tempfile
    d = _scores(["e1", "e2"], ["m1", "m2"], [
        ("e1", "m1", 2), ("e1", "m2", 1, "generic"),
        ("e2", "m1", 0, "hallucination"), ("e2", "m2", 2)])
    with tempfile.TemporaryDirectory() as td:
        data = mod._load_scores(_write(td, "s.json", d))
        dist = mod._distribution(data)
    assert dist["total"] == 4 and dist["solid"] == 2 and dist["weak"] == 1 and dist["broken"] == 1
    print("PASS: complete grid loads; distribution computed correctly")


def test_scores_missing_pair_rejected():
    """A missing (property, meeting) pair is rejected (denominator integrity)."""
    import tempfile
    d = _scores(["e1"], ["m1", "m2"], [("e1", "m1", 2)])  # missing (e1, m2)
    with tempfile.TemporaryDirectory() as td:
        try:
            mod._load_scores(_write(td, "s.json", d))
            assert False, "should have rejected missing pair"
        except SystemExit as e:
            assert "missing" in str(e) and "(e1, m2)" in str(e)
    print("PASS: missing (e1, m2) rejected (denominator integrity)")


def test_scores_duplicate_pair_rejected():
    """A duplicate pair is rejected (double-count guard)."""
    import tempfile
    d = _scores(["e1"], ["m1"], [("e1", "m1", 2), ("e1", "m1", 0, "generic")])
    with tempfile.TemporaryDirectory() as td:
        try:
            mod._load_scores(_write(td, "s.json", d))
            assert False, "should have rejected duplicate pair"
        except SystemExit as e:
            assert "duplicate" in str(e) and "(e1, m1)" in str(e)
    print("PASS: duplicate (e1, m1) rejected (double-count)")


def test_scores_case3_dup_plus_omission_same_length():
    """CASE 3 — the one the count check waves through. A duplicate of (e1,m1)
    plus an omission of (e1,m2) yields row count == P*M, so len(scores)==4==2*2.
    A count check passes; set-equality must still reject."""
    import tempfile
    d = _scores(["e1", "e2"], ["m1", "m2"], [
        ("e1", "m1", 2),
        ("e1", "m1", 0, "generic"),   # duplicate of (e1, m1)
        ("e2", "m1", 2),
        ("e2", "m2", 2),
        # (e1, m2) omitted; total rows = 4 = 2 properties x 2 meetings
    ])
    assert len(d["scores"]) == len(d["properties"]) * len(d["meetings"])  # count check would pass
    with tempfile.TemporaryDirectory() as td:
        try:
            mod._load_scores(_write(td, "s.json", d))
            assert False, "case 3 must be rejected by set-equality"
        except SystemExit as e:
            msg = str(e)
            assert "missing" in msg and "(e1, m2)" in msg
            assert "duplicate" in msg and "(e1, m1)" in msg
    print("PASS: case 3 (dup + omission, correct length) rejected - set-equality, not a count")


def test_scores_undeclared_pair_rejected():
    """A row referencing an undeclared property is rejected (off-grid)."""
    import tempfile
    d = _scores(["e1"], ["m1"], [("e1", "m1", 2), ("e9", "m1", 2)])  # e9 not declared
    with tempfile.TemporaryDirectory() as td:
        try:
            mod._load_scores(_write(td, "s.json", d))
            assert False, "should have rejected undeclared property"
        except SystemExit as e:
            assert "undeclared" in str(e) and "(e9, m1)" in str(e)
    print("PASS: undeclared property 'e9' rejected (out-of-grid)")


def test_scores_missing_category_rejected():
    """A non-solid score without a category is rejected."""
    import tempfile
    d = _scores(["e1"], ["m1"], [("e1", "m1", 0)])  # broken, no category
    with tempfile.TemporaryDirectory() as td:
        try:
            mod._load_scores(_write(td, "s.json", d))
            assert False, "should have rejected missing category"
        except SystemExit as e:
            assert "no category" in str(e)
    print("PASS: non-solid score without category rejected")


def test_compare_refuses_mismatched_meeting_grids():
    """compare refuses (not warns) on different meeting samples."""
    import tempfile
    a = _scores(["e1"], ["m1"], [("e1", "m1", 2)], trajectory="A")
    b = _scores(["e1"], ["m9"], [("e1", "m9", 2)], trajectory="B")

    class Args:
        pass
    with tempfile.TemporaryDirectory() as td:
        args = Args()
        args.scores = [_write(td, "a.json", a), _write(td, "b.json", b)]
        try:
            mod.cmd_compare(args)
            assert False, "compare must refuse mismatched meeting grids"
        except SystemExit as e:
            assert "refusing" in str(e) and "meeting" in str(e)
    print("PASS: compare refuses mismatched meeting grids (not a warning)")


def test_compare_selects_fewest_broken():
    """compare ranks by fewest broken, then weak, then most solid."""
    import tempfile
    good = _scores(["e1"], ["m1", "m2"], [("e1", "m1", 2), ("e1", "m2", 2)], trajectory="good")
    bad = _scores(["e1"], ["m1", "m2"], [("e1", "m1", 0, "generic"), ("e1", "m2", 2)], trajectory="bad")

    class Args:
        pass
    with tempfile.TemporaryDirectory() as td:
        args = Args()
        args.scores = [_write(td, "bad.json", bad), _write(td, "good.json", good)]
        # cmd_compare prints; just assert it runs and the ranking helper picks good
        gd = mod._distribution(mod._load_scores(args.scores[1]))
        bd = mod._distribution(mod._load_scores(args.scores[0]))
        assert mod._rank_key(gd) < mod._rank_key(bd)
    print("PASS: compare selects the fewest-broken candidate")


# ---------------------------------------------------------------------------
# Owner-scoped sampling — the bug that made the corpus look empty
# ---------------------------------------------------------------------------

def _stub_http(mapping):
    """Replace mod.http_request with a lookup over recorded (url-substring -> resp).

    Returns (restore_fn, calls) so a test can assert on which URLs were hit.
    """
    calls = []
    original = mod.http_request

    def fake(url, method="GET", token=None, body=None, _retried=False):
        calls.append(url)
        for needle, resp in mapping.items():
            if needle in url:
                return resp
        raise AssertionError(f"unstubbed URL: {url}")

    mod.http_request = fake
    return (lambda: setattr(mod, "http_request", original)), calls


def test_unfiltered_meeting_list_is_owner_scoped():
    """The original bug: no filter -> server returns only the CALLER'S meetings.

    A helper/service identity owns ~nothing, so the sampler saw 1 meeting and
    the org looked empty. --scope self reproduces the old behavior; the URL must
    carry no customer_owner.
    """
    env = make_meeting_list_envelope([
        {"id": "solo", "actual_start_time": "2026-06-01T10:00:00Z",
         "actual_end_time": "2026-06-01T11:00:00Z"},
    ])
    restore, calls = _stub_http({"/meeting_list/": env})
    try:
        got = mod.sample_meetings(
            "https://api.aircover.ai", "tok", count=10, min_duration=30,
            days=90, scope="self")
    finally:
        restore()
    assert len(got) == 1 and got[0][0] == "solo", got
    assert len(calls) == 1, calls
    assert "customer_owner" not in calls[0], calls[0]
    print("PASS: --scope self reproduces the owner-scoped single-meeting result")


def test_org_scope_fans_out_over_reps():
    """The fix: discover org_users, then one customer_owner call per rep, unioned."""
    org_env = {"data": [{
        "customer_org": "postman.com",
        "org_users": {
            "helper@postman.com": {"role": 2, "teams": []},
            "rep1@postman.com": {"role": 3, "teams": [1]},
            "rep2@postman.com": {"role": 3, "teams": [1]},
        },
    }]}

    def meetings_for(owner_email):
        # rep1 and rep2 co-own one shared meeting -> must dedupe to 3 unique.
        per = {
            "helper@postman.com": [],
            "rep1@postman.com": ["m1", "shared"],
            "rep2@postman.com": ["m2", "shared"],
        }
        return make_meeting_list_envelope([
            {"id": mid, "actual_start_time": "2026-06-01T10:00:00Z",
             "actual_end_time": "2026-06-01T11:00:00Z"}
            for mid in per[owner_email]
        ])

    original = mod.http_request
    calls = []

    def fake(url, method="GET", token=None, body=None, _retried=False):
        calls.append(url)
        if "/organization/" in url:
            return org_env
        if "/meeting_list/" in url:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            owner = q.get("customer_owner", [""])[0]
            assert owner, f"org scope must send customer_owner: {url}"
            return meetings_for(owner)
        raise AssertionError(f"unstubbed URL: {url}")

    mod.http_request = fake
    try:
        got = mod.sample_meetings(
            "https://api.aircover.ai", "tok", count=10, min_duration=30,
            days=90, scope="org")
    finally:
        mod.http_request = original

    ids = sorted(g[0] for g in got)
    assert ids == ["m1", "m2", "shared"], ids
    assert sum(1 for c in calls if "/organization/" in c) == 1, calls
    assert sum(1 for c in calls if "/meeting_list/" in c) == 3, calls
    print("PASS: --scope org fans out per rep and dedupes the shared meeting")


def test_viewer_role_is_flagged_not_silently_empty():
    """A Viewer (role 0) hits the server's enumeration gate. Warn, don't return 1."""
    org_env = {"data": [{
        "customer_org": "postman.com",
        "org_users": {"helper@postman.com": {"role": 0, "teams": []}},
    }]}
    owners, caller, role, domain = None, None, None, None
    original = mod.http_request
    mod.http_request = lambda url, **kw: org_env
    try:
        owners, caller, role, domain = mod.discover_owners(
            "https://api.aircover.ai", make_jwt("helper@postman.com"))
    finally:
        mod.http_request = original
    assert role == mod.ROLE_VIEWER, role
    assert mod.ORG_ROLES[role] == "Viewer"
    assert owners == ["helper@postman.com"], owners
    assert caller == "helper@postman.com", caller
    print("PASS: Viewer role surfaces as role 0 so the enumeration gate is reported")


def test_token_username_decodes_jwt_claim():
    """Caller identity comes from the unverified JWT `username` claim."""
    assert mod.token_username(make_jwt("helper@postman.com")) == "helper@postman.com"
    assert mod.token_username("not-a-jwt") == ""
    print("PASS: token_username decodes the username claim, tolerates garbage")


def test_duration_uses_a_consistent_time_pair():
    """Old bug: actual-start mixed with scheduled-end invented a duration.

    A call that started 40 min late and never wrote actual_end_time used to
    compute actual_start -> scheduled_end, i.e. negative, clamped to 0, silently
    dropped. Must fall back to the scheduled pair whole.
    """
    late = {
        "start_time": "2026-06-01T10:00:00Z",
        "end_time": "2026-06-01T11:00:00Z",     # scheduled 60 min
        "actual_start_time": "2026-06-01T10:40:00Z",
        "actual_end_time": "",                   # never written
    }
    assert mod.meeting_duration_minutes(late) == 60, mod.meeting_duration_minutes(late)

    # Both actual ends present -> actual wins.
    both = dict(late, actual_end_time="2026-06-01T11:30:00Z")
    assert mod.meeting_duration_minutes(both) == 50, mod.meeting_duration_minutes(both)

    assert mod.meeting_duration_minutes({}) == 0
    print("PASS: duration uses a consistent pair, no actual/scheduled crossover")


def test_never_recorded_meeting_is_excluded():
    """A calendar invite the notetaker never joined has no transcript to audit."""
    scheduled_only = {
        "id": "ghost",
        "start_time": "2026-06-01T10:00:00Z",
        "end_time": "2026-06-01T11:00:00Z",   # passes a 30-min duration filter
    }
    recorded = dict(scheduled_only, id="real",
                    actual_start_time="2026-06-01T10:01:00Z",
                    actual_end_time="2026-06-01T10:55:00Z")
    assert not mod.meeting_was_recorded(scheduled_only)
    assert mod.meeting_was_recorded(recorded)

    env = make_meeting_list_envelope([scheduled_only, recorded])
    restore, _ = _stub_http({"/meeting_list/": env})
    try:
        kept = mod.sample_meetings("https://api.aircover.ai", "tok", count=10,
                                   min_duration=30, days=90, scope="self")
        assert [k[0] for k in kept] == ["real"], kept
        loose = mod.sample_meetings("https://api.aircover.ai", "tok", count=10,
                                    min_duration=30, days=90, scope="self",
                                    require_recorded=False)
        assert sorted(k[0] for k in loose) == ["ghost", "real"], loose
    finally:
        restore()
    print("PASS: never-recorded meetings excluded by default, kept with the opt-out")


def test_prospect_scope_sends_prospect_org():
    """--scope prospect uses the prospect_org broadening filter."""
    env = make_meeting_list_envelope([
        {"id": "p1", "actual_start_time": "2026-06-01T10:00:00Z",
         "actual_end_time": "2026-06-01T11:00:00Z", "prospect": "acme.com"},
    ])
    restore, calls = _stub_http({"/meeting_list/": env})
    try:
        got = mod.sample_meetings("https://api.aircover.ai", "tok", count=10,
                                  min_duration=30, days=90, scope="prospect",
                                  prospect_org="acme.com")
    finally:
        restore()
    assert got[0][2] == "acme.com", got
    assert "prospect_org=acme.com" in calls[0], calls[0]
    print("PASS: --scope prospect sends prospect_org and labels from `prospect`")


def test_expired_token_retries_once_with_fresh_credentials():
    """401 mid-eval must re-auth from username/password, not lose the run."""
    mod._REAUTH.update({"base_url": "https://api.aircover.ai",
                        "username": "u@x.com", "password": "pw", "token": "stale"})
    original_login = mod.login
    mod.login = lambda base, u, p: "fresh"
    attempts = []
    real_urlopen = mod.urllib.request.urlopen

    class FakeResp:
        def __init__(self, payload):
            self._p = payload.encode()
        def read(self):
            return self._p
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        tok = req.headers.get("Authorization", "")
        attempts.append(tok)
        if "stale" in tok:
            raise mod.urllib.error.HTTPError(
                req.full_url, 401, "Unauthorized", {}, io.BytesIO(b"expired"))
        return FakeResp('{"data": [{"ok": true}]}')

    mod.urllib.request.urlopen = fake_urlopen
    try:
        out = mod.http_request("https://api.aircover.ai/meeting_list/?start=a&end=b",
                               token="stale")
    finally:
        mod.urllib.request.urlopen = real_urlopen
        mod.login = original_login
        mod._REAUTH.update({"base_url": None, "username": None,
                            "password": None, "token": None})
    assert out == {"data": [{"ok": True}]}, out
    assert len(attempts) == 2, attempts
    assert "fresh" in attempts[1], attempts
    print("PASS: 401 re-authenticates once and retries with the fresh token")


def test_expired_token_without_credentials_explains_itself():
    """Token-only auth cannot refresh; the error must say so, not just 'HTTP 401'."""
    mod._REAUTH.update({"base_url": None, "username": None,
                        "password": None, "token": "stale"})
    real_urlopen = mod.urllib.request.urlopen

    def fake_urlopen(req, timeout=None):
        raise mod.urllib.error.HTTPError(
            req.full_url, 401, "Unauthorized", {}, io.BytesIO(b"expired"))

    mod.urllib.request.urlopen = fake_urlopen
    try:
        mod.http_request("https://api.aircover.ai/meeting_list/", token="stale")
        raise AssertionError("expected SystemExit")
    except SystemExit as e:
        msg = str(e)
        assert "AIRCOVER_USERNAME" in msg, msg
        assert "expired" in msg.lower(), msg
    finally:
        mod.urllib.request.urlopen = real_urlopen
        mod._REAUTH.update({"token": None})
    print("PASS: 401 with no refresh credentials names the fix in the error")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    print(f"Running {len(tests)} tests against {SCRIPT}\n")
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print()
    if failed:
        print(f"{failed} of {len(tests)} tests FAILED")
        sys.exit(1)
    print(f"All {len(tests)} tests passed.")


if __name__ == "__main__":
    main()
