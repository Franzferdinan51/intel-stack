---
name: weather-email-send
description: Send a weather alert email using a 4-level escalation ladder and HTML templates.
metadata:
  hermes:
    tags: [Weather, Email, Send, AgentMail, HTML, Templates]
version: 0.1.0
author: Hermes
---

# Weather Email Send

Renders a weather alert email at the chosen level (1-4) and fans it out to a configured recipient list via AgentMail.in. Pulls HTML + plain-text templates from `references/` and substitutes live data.

Does NOT decide whether to send — that's `weather-email-trigger`. Does NOT track state — that's `weather-monitor`. This skill is the **last hop** in the pipeline: it only sends.

## When to Use

- `weather-email-trigger` returned `{fire: true, ...}` and the operator (or orchestrator) has approved.
- Operator says "send a level N alert" with the data ready.
- Always paired with `weather-email-trigger` in production.

## Scope — Recipients

- Recipients are read from the `ALERT_RECIPIENTS` env var (comma-separated).
- This skill does NOT hard-code any addresses. It does NOT modify the recipient list.
- **Test mode**: set `WEATHER_DRY_RUN=1` to render the email and print it without sending. Always do this first.

## Prerequisites

- `AGENTMAIL_API_KEY` env var (see `.env.example`).
- `AGENTMAIL_INBOX` env var — ONE inbox per AgentMail account.
- `ALERT_RECIPIENTS` env var — comma-separated recipient list.
- Python package: `pip install agentmail`.
- HTML + plain-text templates in `references/` (4 files per level).

## How to Run

Invoke through `terminal`. Always dry-run first if level ≥ 3.

## Quick Reference

- Sender format: `<Display Name> <AGENTMAIL_INBOX>`
- AgentMail API base: `https://api.agentmail.to/v0`
- SDK: `from agentmail import AgentMail`
- 4 levels: `1_weather_watch` / `2_urgent_update` / `3_storm_alert` / `4_wake_up_call`
- Template files per level: `<level>.html`, `<level>.txt`, `<level>.json`
- Subject lines match the level's escalation tone (see templates).

## Procedure

1. **Load the template for the chosen level.** Read from this skill's `references/`:
   ```
   skills/weather-email-send/references/<level>.html
   skills/weather-email-send/references/<level>.txt
   skills/weather-email-send/references/<level>.json
   ```
   The `.json` contains the canonical subject pattern + recipients (for reference, not enforcement).

2. **Substitute live values** into the HTML and plain-text bodies. Required substitutions:
   - `{{DATETIME}}` → ISO timestamp of the alert
   - `{{AREA}}` → home county + state
   - `{{HEADLINE}}` → NWS headline (escaped)
   - `{{CURRENT_CONDITIONS}}` → {temp, wind, humidity, pressure}
   - `{{ACTIVE_ALERTS}}` → list of {event, severity, expires}
   - `{{SPC_CATEGORICAL}}` → today's SPC category
   - `{{ACTION_LIST}}` → recommended safety actions
   - `{{LIVE_SOURCES}}` → list of verification URLs

3. **Dry-run by default.** If `WEATHER_DRY_RUN=1` or `--dry-run` flag, print the rendered subject + body, then STOP.

4. **Send via AgentMail SDK.** For each recipient in `ALERT_RECIPIENTS`:
   ```python
   from agentmail import AgentMail
   import os
   client = AgentMail(api_key=os.getenv('AGENTMAIL_API_KEY'))
   for to in os.getenv('ALERT_RECIPIENTS').split(','):
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

1. NEVER auto-fire level 4 (WAKE-UP CALL). It requires operator `go`.
2. NEVER add recipients to `ALERT_RECIPIENTS`. Operator must edit `.env` themselves.
3. NEVER change the escalation ladder without asking the operator.
4. ALWAYS send BOTH `text` AND `html` versions. The SDK takes both fields.
5. ALWAYS dry-run on level 3+ before actually sending.

## Pitfalls

- **Inventing senders is the #1 mistake.** AgentMail gives you ONE inbox per account. The account IS the sender. Don't construct `From: anything@elsewhere.com`.
- **Templates are versioned.** Don't reinvent the HTML — copy structure from `references/<level>.html` and substitute values.
- **Plain text fallback is required.** Some clients (and screen readers) need it. Always include both.
- **Don't shorten the body.** Match the section order and length of the originals.
- **Subject prefix is part of the brand.** Operators scan their inbox by these prefixes. Don't change them.
- **Recipient list is config, not code.** It lives in `.env`, not in this skill.

## Verification

```bash
# Dry-run (no send):
WEATHER_DRY_RUN=1 python scripts/send_alert.py \
  --level 2 \
  --subject "URGENT UPDATE: Test" \
  --body-file references/2_urgent_update.txt

# Real send (level 1 or 2 only by default):
python scripts/send_alert.py \
  --level 2 \
  --subject "URGENT UPDATE: Test" \
  --body-file references/2_urgent_update.txt
```

Expected dry-run output: rendered subject + first 500 chars of body. Expected real-send output: list of message IDs from AgentMail.