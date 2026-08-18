#!/usr/bin/env python3
"""Pull transcripts, evaluate agents, and push revised configs to Aircover.

Designed to be driven by Claude Code for autonomous agent optimization loops.

Commands
--------
  eval          Sample N random 30+ min meetings, pull transcripts + agent
                results, package into an output directory.
  get-agent     Download the current agent config as JSON.
  update-agent  Upload a revised agent config from a local JSON file.

Authentication
--------------
  export AIRCOVER_TOKEN="eyJ..."
  # — or —
  export AIRCOVER_USERNAME="you@aircover.ai"
  export AIRCOVER_PASSWORD="..."

Examples
--------
  # Baseline eval: sample 10 meetings, run agent, save results
  ./agent_optimize.py eval --agent abc123 --count 10

  # Eval with specific meetings added to the random sample
  ./agent_optimize.py eval --agent abc123 --count 10 \
      --include "2026-06-01T10:00:00.000Z/123456" "2026-06-02T14:00:00.000Z/789012"

  # Download current agent config
  ./agent_optimize.py get-agent --agent abc123

  # Push a revised config
  ./agent_optimize.py update-agent --agent abc123 --from revised_agent.json

  # Re-eval with --mode fresh to force fresh agent runs after an update.
  # A config edit does NOT invalidate the cache (keyed by template id only),
  # so --mode cached would return the OLD pre-change output.
  ./agent_optimize.py eval --agent abc123 --mode fresh \
      --meeting-list previous_eval/meeting_ids.txt

No third-party dependencies — uses only the Python standard library.
"""

import argparse
import datetime
import json
import os
import random
import sys
from collections import Counter
import urllib.error
import urllib.parse
import urllib.request

STAGES = {
    "develop": "https://devapi.aircover.ai",
    "dev": "https://devapi.aircover.ai",
    "staging": "https://stageapi.aircover.ai",
    "stage": "https://stageapi.aircover.ai",
    "prod": "https://api.aircover.ai",
    "production": "https://api.aircover.ai",
}

HEADERS_BASE = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def eprint(*args):
    print(*args, file=sys.stderr)


# Set by resolve_token() when username/password are available, so an expired
# access token can be re-minted mid-run instead of losing the whole sample.
# Aircover access tokens are short-lived (~15 min), which is shorter than a
# 10-meeting fresh eval takes.
_REAUTH = {"base_url": None, "username": None, "password": None, "token": None}


def _try_reauth():
    """Re-mint the access token from stored credentials. Returns a token or None."""
    if not (_REAUTH["username"] and _REAUTH["password"] and _REAUTH["base_url"]):
        return None
    eprint("  Access token rejected; re-authenticating...")
    try:
        token = login(_REAUTH["base_url"], _REAUTH["username"], _REAUTH["password"])
    except SystemExit as e:
        eprint(f"  Re-authentication failed: {e}")
        return None
    _REAUTH["token"] = token
    return token


def current_token():
    """The freshest token we hold (re-auth may have replaced the original)."""
    return _REAUTH["token"]


def http_request(url, method="GET", token=None, body=None, _retried=False):
    """Make an HTTP request and return parsed JSON.

    On a 401 (expired token) this re-authenticates once from AIRCOVER_USERNAME/
    AIRCOVER_PASSWORD if they are set, then retries. With only AIRCOVER_TOKEN
    set there is nothing to refresh from, so the error is reported plainly --
    including the hint, because "HTTP 401" three meetings into a ten-meeting
    fresh eval is otherwise a silent loss of everything already paid for.
    """
    headers = dict(HEADERS_BASE)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, headers=headers, method=method, data=data)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        if e.code == 401 and token and not _retried:
            fresh = _try_reauth()
            if fresh:
                return http_request(url, method=method, token=fresh, body=body,
                                    _retried=True)
            raise SystemExit(
                f"HTTP 401 from {method} {url}\n{detail[:2000]}\n"
                "The access token has expired and there are no credentials to "
                "refresh from. Aircover access tokens are short-lived (~15 min), "
                "shorter than a multi-meeting eval takes. Set AIRCOVER_USERNAME "
                "and AIRCOVER_PASSWORD instead of AIRCOVER_TOKEN so the run can "
                "re-authenticate itself mid-flight."
            )
        raise SystemExit(f"HTTP {e.code} from {method} {url}\n{detail[:2000]}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Network error reaching {url}: {e.reason}")
    return json.loads(raw) if raw.strip() else {}


def login(base_url, username, password):
    """Exchange username/password for an access token."""
    qs = urllib.parse.urlencode({"username": username, "password": password})
    url = f"{base_url}/login/?{qs}"
    data = http_request(url)
    candidates = [data]
    if isinstance(data.get("data"), dict):
        candidates.append(data["data"])
    if isinstance(data.get("data"), list) and data["data"]:
        candidates.append(data["data"][0])
    for obj in candidates:
        if not isinstance(obj, dict):
            continue
        for key in ("access_token", "accessToken", "token"):
            if obj.get(key):
                return obj[key]
    raise SystemExit(
        "Logged in but could not find an access token in the response:\n"
        + json.dumps(data, indent=2)[:2000]
    )


def resolve_token(base_url):
    username = os.environ.get("AIRCOVER_USERNAME")
    password = os.environ.get("AIRCOVER_PASSWORD")
    # Stash credentials (if any) so an expired token can be re-minted mid-run.
    _REAUTH["base_url"] = base_url
    _REAUTH["username"] = username
    _REAUTH["password"] = password

    token = os.environ.get("AIRCOVER_TOKEN")
    if token:
        _REAUTH["token"] = token
        if not (username and password):
            eprint("Note: using AIRCOVER_TOKEN with no AIRCOVER_USERNAME/PASSWORD. "
                   "Access tokens are short-lived (~15 min); a long eval that "
                   "outlives the token cannot refresh itself.")
        return token
    if username and password:
        eprint(f"Logging in as {username}...")
        token = login(base_url, username, password)
        _REAUTH["token"] = token
        return token
    raise SystemExit(
        "No credentials found. Set AIRCOVER_TOKEN, or set both "
        "AIRCOVER_USERNAME and AIRCOVER_PASSWORD."
    )


def safe_filename(s):
    return s.replace("/", "_").replace(":", "-")


def parse_iso(s):
    """Parse an ISO 8601 / RFC 3339 timestamp to a datetime object."""
    if not s:
        return None
    # Handle various suffix styles
    s = s.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def meeting_duration_minutes(meeting):
    """Compute meeting duration in minutes from the response object.

    Uses a CONSISTENT pair. The previous version took actual-start OR
    scheduled-start independently of actual-end OR scheduled-end, so a meeting
    that started late and never had `actual_end_time` written mixed an actual
    start with a scheduled end and reported a duration that never happened --
    sometimes negative, clamped to 0, and silently dropped from the sample.
    Prefer the actual pair when BOTH ends are present; otherwise fall back to
    the scheduled pair whole.
    """
    a_start = parse_iso(meeting.get("actual_start_time"))
    a_end = parse_iso(meeting.get("actual_end_time"))
    if a_start and a_end:
        return max((a_end - a_start).total_seconds() / 60.0, 0)
    s_start = parse_iso(meeting.get("start_time"))
    s_end = parse_iso(meeting.get("end_time"))
    if s_start and s_end:
        return max((s_end - s_start).total_seconds() / 60.0, 0)
    return 0


def meeting_was_recorded(meeting):
    """True if the notetaker actually joined, i.e. a transcript can exist.

    `actual_start_time` is written when the live meeting starts. A calendar
    invite that nobody attended, or that the bot never joined, carries only the
    scheduled window -- it will pass a duration filter on its scheduled length
    while having no transcript to audit. Duration alone is a bad proxy for
    "auditable call"; this is the real gate.
    """
    return bool(meeting.get("actual_start_time"))


# ---------------------------------------------------------------------------
# API wrappers
# ---------------------------------------------------------------------------

def fetch_meeting_list(base_url, token, start_date, end_date,
                       customer_owner=None, prospect_org=None, quiet=False):
    """GET /meeting_list/ with required start/end date range.

    CRITICAL: with no broadening filter this endpoint is OWNER-SCOPED, not
    org-scoped. Server-side (`meeting.ReadMeetingsByUser`) an unfiltered call
    resolves to `ReadMeetingsByOwner(filters, ad.Username)` -- it lists only
    the meetings OWNED BY THE CALLING USER. A service identity that never sits
    on calls (an integration/helper account) therefore gets a near-empty list
    even though its token can read every meeting in the org individually.
    That is scope, not permissions, and no token swap fixes it.

    `customer_owner` is the broadening filter: any non-Viewer may scope to any
    rep in the org. Fan out over the org's reps and union the results to get
    org-wide coverage. See `sample_meetings`.
    """
    params = {"start": start_date, "end": end_date}
    if customer_owner:
        params["customer_owner"] = customer_owner
    if prospect_org:
        params["prospect_org"] = prospect_org
    qs = urllib.parse.urlencode(params)
    url = f"{base_url}/meeting_list/?{qs}"
    if not quiet:
        scope = customer_owner or prospect_org or "(caller's own meetings only)"
        eprint(f"Fetching meeting list ({start_date} to {end_date}) scope={scope}...")
    return http_request(url, token=token)


def fetch_org(base_url, token, customer_org=None):
    """GET /organization/ -- returns the full org object.

    Routed as `isVerified(req, organizationGet)`, so ANY verified user in the
    org may call it; it is not admin-gated. The payload carries `org_users`
    (email -> {role, teams, ...}) and `org_teams`, which is how we discover
    whose meeting timelines to walk.
    """
    params = {}
    if customer_org:
        params["customer_org"] = customer_org
    qs = urllib.parse.urlencode(params)
    url = f"{base_url}/organization/" + (f"?{qs}" if qs else "")
    return http_request(url, token=token)


def fetch_transcript(base_url, token, meeting_id):
    qs = urllib.parse.urlencode({"meeting_id": meeting_id})
    url = f"{base_url}/transcript/?{qs}"
    return http_request(url, token=token)


def fetch_agent_results(base_url, token, meeting_id, agent_id, refresh=False,
                        cache_only=False, preview=False):
    """Run or read an agent against a meeting.

    Side-effect awareness (critical for customer accounts):
      - A bare GET (no flags) on a NEVER-RUN meeting will execute the LLM,
        spend the org's token pool, AND persist the result. It is NOT a
        read-only operation.
      - cache_only=True  -> read-only. Returns 404 ("no cached results") if the
        meeting has never been run. Never spends tokens, never persists.
      - preview=True ALONE -> does NOT bust the cache. The server's cache
        short-circuit is gated only on refresh, so preview alone returns the
        STALE cached result on any meeting that has one. Always pair it with
        refresh=True (that is what --mode fresh does).
      - refresh=True      -> forces a fresh LLM run and persists (overwrites
        cache). Use on re-eval rounds after a config change.
    """
    params = {"meeting_id": meeting_id, "template_id": agent_id}
    if refresh:
        params["refresh"] = "true"
    if cache_only:
        params["cache_only"] = "true"
    if preview:
        params["preview"] = "true"
    qs = urllib.parse.urlencode(params)
    url = f"{base_url}/transcript/coaching/?{qs}"
    return http_request(url, token=token)


def fetch_agent_config(base_url, token, agent_id):
    """GET /coaching-templates/?id= to pull the full agent config."""
    qs = urllib.parse.urlencode({"id": agent_id})
    url = f"{base_url}/coaching-templates/?{qs}"
    return http_request(url, token=token)


def update_agent_config(base_url, token, agent_id, config):
    """PUT /coaching-templates/?id= to push an updated agent config."""
    qs = urllib.parse.urlencode({"id": agent_id})
    url = f"{base_url}/coaching-templates/?{qs}"
    eprint(f"Pushing updated agent config to {url}...")
    return http_request(url, method="PUT", token=token, body=config)


# ---------------------------------------------------------------------------
# Identity and owner discovery
# ---------------------------------------------------------------------------

# server/auth/organization.go role constants. Role 0 (Viewer) is the zero value,
# so an unknown user reads as Viewer -- the Viewer enumeration gate then collapses
# any broadening filter back to "meetings I personally attended".
ORG_ROLES = {
    -1: "NotPresent",
    0: "Viewer",
    1: "Owner",
    2: "Admin",
    3: "Editor",
    4: "Manager",
    5: "GlobalViewer",
}
ROLE_VIEWER = 0


def token_username(token):
    """Read the `username` claim out of a JWT payload without verifying it.

    Local base64url decode only -- no network, no signature check. We only need
    the caller's identity to look up its own role in the org payload and to
    report which identity the sample was drawn as.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        import base64
        claims = json.loads(base64.urlsafe_b64decode(payload.encode()).decode("utf-8"))
        return claims.get("username") or ""
    except Exception:
        return ""


def discover_owners(base_url, token, max_owners=None):
    """Return (owners, caller, caller_role, org_domain) for org-wide sampling.

    `owners` is every email in `org_users`, which is the set of identities whose
    meeting timelines `customer_owner` can address.
    """
    org = fetch_org(base_url, token)
    data = org.get("data") if isinstance(org, dict) else None
    if isinstance(data, list) and data:
        org_obj = data[0]
    elif isinstance(data, dict):
        org_obj = data
    else:
        org_obj = org if isinstance(org, dict) else {}

    org_users = org_obj.get("org_users") or {}
    if not isinstance(org_users, dict) or not org_users:
        raise SystemExit(
            "GET /organization/ returned no org_users, so there is no rep list to "
            "fan out over. Pass --owners <email...> or --prospect-org explicitly."
        )

    caller = token_username(token)
    caller_role = org_users.get(caller, {}).get("role", ROLE_VIEWER) if caller else None

    owners = sorted(org_users.keys())
    org_domain = org_obj.get("customer_org") or org_obj.get("id") or ""
    if max_owners and len(owners) > max_owners:
        eprint(f"  Capping owner fanout at {max_owners} of {len(owners)} reps (--max-owners).")
        owners = owners[:max_owners]
    return owners, caller, caller_role, org_domain


# ---------------------------------------------------------------------------
# Meeting sampling
# ---------------------------------------------------------------------------

def _unwrap_meeting_list(resp):
    """Pull the meetings array out of the codebase-wide Responses envelope.

    Shape: {"data": [ [ {meeting}, ... ] ]} -- data is a list whose FIRST
    element is the meetings array (doubly wrapped).
    """
    if isinstance(resp, dict) and resp.get("errors"):
        raise SystemExit(f"API returned errors: {resp['errors']}")
    data = resp.get("data") if isinstance(resp, dict) else resp
    if isinstance(data, list):
        meetings = data[0] if data else []
    elif isinstance(data, dict):
        meetings = data.get("meetings", [])
    else:
        meetings = []
    if not isinstance(meetings, list):
        raise SystemExit(
            f"Unexpected meeting list response shape. "
            f"Expected data[0] to be a list, got {type(meetings)}. "
            f"Raw keys: {list(resp.keys()) if isinstance(resp, dict) else 'n/a'}"
        )
    return meetings


def _meeting_id(m):
    """Meeting id, preferring explicit fields, else the start_time/room composite.

    (`meetingListGet` only requires room + start_time, so some meetings carry an
    empty `id`; GetMeeting accepts the composite form.)
    """
    mid = m.get("meeting_id") or m.get("id") or ""
    if not mid and m.get("start_time") and m.get("room"):
        mid = f'{m.get("start_time")}/{m.get("room")}'
    return mid


def collect_meetings(base_url, token, start_str, end_str, owners=None,
                     prospect_org=None):
    """Union the meeting lists across a set of owners, deduped by meeting id.

    Returns (meetings, per_owner_counts). An empty/None `owners` means one
    unfiltered call, which the server scopes to the CALLER'S OWN meetings.
    """
    seen = {}
    per_owner = {}
    if prospect_org:
        found = _unwrap_meeting_list(fetch_meeting_list(
            base_url, token, start_str, end_str, prospect_org=prospect_org))
        for m in found:
            mid = _meeting_id(m)
            if mid:
                seen.setdefault(mid, m)
        per_owner[f"prospect:{prospect_org}"] = len(found)
        return list(seen.values()), per_owner

    if not owners:
        found = _unwrap_meeting_list(fetch_meeting_list(base_url, token, start_str, end_str))
        for m in found:
            mid = _meeting_id(m)
            if mid:
                seen.setdefault(mid, m)
        per_owner["(caller)"] = len(found)
        return list(seen.values()), per_owner

    eprint(f"Fanning out over {len(owners)} owners ({start_str[:10]} to {end_str[:10]})...")
    for idx, owner in enumerate(owners, 1):
        try:
            found = _unwrap_meeting_list(fetch_meeting_list(
                base_url, token, start_str, end_str, customer_owner=owner, quiet=True))
        except SystemExit as e:
            # One rep failing must not sink the whole sample.
            eprint(f"  [{idx}/{len(owners)}] {owner}: FAILED ({e})")
            per_owner[owner] = -1
            continue
        per_owner[owner] = len(found)
        new = 0
        for m in found:
            mid = _meeting_id(m)
            if mid and mid not in seen:
                seen[mid] = m
                new += 1
        eprint(f"  [{idx}/{len(owners)}] {owner}: {len(found)} meetings ({new} new)")
    return list(seen.values()), per_owner


def sample_meetings(base_url, token, count, min_duration, days, team_id=None,
                    include_ids=None, owners=None, prospect_org=None,
                    scope="org", max_owners=None, require_recorded=True):
    """Fetch meetings across the org, filter, and return a random sample.

    Returns a list of (meeting_id, duration_min, title/prospect) tuples.

    `scope`:
      "org"  (default) -- discover the org's reps via GET /organization/ and fan
                          out with `customer_owner=<rep>`. This is the only way
                          to see the org's whole corpus; an unfiltered call is
                          scoped to the caller's OWN meetings server-side.
      "self"           -- one unfiltered call (caller's own meetings only).
      "explicit"       -- fan out over the `owners` list you passed.
      "prospect"       -- one call filtered to `prospect_org`.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    start = now - datetime.timedelta(days=days)
    start_str = start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_str = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # team_ids in the response are ints; --team arrives as a string. Build a
    # set of candidate forms (int + str) so the membership test matches either.
    team_match = None
    if team_id:
        team_match = {str(team_id)}
        try:
            team_match.add(int(team_id))
        except (TypeError, ValueError):
            pass

    if scope == "prospect":
        if not prospect_org:
            raise SystemExit("scope=prospect requires --prospect-org.")
        meetings, per_owner = collect_meetings(
            base_url, token, start_str, end_str, prospect_org=prospect_org)
    elif scope == "self":
        eprint("Scope: caller's own meetings only (--scope self).")
        meetings, per_owner = collect_meetings(base_url, token, start_str, end_str)
    elif scope == "explicit":
        if not owners:
            raise SystemExit("scope=explicit requires --owners <email...>.")
        meetings, per_owner = collect_meetings(
            base_url, token, start_str, end_str, owners=owners)
    else:
        discovered, caller, caller_role, org_domain = discover_owners(
            base_url, token, max_owners=max_owners)
        role_name = ORG_ROLES.get(caller_role, f"unknown({caller_role})")
        eprint(f"Org: {org_domain or '(unknown)'} | caller: {caller or '(unknown)'} "
               f"| role: {role_name}")
        if caller_role == ROLE_VIEWER:
            # The Viewer enumeration gate (server/meeting_http.go) refilters any
            # broadening filter down to meetings the caller personally attended,
            # so the fanout below will return roughly nothing and it will look
            # like the org has no calls. Say so instead of returning a silent 1.
            eprint(
                "\n  WARNING: this identity's org role is Viewer (0). The server's\n"
                "  Viewer enumeration gate refilters customer_owner/attendee_emails/\n"
                "  prospect_org results down to meetings the caller personally\n"
                "  attended, so an org-wide fanout will come back near-empty.\n"
                "  Fix: raise this identity to Editor/Manager/Admin/GlobalViewer in\n"
                "  org settings, or pass --meeting-list with explicit meeting IDs.\n"
            )
        meetings, per_owner = collect_meetings(
            base_url, token, start_str, end_str, owners=discovered)

    eprint(f"  {len(meetings)} unique meetings returned across {len(per_owner)} scope(s)")

    # Filter. Track why things dropped -- a silent 0 here is the failure mode
    # that made this tool look like the org had no calls.
    qualified = []
    dropped_no_id = dropped_short = dropped_not_recorded = dropped_team = 0
    for m in meetings:
        mid = _meeting_id(m)
        if not mid:
            dropped_no_id += 1
            continue
        if require_recorded and not meeting_was_recorded(m):
            dropped_not_recorded += 1
            continue
        dur = meeting_duration_minutes(m)
        if dur < min_duration:
            dropped_short += 1
            continue
        # Optional team filter. team_ids may be ints or strings; match either.
        if team_match is not None:
            m_teams = m.get("team_ids") or []
            if not any((t in team_match or str(t) in team_match) for t in m_teams):
                dropped_team += 1
                continue
        label = m.get("prospect") or m.get("prospect_org") or m.get("title") or mid[:40]
        qualified.append((mid, round(dur, 1), label))

    eprint(f"  {len(qualified)} meetings >= {min_duration} min and recorded")
    eprint(f"    dropped: {dropped_short} too short, {dropped_not_recorded} never "
           f"recorded (no actual_start_time), {dropped_no_id} no id, "
           f"{dropped_team} wrong team")

    if not qualified:
        eprint(
            "\n  No meetings qualified. Before assuming the org has no calls, check:\n"
            "    * scope -- an unfiltered /meeting_list/ call returns only the\n"
            "      CALLER'S OWN meetings. Use --scope org (the default) so the\n"
            "      sampler fans out over the org's reps.\n"
            "    * --days (default 30). Widen it.\n"
            "    * --min-duration (default 30). Lower it.\n"
            "    * --no-require-recorded, if you want scheduled-only meetings too.\n"
        )

    # Deduplicate any manually included IDs from the random pool
    include_ids = set(include_ids or [])
    pool = [q for q in qualified if q[0] not in include_ids]

    # Sample
    sample_count = max(0, count - len(include_ids))
    if sample_count > len(pool):
        eprint(
            f"  Warning: requested {sample_count} random meetings but only "
            f"{len(pool)} available. Using all."
        )
        sampled = pool
    else:
        sampled = random.sample(pool, sample_count)

    # Add manually included meetings (with placeholder metadata)
    for mid in include_ids:
        # Check if it's in the qualified list for metadata
        match = next((q for q in qualified if q[0] == mid), None)
        if match:
            sampled.append(match)
        else:
            sampled.append((mid, 0, "(manually included)"))

    return sampled


# ---------------------------------------------------------------------------
# Agent config parsing
# ---------------------------------------------------------------------------

def _find_template_pair(obj, depth=0):
    """Recursively descend through the Responses envelope to find the
    prompt_template / prompt_template_list_item pair.

    The codebase wraps payloads as {"data": [ ... ]} and sometimes double-wraps
    (data[0] is itself an array). This walks dicts and lists until it locates
    an object that looks like a coaching template, returning (pt, li).
    """
    if depth > 6:
        return {}, {}

    if isinstance(obj, dict):
        # Direct hit: this dict has the template pair
        pt = obj.get("prompt_template") or obj.get("promptTemplate")
        li = obj.get("prompt_template_list_item") or obj.get("promptTemplateListItem")
        if pt or li:
            return pt or {}, li or {}
        # This dict might itself BE the template (has a body field)
        if "body" in obj and ("category" in obj or "system_prompt" in str(obj.get("body", ""))):
            return obj, obj
        # Descend into "data" or any nested structure
        if "data" in obj:
            return _find_template_pair(obj["data"], depth + 1)
        # Try other dict values as a last resort
        for v in obj.values():
            if isinstance(v, (dict, list)):
                pt, li = _find_template_pair(v, depth + 1)
                if pt or li:
                    return pt, li
        return {}, {}

    if isinstance(obj, list):
        for item in obj:
            pt, li = _find_template_pair(item, depth + 1)
            if pt or li:
                return pt, li
        return {}, {}

    return {}, {}


def _unwrap_request(obj):
    """Return the bare PromptTemplateRequest the PUT handler expects:
        {"prompt_template": {...}, "prompt_template_list_item": {...}}

    Accepts either a raw GET envelope ({"data": [ {pt, li} ]}) or an already
    unwrapped object. The PUT handler unmarshals the body into a bare
    PromptTemplateRequest with TOP-LEVEL prompt_template / prompt_template_list_item.
    If handed the envelope, both fields come back zero-valued and the handler
    400s on the empty `type`. So we always normalize to the bare shape at both
    the save (get-agent) and push (update-agent) boundaries.

    Returns DEEP COPIES of the located pt/li so the caller can mutate the result
    without aliasing back into the input object. (Without this, unwrapping an
    object and editing the copy would silently edit the original too, which
    makes a before/after diff see no change.)
    """
    import copy
    pt, li = _find_template_pair(obj)
    return {
        "prompt_template": copy.deepcopy(pt) if pt else {},
        "prompt_template_list_item": copy.deepcopy(li) if li else {},
    }


def parse_agent_summary(config):
    """Parse agent config into a human-readable markdown summary for auditing.

    Handles the Responses envelope at arbitrary nesting depth. The body field
    is a JSON string that must be parsed separately.
    """
    if isinstance(config, dict) and config.get("errors"):
        return f"# Agent config error\n\n{config['errors']}\n"

    pt, li = _find_template_pair(config)
    if not pt and not li:
        return "# Agent Summary\n\nCould not locate template structure in response.\n"

    name = li.get("name", "Unknown")
    category = li.get("category") or pt.get("category", "Unknown")
    agent_id = pt.get("id") or li.get("id", "Unknown")

    # Parse the body (JSON string → dict)
    body_raw = pt.get("body", "{}")
    try:
        if isinstance(body_raw, str):
            body = json.loads(body_raw)
        else:
            body = body_raw
    except json.JSONDecodeError:
        return f"# Agent: {name}\n\nCould not parse body JSON.\n"

    system_prompt = body.get("system_prompt", "(none)")
    properties = body.get("properties", {})

    lines = [
        f"# Agent Summary: {name}",
        f"**ID:** {agent_id}",
        f"**Category:** {category}",
        f"**Properties:** {len(properties)}",
        "",
        "## System Prompt",
        "```",
        system_prompt[:2000],
        "```",
        "",
        "## Properties",
        "",
    ]

    for entry_id, prop in sorted(properties.items(), key=lambda x: x[1].get("sort_order", 0)):
        title = prop.get("title", entry_id)
        max_score = prop.get("max_score", 0)
        ptype = "Scored" if max_score > 0 else "Extraction"
        desc = prop.get("description", "(no description)")
        rubric = prop.get("scoring_rubrik", "")
        field_map = prop.get("field_mapping", "")

        lines.append(f"### {title}")
        lines.append(f"- **Entry ID:** {entry_id}")
        lines.append(f"- **Type:** {ptype} (max_score={max_score})")
        if field_map:
            lines.append(f"- **Field Mapping:** {field_map}")
        lines.append(f"- **Description:**")
        # Indent description for readability
        for dline in desc.split("\n"):
            lines.append(f"  {dline}")
        if rubric:
            lines.append(f"- **Scoring Rubric:**")
            for rline in rubric.split("\n"):
                lines.append(f"  {rline}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_eval(args, base_url, token):
    """Pull transcripts and agent results for a sample of meetings."""
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    include_ids = args.include or []

    # If a meeting list file is provided, use those IDs instead of sampling
    if args.meeting_list:
        eprint(f"Reading meeting IDs from {args.meeting_list}")
        with open(args.meeting_list, "r") as f:
            meeting_ids = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        meetings = [(mid, 0, "(from file)") for mid in meeting_ids]
    else:
        meetings = sample_meetings(
            base_url, token,
            count=args.count,
            min_duration=args.min_duration,
            days=args.days,
            team_id=args.team,
            include_ids=include_ids,
            owners=args.owners,
            prospect_org=args.prospect_org,
            scope=args.scope,
            max_owners=args.max_owners,
            require_recorded=not args.no_require_recorded,
        )

    if not meetings:
        raise SystemExit("No meetings matched the criteria.")

    # Write the meeting list for reproducibility
    id_list_path = os.path.join(out_dir, "meeting_ids.txt")
    with open(id_list_path, "w") as f:
        f.write("# Meeting IDs used in this eval run\n")
        f.write(f"# Generated: {datetime.datetime.now().isoformat()}\n")
        f.write(f"# Agent: {args.agent_id}\n")
        f.write(f"# Mode: {args.mode}\n\n")
        for mid, dur, label in meetings:
            f.write(f"{mid}  # {dur} min - {label}\n")
    eprint(f"  Wrote meeting list to {id_list_path}")

    # Pull transcripts and agent results
    manifest = []
    errors = []
    for i, (mid, dur, label) in enumerate(meetings, 1):
        eprint(f"\n[{i}/{len(meetings)}] {label} ({dur} min) — {mid}")
        base_name = safe_filename(mid)

        # Transcript
        transcript_file = f"{base_name}_transcript.json"
        try:
            eprint(f"  Fetching transcript...")
            data = fetch_transcript(base_url, token, mid)
            path = os.path.join(out_dir, transcript_file)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            eprint(f"  Wrote {path}")
        except SystemExit as e:
            eprint(f"  FAILED transcript: {e}")
            errors.append({"meeting_id": mid, "step": "transcript", "error": str(e)})
            continue

        # Agent results.
        # Mode controls side effects (important on customer accounts):
        #   cached  -> read-only; cache_only=true. 404 if never run. No tokens.
        #   preview -> fresh LLM run, NOT persisted. Spends tokens, no mutation.
        #   persist -> fresh LLM run AND saved to the live cache. Spends tokens,
        #              overwrites the customer's stored result.
        agent_file = f"{base_name}_agent_results.json"
        fetch_kwargs = {
            "cached": dict(cache_only=True),
            "fresh":   dict(refresh=True, preview=True),
            "preview": dict(refresh=True, preview=True),   # deprecated alias of fresh
            "persist": dict(refresh=True),
        }[args.mode]
        try:
            eprint(f"  Fetching agent results (mode={args.mode})...")
            agent_data = fetch_agent_results(
                base_url, token, mid, args.agent_id, **fetch_kwargs
            )
            path = os.path.join(out_dir, agent_file)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(agent_data, f, indent=2)
            eprint(f"  Wrote {path}")
        except SystemExit as e:
            # In cached mode, a 404 means this meeting has never been run.
            # That's expected and not a hard failure: note it and move on.
            if args.mode == "cached" and "404" in str(e):
                eprint(f"  No cached result (meeting never run by this agent)")
                errors.append({"meeting_id": mid, "step": "agent",
                               "error": "no cached result (never run)"})
            else:
                eprint(f"  FAILED agent results: {e}")
                errors.append({"meeting_id": mid, "step": "agent", "error": str(e)})
            agent_file = None

        manifest.append({
            "meeting_id": mid,
            "duration_min": dur,
            "label": label,
            "transcript_file": transcript_file,
            "agent_results_file": agent_file,
        })

    # Also pull the current agent config for reference.
    # Save it UNWRAPPED (PUT-ready) so this snapshot doubles as the rollback file.
    eprint(f"\nFetching agent config for {args.agent_id}...")
    try:
        raw_config = fetch_agent_config(base_url, token, args.agent_id)
        agent_config = _unwrap_request(raw_config)
        config_path = os.path.join(out_dir, "agent_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(agent_config, f, indent=2)
        eprint(f"  Wrote {config_path}")

        # Write a human-readable summary of the agent config for auditing
        summary = parse_agent_summary(agent_config)
        if summary:
            summary_path = os.path.join(out_dir, "agent_summary.md")
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary)
            eprint(f"  Wrote {summary_path}")
    except SystemExit as e:
        eprint(f"  Warning: could not fetch agent config: {e}")

    # Write manifest
    manifest_data = {
        "agent_id": args.agent_id,
        "mode": args.mode,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "min_duration": args.min_duration,
        "days_lookback": args.days,
        "meetings": manifest,
        "errors": errors,
    }
    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    eprint(f"\nDone. {len(manifest)} meetings processed, {len(errors)} errors.")
    eprint(f"Results in: {out_dir}/")

    if errors:
        eprint(f"\nErrors:")
        for err in errors:
            eprint(f"  {err['meeting_id']} ({err['step']}): {err['error']}")
        return 1
    return 0


def cmd_list_meetings(args, base_url, token):
    """Show what the sampler would pick, without running the agent on anything.

    Free and side-effect-free: it only hits /meeting_list/ and /organization/.
    Run this FIRST on any new account. It is the cheap way to prove the sampler
    can see the corpus before you spend a single agent run, and it turns "the
    tool returned 1 meeting" into a diagnosis instead of a mystery.
    """
    meetings = sample_meetings(
        base_url, token,
        count=args.count,
        min_duration=args.min_duration,
        days=args.days,
        team_id=args.team,
        include_ids=None,
        owners=args.owners,
        prospect_org=args.prospect_org,
        scope=args.scope,
        max_owners=args.max_owners,
        require_recorded=not args.no_require_recorded,
    )
    if not meetings:
        eprint("No meetings matched the criteria.")
        return 1
    print(f"\n{len(meetings)} meeting(s) sampled:\n")
    for mid, dur, label in sorted(meetings, key=lambda x: -x[1]):
        print(f"  {dur:>6} min  {label[:40]:<42} {mid}")
    if args.out_file:
        with open(args.out_file, "w", encoding="utf-8") as f:
            f.write("# Pinned meeting IDs\n")
            f.write(f"# Generated: {datetime.datetime.now().isoformat()}\n")
            f.write(f"# scope={args.scope} days={args.days} "
                    f"min_duration={args.min_duration}\n\n")
            for mid, dur, label in meetings:
                f.write(f"{mid}  # {dur} min - {label}\n")
        eprint(f"\nWrote {len(meetings)} meeting IDs to {args.out_file}")
    return 0


def cmd_get_agent(args, base_url, token):
    """Download the current agent config as a PUT-ready PromptTemplateRequest."""
    eprint(f"Fetching agent config for {args.agent_id}...")
    raw = fetch_agent_config(base_url, token, args.agent_id)
    # Save the UNWRAPPED request (bare prompt_template / prompt_template_list_item),
    # not the {"data":[...]} envelope. This is the shape PUT expects, so the
    # saved file is both human-editable and directly re-pushable (it's the
    # rollback snapshot).
    data = _unwrap_request(raw)

    out_file = args.out_file or f"agent_config_{safe_filename(args.agent_id)}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    eprint(f"Wrote {out_file}")
    return 0


# Fields the server forces/regenerates on PUT regardless of what we send.
# A dry-run diff ignores these so it doesn't cry wolf on benign churn.
# (Confirmed against coachingTemplatesPut / SaveTemplate.)
SERVER_FORCED_LIST_ITEM_FIELDS = {
    "id",            # forced to ?id=
    "meta",          # audit metadata regenerated
    "customer_org",  # set to caller's org
    "global",        # forced false for non-aircover.ai
    "category",      # copied from prompt_template.category
    "global_default",  # adjusted by visibility-transition logic
    # Tradeoff: excluding global_default means a LEGITIMATE default-flag change
    # also won't appear in the dry-run diff. Acceptable here because the loop
    # never intentionally changes the default flag; it only edits prompt/rubric
    # content. If a future workflow needs to toggle the default, surface it
    # separately rather than removing it from this set.
}


def _normalize_body(body_raw):
    """Parse the stringified body and return the property-level content that
    actually matters for a diff: system_prompt + per-property config fields.
    Strips any result/score fields (those are output, not config)."""
    try:
        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
    except (json.JSONDecodeError, TypeError):
        return {"_unparseable_body": str(body_raw)[:500]}
    if not isinstance(body, dict):
        return {"_non_dict_body": str(body)[:500]}
    props = {}
    for entry_id, prop in (body.get("properties") or {}).items():
        if not isinstance(prop, dict):
            continue
        # Keep only config fields, drop runtime output (result/score)
        props[entry_id] = {
            "title": prop.get("title"),
            "description": prop.get("description"),
            "scoring_rubrik": prop.get("scoring_rubrik"),
            "max_score": prop.get("max_score"),
            "sort_order": prop.get("sort_order"),
            "field_mapping": prop.get("field_mapping"),
            "type": prop.get("type"),
        }
    return {
        "system_prompt": body.get("system_prompt"),
        "properties": props,
    }


def _comparable_view(pt, li):
    """Build the diff-relevant view of a template: the body config plus the
    list-item fields we actually control (excluding server-forced churn)."""
    li_controlled = {
        k: v for k, v in (li or {}).items()
        if k.lower() not in SERVER_FORCED_LIST_ITEM_FIELDS
    }
    return {
        "body": _normalize_body((pt or {}).get("body", "{}")),
        "list_item_controlled": li_controlled,
    }


def _diff_dicts(before, after, path=""):
    """Recursively diff two JSON-able structures. Returns a list of change
    strings. Order-independent for dicts; positional for lists."""
    changes = []
    if type(before) != type(after):
        changes.append(f"{path}: type {type(before).__name__} -> {type(after).__name__}")
        return changes
    if isinstance(before, dict):
        for key in sorted(set(before) | set(after)):
            p = f"{path}.{key}" if path else key
            if key not in before:
                changes.append(f"{p}: ADDED")
            elif key not in after:
                changes.append(f"{p}: REMOVED")
            else:
                changes.extend(_diff_dicts(before[key], after[key], p))
    elif isinstance(before, list):
        if len(before) != len(after):
            changes.append(f"{path}: list length {len(before)} -> {len(after)}")
        for i in range(min(len(before), len(after))):
            changes.extend(_diff_dicts(before[i], after[i], f"{path}[{i}]"))
    else:
        if before != after:
            b = str(before)
            a = str(after)
            if len(b) > 80:
                b = b[:77] + "..."
            if len(a) > 80:
                a = a[:77] + "..."
            changes.append(f"{path}: {b!r} -> {a!r}")
    return changes


def dry_run_diff(base_url, token, agent_id, new_config):
    """Pull the current agent, build the comparable view of both current and
    proposed config, and return the list of meaningful changes. No PUT."""
    current = fetch_agent_config(base_url, token, agent_id)
    cur_pt, cur_li = _find_template_pair(current)

    new_pt, new_li = _find_template_pair(new_config)
    # The new_config may be the bare PromptTemplateRequest (unwrapped); handle that.
    if not new_pt and isinstance(new_config, dict):
        new_pt = new_config.get("prompt_template", {})
        new_li = new_config.get("prompt_template_list_item", {})

    before = _comparable_view(cur_pt, cur_li)
    after = _comparable_view(new_pt, new_li)
    return _diff_dicts(before, after), cur_li, new_li


def cmd_update_agent(args, base_url, token):
    """Push a revised agent config from a local JSON file (or dry-run diff)."""
    eprint(f"Reading config from {args.from_file}...")
    with open(args.from_file, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Normalize to the bare PromptTemplateRequest the PUT handler expects.
    # Accepts either an enveloped GET response or an already-unwrapped file.
    # Without this, PUTting an enveloped {"data":[...]} body yields zero-valued
    # fields and a 400 "Invalid coaching template type".
    config = _unwrap_request(raw)

    # Guard: if unwrap couldn't find a template type, fail early with a clear
    # message rather than letting the server 400.
    li_check = config.get("prompt_template_list_item") or {}
    if not li_check.get("type"):
        raise SystemExit(
            f"Config in {args.from_file} has no resolvable "
            "prompt_template_list_item.type. Expected a coaching template "
            "(either a raw GET response or a bare PromptTemplateRequest)."
        )

    # Pre-flight: diff against the live config, ignoring server-forced churn.
    changes, cur_li, new_li = dry_run_diff(base_url, token, args.agent_id, config)

    # Safety check: warn loudly if the proposed config would drop a controlled
    # field that's currently set (the silent-unshare risk).
    dropped = []
    for k, v in (cur_li or {}).items():
        if k.lower() in SERVER_FORCED_LIST_ITEM_FIELDS:
            continue
        if v and (k not in (new_li or {}) or not new_li.get(k)):
            dropped.append(k)

    eprint("\n=== Pre-flight diff (changes you control) ===")
    if not changes:
        eprint("  No meaningful changes. Config is identical to live.")
    else:
        for c in changes:
            eprint(f"  {c}")

    if dropped:
        eprint("\n  WARNING: these currently-set fields are missing/empty in the")
        eprint("  new config and PUT will WIPE them (full-replace, no merge):")
        for k in dropped:
            eprint(f"    - {k}: currently {cur_li.get(k)!r}")
        eprint("  If unintended, copy these fields from the original config.")

    if args.dry_run:
        eprint("\n[dry-run] No PUT sent.")
        return 0

    if dropped and not args.force:
        raise SystemExit(
            "\nRefusing to PUT: the update would wipe currently-set fields "
            f"({', '.join(dropped)}). Re-run with --force to override, or fix "
            "the config to preserve them."
        )

    eprint(f"\nUpdating agent {args.agent_id}...")
    result = update_agent_config(base_url, token, args.agent_id, config)

    eprint("Update successful.")
    resp_file = f"update_response_{safe_filename(args.agent_id)}.json"
    with open(resp_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    eprint(f"Response saved to {resp_file}")
    return 0


# ---------------------------------------------------------------------------
# Scoring aggregation + best-of-K selection (offline: no network, no token)
# ---------------------------------------------------------------------------

FAILURE_CATEGORIES = {
    "hallucination",   # content not present in the transcript
    "wrong_speaker",   # rep statement scored as buyer, or misattributed
    "missed_signal",   # "not found"/empty when the call had clear signal
    "miscalibrated",   # score doesn't match what happened in the call
    "generic",         # templated/vague, not grounded in this conversation
    "format",          # line breaks, truncation, char-limit violations
    "bleed",           # content from a different property leaked in
}

SCORE_LABELS = {2: "solid", 1: "weak", 0: "broken"}


def _load_scores(path):
    """Load a scores.json and enforce a COMPLETE grid via SET-EQUALITY.

    The (property, meeting) pairs in `scores` must equal the full Cartesian
    product of the declared `properties` x `meetings`, exactly once each. This
    single set-equality check subsumes three failure modes a length/count check
    misses (notably when they co-occur and net to the right length):
      - missing pairs: an audit that silently drops the meeting it would score
        0 on gets a smaller denominator and can win best-of-K unfairly.
      - duplicate pairs: double-counted in the distribution.
      - undeclared pairs: a typo'd property/meeting id silently off-grid.
    Hard-fails naming the offending pairs. Duplicates are detected with Counter
    on the raw pair list, independent of the set, so a dup can never be silently
    swallowed by set membership.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "scores" not in data:
        raise SystemExit(f"{path}: not a scores file (missing 'scores').")
    props = data.get("properties")
    meetings = data.get("meetings")
    if not isinstance(props, list) or not isinstance(meetings, list):
        raise SystemExit(f"{path}: 'properties' and 'meetings' must both be lists.")

    pairs = []
    for i, row in enumerate(data["scores"]):
        if not all(k in row for k in ("property", "meeting", "score")):
            raise SystemExit(f"{path}: scores[{i}] missing property/meeting/score.")
        s = row["score"]
        if s not in (0, 1, 2):
            raise SystemExit(f"{path}: scores[{i}] has score {s!r}, must be 0/1/2.")
        if s < 2:
            cat = row.get("category")
            if not cat:
                raise SystemExit(
                    f"{path}: ({row['property']}, {row['meeting']}) scored {s} with no category.")
            if cat not in FAILURE_CATEGORIES:
                raise SystemExit(
                    f"{path}: ({row['property']}, {row['meeting']}) has unknown category {cat!r}. "
                    f"Use one of: {', '.join(sorted(FAILURE_CATEGORIES))}.")
        pairs.append((row["property"], row["meeting"]))

    grid = {(p, m) for p in props for m in meetings}
    seen = set(pairs)
    counts = Counter(pairs)
    duplicates = [pair for pair, n in counts.items() if n > 1]
    missing = grid - seen
    extra = seen - grid  # rows referencing an undeclared property or meeting

    def fmt(pairset):
        return ", ".join(f"({p}, {m})" for p, m in sorted(pairset))

    problems = []
    if missing:
        problems.append(f"missing {len(missing)} pair(s): {fmt(missing)}")
    if extra:
        problems.append(f"undeclared {len(extra)} pair(s): {fmt(extra)}")
    if duplicates:
        problems.append(f"duplicate {len(duplicates)} pair(s): {fmt(duplicates)}")
    if problems:
        raise SystemExit(
            f"{path}: scores is not a complete grid "
            f"({len(props)} properties x {len(meetings)} meetings = {len(grid)} cells). "
            + "; ".join(problems))
    return data


def _distribution(data):
    """Compute the distribution from a validated (grid-complete) scores dict."""
    per_prop = {}
    cats = {}
    solid = weak = broken = 0
    for row in data["scores"]:
        prop = row["property"]
        s = row["score"]
        bucket = per_prop.setdefault(prop, {"solid": 0, "weak": 0, "broken": 0})
        bucket[SCORE_LABELS[s]] += 1
        if s == 2:
            solid += 1
        elif s == 1:
            weak += 1
        else:
            broken += 1
        if s < 2:
            cat = row.get("category", "uncategorized")
            cats[cat] = cats.get(cat, 0) + 1
    return {
        "total": solid + weak + broken,
        "solid": solid, "weak": weak, "broken": broken,
        "per_property": per_prop,
        "categories": cats,
    }


def _rank_key(dist):
    """Lexicographic ordering for candidate selection, matching the tool's
    distribution philosophy: fewest broken, then fewest weak, then most solid.
    No composite average, so a regression on one axis can't be masked by a gain
    on another."""
    return (dist["broken"], dist["weak"], -dist["solid"])


def cmd_summarize(args):
    """One scores.json -> distribution + category histogram. Offline."""
    data = _load_scores(args.scores)
    dist = _distribution(data)
    agent = data.get("agent_id", "?")
    rnd = data.get("round", data.get("trajectory", "?"))
    print(f"# Score summary - agent {agent}, round/trajectory {rnd}")
    print(f"Headline: {dist['solid']} of {dist['total']} property-outputs solid "
          f"({dist['weak']} weak, {dist['broken']} broken)\n")
    print("Per-property (solid/weak/broken):")
    for prop in sorted(dist["per_property"]):
        b = dist["per_property"][prop]
        verdict = "OK" if b["broken"] == 0 and b["weak"] <= b["solid"] else (
            "NEEDS FIX" if b["broken"] else "WATCH")
        print(f"  {prop:<24} {b['solid']}/{b['weak']}/{b['broken']}   {verdict}")
    if dist["categories"]:
        print("\nFailure categories (non-solid outputs):")
        for cat, n in sorted(dist["categories"].items(), key=lambda x: -x[1]):
            print(f"  {cat:<16} {n}")
    return 0


def cmd_compare(args):
    """Multiple scores.json (best-of-K candidates) -> rank, winner, tradeoff
    matrix. Offline. Refuses on non-comparable candidates."""
    candidates = []
    for path in args.scores:
        data = _load_scores(path)
        dist = _distribution(data)
        label = data.get("trajectory", data.get("round", path))
        candidates.append({"path": path, "label": label, "data": data, "dist": dist})

    # Non-comparable candidates are a hard refusal, not a warning: comparing
    # across different property sets or meeting samples measures different tests
    # and its winner is meaningless.
    prop_sets = {frozenset(c["dist"]["per_property"]) for c in candidates}
    meeting_sets = {frozenset(c["data"].get("meetings", [])) for c in candidates}
    if len(prop_sets) > 1:
        raise SystemExit(
            "compare: candidates have different property sets; refusing. "
            "Best-of-K requires identical properties across trajectories.")
    if len(meeting_sets) > 1:
        raise SystemExit(
            "compare: candidates scored on different meeting samples; refusing. "
            "Pin --meeting-list so every trajectory scores the same meetings.")

    ranked = sorted(candidates, key=lambda c: _rank_key(c["dist"]))
    winner = ranked[0]

    print("# Best-of-K comparison\n")
    print(f"{'rank':<5}{'candidate':<14}{'solid':<7}{'weak':<7}{'broken':<8}")
    for i, c in enumerate(ranked, 1):
        d = c["dist"]
        star = "  <- winner" if c is winner else ""
        print(f"{i:<5}{str(c['label']):<14}{d['solid']:<7}{d['weak']:<7}{d['broken']:<8}{star}")

    all_props = sorted({p for c in candidates for p in c["dist"]["per_property"]})
    print("\nPer-property broken counts (lower is better):")
    print("  " + "property".ljust(24) + "".join(f"{str(c['label']):>8}" for c in candidates))
    tradeoffs = []
    for prop in all_props:
        cells = [c["dist"]["per_property"].get(prop, {"broken": 0})["broken"] for c in candidates]
        win_b = winner["dist"]["per_property"].get(prop, {"broken": 0})["broken"]
        best_b = min(cells)
        line = "  " + prop.ljust(24) + "".join(f"{x:>8}" for x in cells)
        if win_b > best_b:
            line += "  *"
            tradeoffs.append((prop, win_b, best_b, candidates[cells.index(best_b)]["label"]))
        print(line)

    print(f"\nRecommended winner: candidate {winner['label']} ({winner['path']})")
    if tradeoffs:
        print("\nTradeoffs to review (winner is not best on these properties):")
        for prop, wb, bb, who in tradeoffs:
            print(f"  - {prop}: winner has {wb} broken; candidate {who} has {bb}.")
        print("  The overall winner regressed these vs. another trajectory. "
              "Veto if a flagged property is business-critical.")
    else:
        print("No per-property regressions: the winner is at least tied as best on every property.")

    print("\nNext: dry-run the winning config before any push:")
    print(f"  python3 agent_optimize.py update-agent --agent {winner['data'].get('agent_id','<id>')} "
          f"--from <winner_config.json> --dry-run --stage <stage>")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def add_sampling_args(p):
    """Sampling flags shared by `eval` and `list-meetings`."""
    p.add_argument("--count", type=int, default=10,
                   help="Number of meetings to sample (default: 10).")
    p.add_argument("--min-duration", type=int, default=30,
                   help="Minimum meeting duration in minutes (default: 30).")
    p.add_argument("--days", type=int, default=30,
                   help="Look back N days for meetings (default: 30).")
    p.add_argument("--scope", choices=["org", "self", "explicit", "prospect"],
                   default="org",
                   help="Whose meetings to sample. "
                   "org (default): discover the org's reps via GET /organization/ "
                   "and fan out with customer_owner=<rep>, which is the only way to "
                   "see the whole corpus. "
                   "self: one unfiltered call -- the server scopes this to the "
                   "CALLER'S OWN meetings, which is near-empty for a service "
                   "identity that never sits on calls. "
                   "explicit: fan out over --owners. "
                   "prospect: filter to --prospect-org.")
    p.add_argument("--owners", nargs="*", default=None,
                   help="Explicit owner emails to fan out over (with --scope explicit).")
    p.add_argument("--prospect-org", default=None,
                   help="Prospect domain to filter to (with --scope prospect).")
    p.add_argument("--max-owners", type=int, default=None,
                   help="Cap the owner fanout at N reps (default: no cap).")
    p.add_argument("--no-require-recorded", action="store_true",
                   help="Keep meetings with no actual_start_time. Off by default: "
                   "a meeting the notetaker never joined has no transcript to audit, "
                   "but still passes a duration filter on its scheduled window.")
    p.add_argument("--team", default=None,
                   help="Filter to meetings with this team ID.")


def main():
    parser = argparse.ArgumentParser(
        description="Aircover agent optimization toolkit.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--stage", default="prod",
        help="Stage: develop|staging|prod (default: prod).",
    )
    parser.add_argument(
        "--base-url", default=None,
        help="Explicit API base URL (overrides --stage).",
    )

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # -- eval --
    p_eval = sub.add_parser("eval", help="Sample meetings, pull transcripts + agent results.")
    p_eval.add_argument("--agent", "--agent-id", dest="agent_id", required=True,
                         help="Agent (template) ID to evaluate.")
    add_sampling_args(p_eval)
    p_eval.add_argument("--include", nargs="*", default=None,
                         help="Additional specific meeting IDs to include.")
    p_eval.add_argument("--meeting-list", default=None,
                         help="File of meeting IDs to use (skips random sampling).")
    p_eval.add_argument("--mode", choices=["cached", "fresh", "preview", "persist"],
                         default="cached",
                         help="How to fetch agent results. "
                         "cached (default): read-only, no tokens, 404 if never run. "
                         "fresh: forces a fresh LLM run (refresh=true) and does NOT "
                         "persist it (preview=true). Use this for post-update re-eval. "
                         "preview: deprecated alias of fresh, identical behavior. "
                         "persist: fresh run AND overwrites the live cached result, "
                         "also writing into qualification/deal rollups. "
                         "COST: token charges are recorded before the no-persist check, "
                         "so fresh and persist cost exactly the same. fresh buys "
                         "non-mutation, not a discount.")

    p_eval.add_argument("--out-dir", default=None,
                         help="Output directory (default: eval_<agent_id>_<timestamp>).")

    # -- get-agent --
    p_get = sub.add_parser("get-agent", help="Download current agent config as JSON.")
    p_get.add_argument("--agent", "--agent-id", dest="agent_id", required=True,
                        help="Agent (template) ID.")
    p_get.add_argument("--out-file", default=None,
                        help="Output filename (default: agent_config_<id>.json).")

    # -- update-agent --
    p_upd = sub.add_parser("update-agent", help="Push revised agent config from a JSON file.")
    p_upd.add_argument("--agent", "--agent-id", dest="agent_id", required=True,
                         help="Agent (template) ID to update.")
    p_upd.add_argument("--from", dest="from_file", required=True,
                         help="Path to the revised agent JSON file.")
    p_upd.add_argument("--dry-run", action="store_true",
                         help="Show the pre-flight diff against the live config and exit "
                         "without sending the PUT.")
    p_upd.add_argument("--force", action="store_true",
                         help="Push even if the update would wipe currently-set "
                         "list-item fields (teams, visibility, etc.).")

    # -- list-meetings --
    p_list = sub.add_parser(
        "list-meetings",
        help="List the meetings the sampler WOULD pick. Free: no agent runs, no tokens.")
    add_sampling_args(p_list)
    p_list.add_argument("--out-file", default=None,
                        help="Write the qualifying meeting IDs to this file "
                        "(ready to pass to eval --meeting-list).")

    # -- summarize (offline) --
    p_sum = sub.add_parser("summarize", help="One scores.json -> distribution + category histogram (offline).")
    p_sum.add_argument("scores", help="Path to a scores.json")

    # -- compare (offline) --
    p_cmp = sub.add_parser("compare", help="Multiple scores.json -> rank, winner, tradeoffs (offline).")
    p_cmp.add_argument("scores", nargs="+", help="Two or more scores.json (best-of-K candidates)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Offline commands: no network, no token. Dispatch before touching auth.
    if args.command == "summarize":
        sys.exit(cmd_summarize(args))
    elif args.command == "compare":
        sys.exit(cmd_compare(args))

    base_url = args.base_url or STAGES.get(args.stage.lower())
    if not base_url:
        raise SystemExit(
            f"Unknown stage '{args.stage}'. Choose from: {', '.join(sorted(set(STAGES)))}"
        )
    base_url = base_url.rstrip("/")

    token = resolve_token(base_url)

    # Default output dir for eval includes agent ID and timestamp
    if args.command == "eval" and not args.out_dir:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        args.out_dir = f"eval_{safe_filename(args.agent_id)}_{ts}"

    if args.command == "eval":
        sys.exit(cmd_eval(args, base_url, token))
    elif args.command == "list-meetings":
        sys.exit(cmd_list_meetings(args, base_url, token))
    elif args.command == "get-agent":
        sys.exit(cmd_get_agent(args, base_url, token))
    elif args.command == "update-agent":
        sys.exit(cmd_update_agent(args, base_url, token))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
