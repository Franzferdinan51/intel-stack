---
name: defcon-pull
description: Pull DEFCON level and active threats from state + OSINT sources.
metadata:
  hermes:
    tags: [DEFCON, OSINT, Pull, Intelligence, Threat-Level]
version: 0.1.0
author: Hermes
---

# DEFCON Pull

Pulls the current DEFCON threat level and active threats from existing DEFCON state files and complementary live OSINT sources. Does NOT decide whether to alert. Does NOT send any email. Just gathers and returns structured JSON.

## When to Use

- Scheduled cron wants fresh DEFCON data.
- Another skill (`defcon-monitor-email`) needs raw state.
- Pre-flight before sending a DEFCON email — confirm level is actually 1 or 2.
- Operator asks "what's the DEFCON level right now?"

## Scope — Source Layer

This skill reads from existing infrastructure:

- **DEFCON state file** at `~/.openclaw/memory/defcon-state.json` — canonical state written by your DEFCON monitor after every scan. Path is configurable.
- **ClawdWatch server** (optional, if running) — `http://localhost:3444/defcon/score` returns the latest composite level + score.
- **`defconlevel.com`** (fallback) — `https://www.defconlevel.com/alerts/european-command` for EUCOM-style signals.

## Prerequisites

- Python 3.10+ with `urllib`, `json` (stdlib).
- A DEFCON state file must exist (created by your DEFCON monitor runs).
- No API keys.

## How to Run

Invoke through `terminal`. Runs in <1 second.

## Quick Reference

- State path: `~/.openclaw/memory/defcon-state.json` (configurable via env var `DEFCON_STATE_PATH`)
- ClawdWatch (live): `http://localhost:3444/defcon/score`
- Web fallback: `https://www.defconlevel.com/alerts/european-command`
- DEFCON scale: 1 (nuclear war imminent) ↔ 5 (peacetime)

## Procedure

1. **Read primary state file** through `read_file`:
   ```
   path: <DEFCON_STATE_PATH>   # default ~/.openclaw/memory/defcon-state.json
   ```
   Extract: `current_level`, `threat_score`, `last_reason`, `last_updated`, `scores` (per-domain breakdown), `active_threats[]`.

2. **Try ClawdWatch** (live cross-check) through `terminal`:
   ```bash
   curl -s --max-time 5 http://localhost:3444/defcon/score
   ```
   If returns valid JSON with `level` and `score`, use it. If timeout/refused, fall through to step 3.

3. **Web fallback** through `web_extract`:
   ```
   url: https://www.defconlevel.com/alerts/european-command
   char_limit: 3000
   ```
   Parse for the current EUCOM DEFCON level + headline.

4. **Cross-validate.** If the state file says level 2 but ClawdWatch says level 4, take the **higher** of the two (fail-safe). If they agree, use that value.

5. **Compile and return**:
   ```json
   {
     "level": 2,
     "level_label": "HIGH (or similar)",
     "threat_score": 78,
     "last_updated_utc": "2026-07-09T15:50:00Z",
     "source": "state_file" | "clawdwatch" | "web",
     "active_threats": [
       {"id": "...", "category": "...", "description": "...", "level": 2, "severity": "..."}
     ],
     "per_domain_scores": {
       "geopolitical": {"value": 18, "max": 20, "detail": "..."},
       "cyber": {"value": 12, "max": 15, "detail": "..."}
     },
     "escalation_signal": "high" | "severe" | "critical" | "none",
     "sources_ok": ["state_file", "clawdwatch"]
   }
   ```

## Pitfalls

- **State file may be stale.** `last_updated_utc` should be within the last 6 hours. If older, treat as "stale — run your DEFCON monitor first" and return level 5 (safest).
- **ClawdWatch may be down.** Use the web fallback. Don't fail the whole pull.
- **DEFCON levels are integers 1-5 only.** State file might have float-like values in `threat_score` (0-100). The level is the integer; the score is the continuous signal.
- **Active threats can be empty array.** That's fine — DEFCON can still be elevated by domain scores alone.
- **`current_level` in state file is the SUSTAINED level.** For real-time spikes, prefer ClawdWatch.

## Verification

```bash
python -c "
import json, os
p = os.path.expanduser(os.getenv('DEFCON_STATE_PATH', '~/.openclaw/memory/defcon-state.json'))
if not os.path.exists(p):
    print('NO STATE FILE — run your DEFCON monitor first')
else:
    d = json.loads(open(p).read())
    print('OK level:', d.get('current_level'), 'score:', d.get('threat_score'), 'updated:', d.get('last_updated'))
"
```

Expected: `OK level: <1-5> score: <0-100> updated: <iso8601>`. If `NO STATE FILE`, run your monitor first. If `updated` is >6h old, the state is stale — refresh.

## Related Repositories

| Tool | Repo |
|---|---|
| **Intelligence Stack** (umbrella repo) | [Franzferdinan51/intel-stack](https://github.com/Franzferdinan51/intel-stack) |
| **Hermes Agent** | [nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent) |
| **ClawdWatch** (optional live source) | Local server on port 3444 |
| **AgentMail SDK** | [docs.agentmail.to](https://docs.agentmail.to) |