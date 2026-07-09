# Contributing

Thanks for your interest in improving the Intelligence Stack! This project is MIT-licensed and accepts PRs from anyone.

## Ground Rules

**Do NOT submit:**
- Real email addresses, phone numbers, or any PII
- API keys, tokens, or credentials of any kind
- Anything that could be used to identify a private individual
- Real recipient lists — use `recipient1@example.com` style placeholders

**Always include:**
- Tests for new functionality (`pytest tests/`)
- Updated docs if you change user-facing behavior
- A clear commit message describing the change

## Development Setup

```bash
git clone https://github.com/<your-org>/intelligence-stack.git
cd intelligence-stack
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
pytest tests/
```

## Project Layout

```
intelligence-stack/
├── README.md                  # Landing page
├── LICENSE                    # MIT
├── .env.example               # Template for env vars
├── .gitignore                 # Excludes .env, state/, etc.
├── skills/
│   ├── weather-pull/          # NWS + SPC + FEMA + radar
│   ├── weather-monitor/       # State tracking + escalation
│   ├── weather-email-trigger/ # Scope + cooldown + level mapping
│   └── weather-email-send/    # HTML templates + AgentMail send
├── workflows/
│   ├── README.md
│   ├── cron-weather-watchdog.json
│   ├── agentmail-daily-healthcheck.json
│   └── alert-ladder.md
├── scripts/
│   └── orchestrate_alert.py
├── docs/
│   ├── README.md
│   ├── architecture.md
│   ├── faq.md
│   ├── security.md
│   └── extending.md
└── tests/
    ├── test_pull.py
    ├── test_monitor.py
    ├── test_trigger.py
    └── fixtures/
```

## Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(pull): add SPC mesoscale discussion endpoint
fix(trigger): correct cooldown logic for level 4 escalation
docs(readme): clarify geographic scope filter
test(monitor): add de-escalation case
```

## Pull Request Process

1. Fork the repo and create a feature branch from `main`.
2. Make your changes. Include tests.
3. Run `pytest tests/` — all tests must pass.
4. Run `python scripts/lint_md.py` (markdown lint).
5. Open a PR with:
   - A short title (≤72 chars)
   - A description of what changed and why
   - Any breaking changes called out explicitly
   - Screenshots / sample output if applicable

## Reporting Bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your environment (OS, Python version, package versions)

## Security Issues

See [`docs/security.md`](docs/security.md) for the reporting policy. **Do NOT open public GitHub issues for security bugs.**

## Adding a New Domain

See [`docs/extending.md`](docs/extending.md) for the full guide. TL;DR: add 4 new skills (pull, monitor, trigger, send) and a cron definition. Keep them in their own folder namespaced by domain.

## Code Style

- Python: PEP 8, type hints preferred, docstrings on public functions
- Markdown: CommonMark, header levels increment by one, no trailing whitespace
- JSON: 2-space indent, sorted keys where it aids review
- YAML (in cron files): 2-space indent, no tabs

## License

By contributing, you agree that your contributions will be licensed under the project's MIT license.