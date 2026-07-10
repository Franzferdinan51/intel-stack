# Documentation

Detailed docs for the Intelligence Stack.

| File | What it covers |
|---|---|
| [`setup.md`](setup.md) | **Required** OpenClaw + Hermes Agent setup steps before any cron will work. Must-read before installing. |
| [`architecture.md`](architecture.md) | System overview, data flow per tick, skill contracts for both domains (weather + DEFCON), state schemas, failure modes |
| [`faq.md`](faq.md) | Why-this-why-that, common questions, how it compares to existing weather apps |
| [`security.md`](security.md) | Threat model, anti-injection rules, scope guarantees, data handling |
| [`extending.md`](extending.md) | How to add a new domain (seismic, civic, financial) reusing the same pattern |

## Quick Links

- [Top-level README](../README.md) — landing page, quick start, both domain ladders
- [Skills](../skills/) — 8 skills total (4 weather + 4 DEFCON)
- [Workflows](../workflows/) — cron definitions + orchestrator
- [Scripts](../scripts/) — runnable Python utilities