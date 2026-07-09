---
name: defcon-email-trigger
description: Decide if a DEFCON email should fire — only on level 1 or 2 escalation.
metadata:
  hermes:
    tags: [DEFCON, Email, Trigger, Escalation, Intelligence]
version: 0.1.0
author: Hermes
---

# DEFCON Email Trigger

Gatekeeper between `defcon-monitor-email` (which detects escalation to DEFCON 1 or 2) and `defcon-email-send` (which sends the actual email). Decides IF and WHEN a DEFCON email should fire.

**Hard rule: emails only fire on transitions to DEFCON 1 or 2.** Levels 3-5 are silent. Sustained levels don't re-fire.

## When to Use

- After a `defcon-monitor-email` run returns `changed: true`.
- Cron / heartbeat asks "should we send a DEFCON email right now?"
- Operator says "send a DEFCON alert" and the skill picks the right level.

## Scope — STRICT Trigger Filter

- ✅ **Fire** on: transition to DEFCON 2 (high) or DEFCON 1 (emergency).
- ❌ **NEVER fire** on: DEFCON 3, 4, or 5 — silent.
- ❌ **NEVER fire** on de-escalation (e.g. 1 → 2). No email on de-escalation.
- ❌ **NEVER re-fire** while sustained at the same level. Only transitions trigger.
- ❌ **NEVER auto-fire** without operator override during DEFCON 1 — that level is so rare and consequential that human confirmation is mandatory before blast.

## Prerequisites

- `defcon-monitor-email` state file: `~/.openclaw/workspace/state/defcon-email.json`
- `defcon-email-send` skill loaded for the actual send.
- Operator confirmation channel.

## How to Run

Invoke through `terminal` + `read_file`. Returns a decision object; caller does the actual send.

## Quick Reference

- Email levels (matches DEFCON): `level_2_high` (DEFCON 2), `level_1_emergency` (DEFCON 1)
- Mapping from monitor alert_level → email level:
  - `none` (DEFCON 3/4/5) → no email
  - `high` (DEFCON 2) → `level_2_high`
  - `emergency` (DEFCON 1) → `level_1_emergency`
- Cooldown: 6 hours minimum between any DEFCON emails (this is rare — don't spam).

## Procedure

1. **Read monitor state** through `read_file`:
   ```
   path: ~/.openclaw/workspace/state/defcon-email.json
   ```

2. **Check trigger filter:**
   - If `current_alert_level == "none"` → return `{fire: false, reason: "below_trigger"}`
   - If event_type is `de_escalation` → return `{fire: false, reason: "de_escalation_no_alert"}`
   - If `changed == false` → return `{fire: false, reason: "no_change"}`

3. **Check cooldown** in state file's `last_email`:
   ```json
   "last_email": {"level": "level_2_high", "at_utc": "..."}
   ```
   If `now - last_email.at_utc < 6 hours`, return `{fire: false, reason: "cooldown"}`.

4. **Map alert level to email level:**
   - `high` → `level_2_high`
   - `emergency` → `level_1_emergency`

5. **Apply confirmation policy:**
   - `level_2_high` (DEFCON 2): AUTO-fire is OK. Operator pre-authorized these.
   - `level_1_emergency` (DEFCON 1): NEVER auto-fire. Return `{fire: true, requires_confirmation: true}` and wait for explicit `go`.

6. **Build the decision object:**
   ```json
   {
     "fire": true,
     "level": "level_2_high",
     "defcon_level": 2,
     "requires_confirmation": false,
     "subject_hint": "DEFCON 2 ALERT: High Threat Level — Action Required",
     "body_data": {
       "headline": "<defcon reason>",
       "threat_score": 78,
       "active_threats": [...],
       "per_domain_scores": {...},
       "action_list": [...]
     },
     "reason": "escalation to DEFCON 2, transition detected, cooldown OK"
   }
   ```

7. **Update monitor state** with `last_email`:
   ```json
   "last_email": {"level": "level_2_high", "at_utc": "<now>"}
   ```
   Write back with `write_file`.

8. **Return the decision.** Caller (human or orchestrator) hands it to `defcon-email-send`.

## Pitfalls

- **Sustained levels don't re-fire.** DEFCON 2 today and DEFCON 2 tomorrow = only one email (the transition).
- **De-escalation is silent.** When level moves from 1 to 2, that's good news but we don't email about good news.
- **DEFCON 1 requires operator `go`.** Even with auto-fire enabled, the human must confirm. False DEFCON 1 emails destroy trust permanently.
- **Cooldown is 6 hours, not 30 minutes.** DEFCON events are rare. Don't spam.
- **Geographic scope is irrelevant.** DEFCON is global — no county/ZIP filter.

## Verification

```bash
python -c "
import json, os
p = os.path.expanduser('~/.openclaw/workspace/state/defcon-email.json')
if not os.path.exists(p):
    print('NO STATE — run defcon-monitor-email first')
else:
    d = json.loads(open(p).read())
    print('alert:', d.get('current_alert_level'), '| defcon:', d.get('current_defcon_level'), '| last_email:', d.get('last_email'))
"
```

Expected: prints alert level + DEFCON level + last_email. If `alert: none`, no email will fire — correct answer for quiet days.

## Related Repositories

| Tool | Repo |
|---|---|
| **Intelligence Stack** (umbrella repo) | [Franzferdinan51/intel-stack](https://github.com/Franzferdinan51/intel-stack) |
| **Hermes Agent** | [nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent) |
| **AgentMail SDK** | [docs.agentmail.to](https://docs.agentmail.to) |