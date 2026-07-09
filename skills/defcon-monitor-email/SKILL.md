---
name: defcon-monitor-email
description: Track DEFCON level changes and detect escalation to 1 or 2 for email.
metadata:
  hermes:
    tags: [DEFCON, Monitor, Escalation, Email, Intelligence]
version: 0.1.0
author: Hermes
---

# DEFCON Monitor (Email Pipeline)

Tracks DEFCON level changes over time and detects escalation to **1 or 2** (the trigger thresholds for emergency email alerting). Companion to any DEFCON monitor you run — this one is scoped specifically to the email alerting pipeline and uses a separate, lightweight state file.

Does NOT pull data itself (delegates to `defcon-pull`). Does NOT send emails (delegates to `defcon-email-trigger`). Just maintains the alert-relevant state.

## When to Use

- Scheduled cron / heartbeat wants to know "did DEFCON escalate to 1 or 2 since last check?".
- Another skill needs a stable ID like `current_alert_level: emergency|high|none` without re-implementing the logic.
- Pre-flight check before `defcon-email-send` fires.

## Scope

- **Single composite DEFCON level** (1-5, where 1 = nuclear war imminent, 5 = peacetime).
- **Trigger thresholds**: only levels 1 and 2 trigger email alerts. Levels 3-5 are silent (existing Telegram/Slack notifiers in your main monitor cover those).
- **No geographic scope** — DEFCON is global by definition.

## Prerequisites

- `defcon-pull` must be runnable (returns the structured data this skill consumes).
- State file at `~/.openclaw/workspace/state/defcon-email.json` (separate from your main DEFCON state so the email-trigger logic doesn't pollute the heavy monitor schema).

## How to Run

Invoke through `terminal` + `read_file`/`write_file`. State updates happen every run. Caller decides polling cadence.

## Quick Reference

- State path: `~/.openclaw/workspace/state/defcon-email.json`
- Trigger levels: 1 (max), 2 (high)
- Silent levels: 3, 4, 5
- DEFCON scale (low number = higher threat): 1 < 2 < 3 < 4 < 5

## Procedure

1. **Call `defcon-pull`** through the terminal tool. Get the structured summary.

2. **Read prior state** through `read_file`:
   ```
   path: ~/.openclaw/workspace/state/defcon-email.json
   ```

3. **Compute current alert level:**
   - `emergency` — DEFCON 1
   - `high` — DEFCON 2
   - `none` — DEFCON 3, 4, or 5

4. **Compare to prior alert level.** If `current < prior` (lower number = higher threat), that's an **ESCALATION** (e.g. high → emergency). If `current > prior`, that's DE-ESCALATION (e.g. emergency → high). If equal, no change.

5. **Build event records** for any changes:
   - `{event_type: escalation|de_escalation, from: <prior>, to: <current>, at: <utc_iso>, headline: <reason>, threats: [<top threats>]}`

6. **Append events** to the state file's `events[]` array (cap at 50 most recent).

7. **Write state file** through `write_file`:
   ```json
   {
     "last_checked_utc": "2026-07-09T15:50:00Z",
     "current_alert_level": "high",
     "current_defcon_level": 2,
     "threat_score": 78,
     "escalation_signal": "high",
     "active_threats_count": 4,
     "events": [...],
     "last_pulled_data": { /* full defcon-pull summary */ },
     "last_email": null
   }
   ```

8. **Return** to caller:
   - `alert_level`: current level ("emergency" / "high" / "none")
   - `defcon_level`: the integer (1-5)
   - `changed`: bool
   - `change`: the event record if changed, else null
   - `prior_alert_level`: what it was before this run
   - `recommended_action`: text hint for the email-trigger skill

## Pitfalls

- **DEFCON direction is INVERSE to alert level.** A lower DEFCON number = more threat. Don't accidentally sort ascending.
- **Only escalate emails on transitions to 1 or 2.** A sustained DEFCON 2 (already at high) doesn't re-fire every cron tick — only transitions do.
- **State file is separate from the main monitor state.** This keeps the email-trigger state isolated.
- **ClawdWatch can be down.** Fall back to state file alone. If state file is also stale (>6h), treat as `none` and don't fire.
- **DEFCON 1 is so rare that any false positive is bad.** Require cross-validation between two sources before treating a level-1 signal as real. ClawdWatch AND state file must agree.

## Verification

```bash
python -c "
import json, os
p = os.path.expanduser('~/.openclaw/workspace/state/defcon-email.json')
if os.path.exists(p):
    d = json.loads(open(p).read())
    print('OK alert_level:', d.get('current_alert_level'), 'defcon:', d.get('current_defcon_level'), 'events:', len(d.get('events', [])))
else:
    print('NO STATE FILE — run the skill first')
"
```

Expected: `OK alert_level: <emergency|high|none> defcon: <1-5> events: <N>`. If `NO STATE FILE`, run the procedure once. If `events` is 0, no escalation detected — that's fine for quiet days.

## Related Repositories

| Tool | Repo |
|---|---|
| **Intelligence Stack** (umbrella repo) | [Franzferdinan51/intel-stack](https://github.com/Franzferdinan51/intel-stack) |
| **Hermes Agent** | [nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent) |
| **AgentMail SDK** | [docs.agentmail.to](https://docs.agentmail.to) |