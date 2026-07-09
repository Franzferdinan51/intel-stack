# Alert Ladder

The 4-level escalation ladder used by the `weather-monitor` and `weather-email-trigger` skills.

## Visual

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                  ESCALATION LADDER                          │
                    └─────────────────────────────────────────────────────────────┘

      Level 0              Level 1              Level 2              Level 3
      ───────              ───────              ───────              ───────
      none                 watch                warning              emergency
      (no threat)          (12-36h)             (hours)              (imminent)

                          │                    │                    │
   ┌──────────────────┐   │   ┌─────────────┐  │   ┌──────────────┐ │   ┌──────────────┐
   │ No email         │   │   │ Weather     │  │   │ URGENT       │ │   │ Storm Alert  │
   │ Quiet day        │   │   │ Watch       │  │   │ UPDATE       │ │   │ + WAKE-UP    │
   │                  │   │   │ Subject:    │  │   │ Subject:     │ │   │ CALL option  │
   │ Auto-fire: NO    │   │   │ "Weather    │  │   │ "URGENT      │ │   │ Subject:     │
   │                  │   │   │ Watch -"    │  │   │ UPDATE:"     │ │   │ "Storm       │
   │ Tone: silent     │   │   │             │  │   │              │ │   │ Alert:" /    │
   │                  │   │   │ Auto: YES   │  │   │ Auto: YES    │ │   │ "WAKE-UP:"   │
   └──────────────────┘   │   └─────────────┘  │   └──────────────┘ │   │              │
                          │                    │                    │   │ Auto: 3=YES  │
                          │                    │                    │   │       4=NO   │
                          │                    │                    │   └──────────────┘
                          ▼                    ▼                    ▼

                          ┌──────────────────────────────────────────────────────┐
                          │  When in doubt, stay silent. When certain, escalate. │
                          └──────────────────────────────────────────────────────┘
```

## Level Definitions

| Level | Monitor Name | Trigger Conditions | Email Subject | Auto-fire? |
|---|---|---|---|---|
| 0 | `none` | No alerts. SPC MRGL or below. | — | — |
| 1 | `watch` | SPC ENH/SLGT in day's outlook. Tornado/Severe T-Storm Watch active. | `Weather Watch - <Area> - <Day> <Date> Severe Storm Threat` | ✅ Yes |
| 2 | `warning` | Severe T-Storm Warning active. SPC MDT. Flash Flood Warning. | `URGENT UPDATE: Level N of 5 - <Day> <Date> Severe Storm Threat - <Area>` | ✅ Yes |
| 3 | `emergency` | Tornado Warning active. SPC HIGH. Flash Flood Emergency. | `Storm Alert: <Area> - Tonight <Window> - Tornadoes + 80 mph Wind Possible` | ✅ Yes + Telegram heads-up |
| 4 | `emergency` + night | Level 3 conditions AND local time 22:00-04:00 | `WAKE-UP CALL: Tonight <Window> is the REAL Threat - <Area>` | ❌ Operator `go` |

## Email Tone by Level

| Level | Tone | Sample Phrases |
|---|---|---|
| 1 | Informational | "Damaging winds, large hail, isolated tornadoes possible." |
| 2 | Bold, direct | "FORECAST ESCALATED since 3pm today." |
| 3 | Action-oriented | "STRONG TORNADOES POSSIBLE — TONIGHT 9 PM to MIDNIGHT." |
| 4 | All-caps, urgent | "DON'T LET THE CURRENT LULL FOOL YOU." |

## State Transitions

```
none ──escalation──> watch ──escalation──> warning ──escalation──> emergency
  ↑                      │                     │                       │
  │                      │                     │                       │
  └────── de-escalation ─┴────── de-escalation ┴────── de-escalation ──┘
```

A de-escalation is when current_level < prior_level. **No email is sent on de-escalation** — the operator already knows the threat is past.

## Geographic Scope

Every email MUST pass the geographic scope filter. See `skills/weather-email-trigger/SKILL.md` for the strict rules. TL;DR: alerts only fire for the configured home location; out-of-area mentions are ignored.

## Cooldown Rules

| Rule | Default |
|---|---|
| Same level (e.g. level 2 → level 2) | 30 min minimum |
| Escalation (e.g. level 2 → level 3) | 5 min minimum |
| De-escalation | No email |
| Operator force-fire | Skip cooldowns |

## When to Override

- ✅ Force-fire level 1 or 2 manually: `python orchestrate_alert.py --send --level 2`
- ❌ Force-fire level 4 from cron: NEVER. Level 4 requires human judgment.
- ✅ Override cooldowns: just add `--send` to bypass dry-run and use the override flag.
- ❌ Skip geographic scope filter: NEVER. Wrong-region emails are the #1 trust-killer.