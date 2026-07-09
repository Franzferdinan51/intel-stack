---
name: defcon-email-send
description: Send DEFCON 1 or 2 alert email with full HTML+CSS and action list.
metadata:
  hermes:
    tags: [DEFCON, Email, Send, HTML, Templates, Alert]
version: 0.1.0
author: Hermes
---

# DEFCON Email Send

Renders a DEFCON alert email at level 1 (emergency) or level 2 (high) and fans it out via AgentMail.in. Pulls HTML + plain-text templates from `references/` and substitutes live data.

**Only 2 levels exist**: `level_2_high` (DEFCON 2) and `level_1_emergency` (DEFCON 1). DEFCON 3-5 are silent — never email.

## When to Use

- `defcon-email-trigger` returned `{fire: true, ...}` and the operator (or orchestrator) has approved.
- Operator says "send a DEFCON 2 alert" with the data ready.
- Always paired with `defcon-email-trigger` in production.

## Scope — Recipients

- Recipients are read from the `DEFCON_ALERT_RECIPIENTS` env var (separate from `ALERT_RECIPIENTS` so DEFCON alerts don't piggyback on weather alerts).
- This skill does NOT hard-code any addresses. It does NOT modify the recipient list.
- **Test mode**: set `DEFCON_DRY_RUN=1` to render the email and print it without sending. Always do this first.

## Prerequisites

- `AGENTMAIL_API_KEY` env var (see `.env.example`).
- `AGENTMAIL_INBOX` env var.
- `DEFCON_ALERT_RECIPIENTS` env var — comma-separated recipient list.
- Python package: `pip install agentmail`.
- HTML + plain-text templates in `references/` (2 files per level: `level_2_high.{html,txt,json}` and `level_1_emergency.{html,txt,json}`).

## How to Run

Invoke through `terminal`. Always dry-run first for level_1_emergency.

## Quick Reference

- Sender format: `<Display Name> <AGENTMAIL_INBOX>`
- AgentMail API base: `https://api.agentmail.to/v0`
- SDK: `from agentmail import AgentMail`
- 2 levels: `level_2_high` (DEFCON 2), `level_1_emergency` (DEFCON 1)
- Template files per level: `<level>.html`, `<level>.txt`, `<level>.json`
- Subject lines match the level's escalation tone (see templates).

## Procedure

1. **Load the template for the chosen level.** Read from this skill's `references/`:
   ```
   skills/defcon-email-send/references/<level>.html
   skills/defcon-email-send/references/<level>.txt
   skills/defcon-email-send/references/<level>.json
   ```
   The `.json` contains the canonical subject pattern + recipients (for reference, not enforcement).

2. **Substitute live values** into the HTML and plain-text bodies. Required substitutions:
   - `{{DATETIME}}` → ISO timestamp of the alert (UTC)
   - `{{DEFCON_LEVEL}}` → "2" or "1"
   - `{{THREAT_SCORE}}` → 0-100 composite score
   - `{{HEADLINE}}` → main reason / headline (escaped)
   - `{{ACTIVE_THREATS}}` → HTML list of {id, category, description, level, severity}
   - `{{ACTIVE_THREATS_TEXT}}` → plain-text version of the same
   - `{{ACTIVE_THREATS_COUNT}}` → integer
   - `{{SCORE_GEOPOL}}`, `{{SCORE_CYBER}}`, `{{SCORE_ECON}}`, `{{SCORE_NUCLEAR}}` → per-domain scores
   - `{{ACTION_LIST}}` → recommended actions (e.g. "shelter in place", "monitor news")
   - `{{LIVE_SOURCES}}` → list of verification URLs

3. **Dry-run by default.** If `DEFCON_DRY_RUN=1` or `--dry-run` flag, print the rendered subject + body, then STOP.

4. **Send via AgentMail SDK.** For each recipient in `DEFCON_ALERT_RECIPIENTS`:
   ```python
   from agentmail import AgentMail
   import os
   client = AgentMail(api_key=os.getenv('AGENTMAIL_API_KEY'))
   for to in os.getenv('DEFCON_ALERT_RECIPIENTS').split(','):
       client.inboxes.messages.send(
           inbox_id=os.getenv('AGENTMAIL_INBOX'),
           to=to.strip(),
           subject=subject,
           text=text_body,   # plain-text fallback
           html=html_body,   # inline CSS version
       )
   ```

5. **Return** the list of `message_id`s returned by the SDK (for audit trail). Write them to the monitor state file's `last_email.message_ids` field.

## Safety Rules (Non-Negotiable)

1. NEVER auto-fire `level_1_emergency` (DEFCON 1). It ALWAYS requires operator `go`.
2. NEVER auto-fire on levels 3, 4, or 5. Email trigger skill blocks these, but double-check.
3. NEVER add recipients to `DEFCON_ALERT_RECIPIENTS`. Operator must edit `.env` themselves.
4. NEVER send on de-escalation. Only escalations fire.
5. ALWAYS send BOTH `text` AND `html` versions. The SDK takes both fields.
6. ALWAYS dry-run on `level_1_emergency` before actually sending.
7. ALWAYS include the action list. The email's job is to tell the recipient what to do.

## Pitfalls

- **DEFCON direction is INVERSE to alert level.** Subject lines say "DEFCON 2 ALERT" (high) or "DEFCON 1 EMERGENCY" (max threat). Don't accidentally say "DEFCON 5 ALERT" (which would be peacetime).
- **Inventing senders is the #1 mistake.** AgentMail gives you ONE inbox per account. The account IS the sender.
- **Templates are versioned.** Don't reinvent the HTML — copy structure from `references/<level>.html` and substitute values.
- **Plain text fallback is required.** Some clients (and screen readers) need it. Always include both.
- **Recipient list is config, not code.** It lives in `.env`, not in this skill.
- **Don't include the full PDF brief in the email body.** If operator wants the PDF, attach it as a file separately. The HTML body should be scannable in <30 seconds.

## Verification

```bash
# Dry-run:
DEFCON_DRY_RUN=1 python scripts/send_defcon_alert.py \
  --level level_2_high \
  --subject "DEFCON 2 ALERT: Test" \
  --body-file references/level_2_high.txt

# Real send (operator override required for level_1_emergency):
python scripts/send_defcon_alert.py \
  --level level_2_high \
  --subject "DEFCON 2 ALERT: Test" \
  --body-file references/level_2_high.txt
```

Expected dry-run output: rendered subject + first 500 chars of body. Expected real-send output: list of message IDs from AgentMail.

## External Repositories (Referenced Programs)

This skill chains into the broader Intelligence Stack. Clone or fork these to get the full pipeline:

| Tool | What it is | Repo |
|---|---|---|
| **Intelligence Stack** (umbrella repo) | The 4-skill email pipeline + orchestrator | [Franzferdinan51/intel-stack](https://github.com/Franzferdinan51/intel-stack) |
| **Hermes Agent** | The agent runtime this skill runs on | [nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent) |
| **AgentMail Python SDK** | Email send/receive (`pip install agentmail`) | [docs.agentmail.to](https://docs.agentmail.to) |
| **ClawdWatch** (optional) | Live DEFCON composite score source | Local server on port 3444 (our Lobster Edition fork) |

## Template Customization

The HTML templates in `references/` use a small set of placeholder tokens:
- `{{DATETIME}}` — UTC ISO timestamp
- `{{DEFCON_LEVEL}}` — "2" or "1"
- `{{THREAT_SCORE}}` — 0-100
- `{{HEADLINE}}` — short headline string (HTML-escaped)
- `{{ACTIVE_THREATS}}` — HTML `<li>` list
- `{{ACTIVE_THREATS_TEXT}}` — plain-text list
- `{{ACTIVE_THREATS_COUNT}}` — integer
- `{{SCORE_*}}` — per-domain integer scores
- `{{ACTION_LIST}}` — `<li>` or `-` list
- `{{LIVE_SOURCES}}` — `<a>` tags or `- [name](url)` markdown

The two included templates (`level_2_high.html` and `level_1_emergency.html`) are styled to be visually distinct — the level-1 template uses pure black + red while level-2 uses a red gradient on white. Customize by editing the inline `<style>` blocks.