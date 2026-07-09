# Alert Ladders

The escalation ladders used by the Intelligence Stack. Two domains, two ladders:

1. **Weather** — 4-level ladder (Watch / URGENT UPDATE / Storm Alert / WAKE-UP CALL)
2. **DEFCON** — 2-level ladder (level 2 high / level 1 emergency) — levels 3-5 are silent

Both ladders share the same `pull → monitor → trigger → send` architecture. Only the trigger logic differs.

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

---

# DEFCON Ladder (2 levels)

The DEFCON domain uses a much tighter ladder than weather — only 2 email levels. Levels 3-5 are silent because existing Telegram/Slack notifiers (in your main DEFCON monitor) already cover them.

## Visual

```
            ┌─────────────────────────────────────────────────────────────┐
            │                  DEFCON LADDER (EMAIL ONLY)                 │
            └─────────────────────────────────────────────────────────────┘

   DEFCON 5        DEFCON 4        DEFCON 3        DEFCON 2        DEFCON 1
   ────────        ────────        ────────        ────────        ────────
   PEACETIME       ELEVATED        HIGH            DEFCON 2        DEFCON 1
   (no threat)     (routine)       (active)        (HIGH)          (EMERGENCY)

        │               │               │               │                │
        │               │               │               │                │
   ┌─────────┐     ┌─────────┐    ┌─────────┐    ┌─────────────┐   ┌─────────────┐
   │ No email│     │ No email│    │ No email│    │ DEFCON 2    │   │ DEFCON 1    │
   │ Silent  │     │ Silent  │    │ Silent  │    │ ALERT       │   │ EMERGENCY   │
   │         │     │         │    │         │    │             │   │             │
   │ Auto:NO │     │ Auto:NO │    │ Auto:NO │    │ Auto:YES    │   │ Auto:NO     │
   │         │     │         │    │         │    │             │   │ Operator `go`│
   └─────────┘     └─────────┘    └─────────┘    └─────────────┘   └─────────────┘
                                                       │                │
                                                       ▼                ▼
                                              Subject: "DEFCON 2    Subject: "DEFCON 1
                                              ALERT: ..."            EMERGENCY: ..."
                                              Red gradient           Black + red
                                              on white               (most aggressive)


                          ┌──────────────────────────────────────────────────────┐
                          │  DEFCON direction is INVERSE: lower number = more   │
                          │  threat. DEFCON 1 = nuclear war imminent.           │
                          └──────────────────────────────────────────────────────┘
```

## DEFCON Email Level Definitions

| DEFCON level | Email level | Subject prefix | Auto-fire? |
|---|---|---|---|
| 5, 4, 3 | — | — | — (silent, Telegram/Slack only) |
| 2 (high) | `level_2_high` | `DEFCON 2 ALERT: <headline>` | ✅ Yes |
| 1 (emergency) | `level_1_emergency` | `DEFCON 1 EMERGENCY: <headline>` | ❌ Operator `go` required |

## DEFCON State Transitions

```
DEFCON 5/4/3 ──escalation──> DEFCON 2 ──escalation──> DEFCON 1
     ↑                            │                        │
     │                            │                        │
     └─────── de-escalation ──────┴──────── de-escalation ─┘
```

**Emails only fire on escalations.** A de-escalation (e.g. 1 → 2) is good news but we don't email about it. The operator already knows the threat is reduced.

## Cooldown Rules (DEFCON)

| Rule | Default |
|---|---|
| Same level | **6 hours minimum** (DEFCON events are rare — don't spam) |
| Escalation (e.g. 2 → 1) | 6 hours |
| De-escalation | No email |
| Operator force-fire | Skip cooldown |

## When to Override

- ✅ Force-fire DEFCON 2 manually: `python scripts/send_defcon_alert.py --send --level level_2_high`
- ❌ Auto-fire DEFCON 1: NEVER. DEFCON 1 ALWAYS requires operator `go`. False DEFCON 1 emails destroy trust permanently.
- ✅ Override cooldowns for DEFCON 2: `--send` flag bypasses dry-run.
- ❌ Re-fire while sustained at the same level: NEVER. Only transitions trigger.

## Why DEFCON 3-5 Are Silent

If you already have Telegram/Slack notifications firing on every DEFCON escalation, you don't need emails for the routine levels. The email pipeline exists specifically for the **rare, consequential events** — DEFCON 1 (emergency) and DEFCON 2 (high). Sustained DEFCON 3 with no escalation doesn't justify an email blast.

If you want a different threshold (e.g. email on DEFCON 3), edit `defcon-email-trigger` SKILL.md step 3 and the corresponding `compute_current_alert_level()` logic in your monitor.

## Cross-Domain Correlation

If both ladders fire at the same time (e.g. DEFCON 2 + weather Storm Alert), the email-trigger skill for each domain runs independently. You may receive two emails. This is intentional — the action lists are different (one tells you to take political action, the other tells you to take shelter), and consolidating them would lose information.

Future versions may add a "cross-domain amplifier" skill that detects compound threats and increases severity. See [`docs/extending.md`](../docs/extending.md).