#!/usr/bin/env python3
"""
orchestrate_alert.py — Run the full weather intelligence pipeline.

Pulls fresh data, detects escalation, decides if email should fire, and (if approved) sends.
Designed to be invoked from a manual operator command OR from the cron watchdog.

Usage:
    # Manual: dry-run a level 2 alert
    python orchestrate_alert.py --dry-run --level 2

    # Manual: actually send (operator override)
    python orchestrate_alert.py --send --level 2 --subject "URGENT UPDATE: ..."

    # Cron: just run the pipeline (will auto-fire levels 1-3 if warranted)
    python orchestrate_alert.py

Environment:
    HOME_LAT, HOME_LON, HOME_ZIP, HOME_COUNTY, HOME_WFO  - required for scope
    AGENTMAIL_API_KEY, AGENTMAIL_INBOX                    - required for send
    ALERT_RECIPIENTS                                       - required for send
    WEATHER_DRY_RUN=1                                      - default to dry-run

Exit codes:
    0  - no action needed (level=none)
    1  - error
    2  - escalation detected, email not sent (cooldown, out of scope, or requires_confirmation)
    3  - email sent successfully
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path("~/.openclaw/workspace/state/weather-{zip}.json").expanduser()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(zip_code: str) -> dict | None:
    p = Path(str(STATE_PATH).format(zip=zip_code))
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(zip_code: str, state: dict) -> None:
    p = Path(str(STATE_PATH).format(zip=zip_code))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


def compute_level(pulled: dict) -> str:
    """Map the pulled data into one of: none / watch / warning / emergency."""
    alerts = pulled.get("active_alerts", [])
    spc = pulled.get("spc_day1", {}).get("categorical", "TSTM")

    for a in alerts:
        ev = (a.get("event") or "").lower()
        sev = (a.get("severity") or "").lower()
        if "tornado warning" in ev or "flash flood emergency" in ev or sev == "extreme":
            return "emergency"
        if "severe thunderstorm warning" in ev or "tornado warning" in ev:
            return "warning"

    if spc in ("MDT", "HIGH"):
        return "warning"
    if spc in ("ENH", "SLGT"):
        return "watch"
    if any("watch" in (a.get("event") or "").lower() for a in alerts):
        return "watch"

    return "none"


LEVEL_ORDER = {"none": 0, "watch": 1, "warning": 2, "emergency": 3}


def decide_send(state: dict, level: str, dry_run: bool, force_level: int | None) -> dict:
    """Decide IF and WHEN an email should fire."""
    if level == "none" and force_level is None:
        return {"fire": False, "reason": "no_threat"}

    prior = state.get("current_level", "none") if state else "none"
    last_email = (state or {}).get("last_email", {}) or {}

    # Determine target email level
    if force_level is not None:
        target_level = force_level
    elif level == "watch":
        target_level = 1
    elif level == "warning":
        target_level = 2
    elif level == "emergency":
        target_level = 3
    else:
        return {"fire": False, "reason": "no_threat"}

    # Cooldown check
    if last_email and not dry_run:
        try:
            last_at = datetime.fromisoformat(last_email["at_utc"].replace("Z", "+00:00"))
            minutes_since = (datetime.now(timezone.utc) - last_at).total_seconds() / 60
            if last_email.get("level") == target_level and minutes_since < 30:
                return {"fire": False, "reason": "cooldown_same_level"}
            if minutes_since < 5:
                return {"fire": False, "reason": "cooldown_escalation"}
        except Exception:
            pass

    return {
        "fire": True,
        "level": target_level,
        "level_name": ["weather_watch", "urgent_update", "storm_alert", "wake_up_call"][target_level - 1],
        "requires_confirmation": target_level == 4,
        "reason": f"escalation {prior} -> {level}" if LEVEL_ORDER.get(level, 0) > LEVEL_ORDER.get(prior, 0) else "manual",
    }


def send_email(decision: dict, state: dict) -> list[str]:
    """Actually send via AgentMail. Returns list of message_ids."""
    try:
        from agentmail import AgentMail
    except ImportError:
        print("ERROR: pip install agentmail", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("AGENTMAIL_API_KEY", "")
    inbox = os.environ.get("AGENTMAIL_INBOX", "")
    recipients = [r.strip() for r in os.environ.get("ALERT_RECIPIENTS", "").split(",") if r.strip()]

    if not all([api_key, inbox, recipients]):
        print("ERROR: AGENTMAIL_API_KEY / AGENTMAIL_INBOX / ALERT_RECIPIENTS must be set", file=sys.stderr)
        sys.exit(1)

    client = AgentMail(api_key=api_key)
    message_ids = []
    level = decision["level"]

    subject_prefix = ["Weather Watch", "URGENT UPDATE", "Storm Alert", "WAKE-UP CALL"][level - 1]
    subject = f"{subject_prefix}: {state.get('current_level', 'alert')} for {os.environ.get('HOME_COUNTY', 'home area')}"

    # In a real implementation, load templates from skills/weather-email-send/references/
    # and substitute {{AREA}}, {{HEADLINE}}, etc. Stubbed here for portability.
    body_text = f"Alert level {level}. Check NWS for details: https://forecast.weather.gov/"
    body_html = f"<p>Alert level {level}. Check NWS for details: <a href='https://forecast.weather.gov/'>forecast.weather.gov</a></p>"

    for to in recipients:
        resp = client.inboxes.messages.send(
            inbox_id=inbox,
            to=to,
            subject=subject,
            text=body_text,
            html=body_html,
        )
        message_ids.append(getattr(resp, "message_id", "?"))

    return message_ids


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", default=os.getenv("WEATHER_DRY_RUN") == "1")
    parser.add_argument("--send", action="store_true", help="Override dry-run and actually send")
    parser.add_argument("--level", type=int, choices=[1, 2, 3, 4], help="Force a specific email level")
    parser.add_argument("--subject", help="Override the subject line (manual send)")
    parser.add_argument("--zip", default=os.getenv("HOME_ZIP", "00000"), help="Home ZIP for state file")
    args = parser.parse_args()

    zip_code = args.zip
    state = load_state(zip_code)

    # In a real implementation, call weather-pull here. Stubbed for portability.
    print(f"[{now_utc_iso()}] Orchestrator starting for ZIP {zip_code}")
    print(f"[{now_utc_iso()}] Prior state: {state.get('current_level') if state else 'NONE'}")

    # Decide
    forced = args.level if args.level else None
    decision = decide_send(state or {}, state.get("current_level", "none") if state else "none", args.dry_run, forced)

    print(f"[{now_utc_iso()}] Decision: {json.dumps(decision, indent=2)}")

    if not decision["fire"]:
        print(f"[{now_utc_iso()}] No action: {decision['reason']}")
        sys.exit(0 if decision["reason"] == "no_threat" else 2)

    if decision["requires_confirmation"] and not args.send:
        print(f"[{now_utc_iso()}] Level {decision['level']} requires operator confirmation. Run with --send to override.")
        sys.exit(2)

    if args.dry_run and not args.send:
        print(f"[{now_utc_iso()}] DRY RUN — would send level {decision['level']} ({decision['level_name']})")
        sys.exit(0)

    # Actually send
    msg_ids = send_email(decision, state or {})
    print(f"[{now_utc_iso()}] Sent {len(msg_ids)} messages: {msg_ids}")

    # Update state
    if state is None:
        state = {}
    state["last_email"] = {"level": decision["level"], "at_utc": now_utc_iso(), "message_ids": msg_ids}
    save_state(zip_code, state)
    print(f"[{now_utc_iso()}] State updated.")
    sys.exit(3)


if __name__ == "__main__":
    main()