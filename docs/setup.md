# Setup Requirements

This document lists **everything you must install, configure, and verify** before the Intelligence Stack will run correctly. It is split into two sections:

1. **[OpenClaw setup](#openclaw-setup)** — required if you want any cron-driven intelligence pipeline to run unattended.
2. **[Hermes Agent setup](#hermes-agent-setup)** — required if you want the agent runtime to load the skills + memory provider plugins.

Each step is a **requirement**, not a recommendation. Skipping any step means the corresponding pipeline will not function.

**Authoritative sources used to write this doc:**
- [Hermes Agent — Memory Provider Plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin)
- [Hermes Agent — Memory Providers (User Guide)](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers)
- [Hermes Agent — Built-in Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/built-in-plugins)
- [Hermes Agent — Plugins User Guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [OpenClaw — Skills, Cron Jobs, and Automation (RamNode)](https://www.ramnode.com/guides/series/openclaw/skills-automation)
- [OpenClaw — Isolated cron session bug #10804](https://github.com/openclaw/openclaw/issues/10804)
- [DuckBot RAG Memory — INSTALL.md](https://github.com/Franzferdinan51/duckbot-rag-memory/blob/main/INSTALL.md)

---

## OpenClaw Setup

OpenClaw is the runtime that hosts cron jobs, ingests skills, and routes notifications. **Every cron in this repo assumes OpenClaw is installed and configured.**

### Requirement 1: OpenClaw binary is installed

```bash
# Verify the binary exists
openclaw --version
```

Expected: prints `openclaw X.Y.Z` (any 2026.x release). If missing, install per the [OpenClaw GitHub](https://github.com/openclaw/openclaw) instructions for your platform (Windows / macOS / Linux).

### Requirement 2: Workspace directory exists

The Intelligence Stack writes state files to `~/.openclaw/workspace/state/` and logs to `~/.openclaw/workspace/logs/`. Both must exist and be writable.

```bash
# Required directory tree
~/.openclaw/
└── workspace/
    ├── state/        # state files for each domain (e.g. weather-45424.json, defcon-email.json)
    ├── logs/         # per-cron log files (e.g. weather-watchdog.log)
    └── skills/       # additional OpenClaw skills you author (separate from Hermes skills)
```

```bash
mkdir -p ~/.openclaw/workspace/{state,logs,skills}
```

### Requirement 3: A Telegram bot + chat ID for cron delivery

Every cron in this repo uses `deliver: "telegram,local"` so you see cron output in chat AND get a local log. **Without these env vars, cron output goes to `/dev/null` and you'll have no idea whether the pipeline ran.**

```bash
# 1. Create a bot via @BotFather in Telegram. You'll get a token like:
export TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"

# 2. Send any message to your new bot, then visit:
#    https://api.telegram.org/bot<TOKEN>/getUpdates
#    Look for "chat":{"id": <CHAT_ID>}. For a 1:1 DM with the bot, it's a positive integer.
export TELEGRAM_HOME_CHAT_ID="588090613"
```

These two vars are required for every weather + DEFCON cron in this repo. Add them to your shell profile (`.bashrc`, `.zshrc`, or PowerShell `$PROFILE`) so they persist across reboots.

### Requirement 4: OpenClaw cron scheduling is enabled

OpenClaw runs crons via its built-in scheduler. Verify with:

```bash
openclaw crons list
```

Expected: prints a JSON list of registered crons. If the command errors, the scheduler daemon isn't running — start it per the OpenClaw docs.

### Requirement 5: Each cron uses `deliver: "telegram,local"`

All cron definitions in `workflows/` use this delivery pair. **You must not change it to `local`-only** or you'll lose visibility into cron runs.

---

## Hermes Agent Setup

Hermes is the agent runtime that loads the skills + memory provider plugins. **Every skill in this repo is a Hermes skill format with `SKILL.md` + optional `references/`.**

### Requirement 1: Hermes Agent is installed

```bash
# Verify
hermes --version
```

Expected: `hermes-agent 0.14.x` or newer. Install per the [Hermes Agent GitHub](https://github.com/nousresearch/hermes-agent).

### Requirement 2: Skills directory exists at `~/.hermes/skills/`

Hermes auto-discovers skills from this path. The Intelligence Stack's 8 skills (4 weather + 4 DEFCON) must live here.

```bash
# Required layout
~/.hermes/
└── skills/
    ├── weather-pull/          SKILL.md (+ optional references/)
    ├── weather-monitor/
    ├── weather-email-trigger/
    ├── weather-email-send/    SKILL.md + references/{1..4}_*.{html,txt,json}
    ├── defcon-pull/
    ├── defcon-monitor-email/
    ├── defcon-email-trigger/
    └── defcon-email-send/     SKILL.md + references/{level_2_high,level_1_emergency}.{html,txt,json}
```

Copy from this repo:

```bash
# From the cloned intelligence-stack directory
cp -r skills/* ~/.hermes/skills/

# Verify each one is discoverable
hermes skills list | grep -E "weather-|defcon-"
```

Expected: 8 skills listed.

### Requirement 3: Memory provider plugin installed (REQUIRED for skill memory)

The skills in this repo don't carry their own memory — they rely on the DuckBot RAG Memory plugin to provide persistent context. **Without this plugin, every Hermes session starts with no prior context.**

```bash
# Required repo: duckbot-rag-memory at ~/duckbot-rag-memory
# Clone it
git clone https://github.com/Franzferdinan51/duckbot-rag-memory ~/duckbot-rag-memory

# Install Python deps (ChromaDB + LM Studio client + RRF reranker)
cd ~/duckbot-rag-memory
python -m venv .venv
source .venv/bin/activate          # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env to set LMSTUDIO_API_KEY (recommended) or OPENAI_API_KEY

# Verify
./duck-memory doctor
```

Expected: doctor reports "OK" for all checks. See [INSTALL.md](https://github.com/Franzferdinan51/duckbot-rag-memory/blob/main/INSTALL.md) for the full setup.

### Requirement 4: Memory provider plugin is wired into Hermes

The plugin lives at `~/duckbot-rag-memory/hermes/plugins/duckbot_brain/`. Per the [Hermes plugin docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins), user-installed plugins go in `~/.hermes/plugins/`:

```bash
# Symlink the plugin into Hermes's plugins directory
mkdir -p ~/.hermes/plugins
ln -s ~/duckbot-rag-memory/hermes/plugins/duckbot_brain ~/.hermes/plugins/duckbot-brain

# Or copy it
cp -r ~/duckbot-rag-memory/hermes/plugins/duckbot_brain ~/.hermes/plugins/duckbot-brain

# Verify Hermes discovered it
hermes plugins list | grep duckbot-brain
```

Expected: `duckbot-brain` appears in the list with status `enabled`.

**If you skip this step:** Hermes will fall back to its built-in MEMORY.md + USER.md, the skills will lose their recall context, and you'll see degraded answers across sessions.

### Requirement 5: Set the duckbot-brain as the active memory provider

```bash
# Via the Hermes CLI (writes to ~/.hermes/config.yaml under plugins.duckbot-brain)
hermes memory setup duckbot-brain

# Or manually edit ~/.hermes/config.yaml:
#   memory:
#     provider: duckbot-brain
```

Verify:

```bash
hermes memory status
```

Expected: `Active provider: duckbot-brain`.

### Requirement 6: LM Studio (or OpenAI) is reachable for embeddings

The DuckBot RAG Memory plugin calls LM Studio (or OpenAI) for embeddings on every recall. **If neither is reachable, the plugin silently fails closed — every Hermes session will look like it has zero prior context.**

```bash
# Option A: LM Studio local
# 1. Install LM Studio: https://lmstudio.ai/
# 2. Start the local server (default port 1234)
# 3. Set in ~/.duckbot-rag-memory/.env:
#      LMSTUDIO_API_KEY=lm-studio
#      LMSTUDIO_BASE_URL=http://localhost:1234/v1

# Option B: OpenAI cloud
#      OPENAI_API_KEY=sk-...

# Verify
cd ~/duckbot-rag-memory
./duck-memory doctor
```

Expected: doctor reports embeddings reachable.

### Requirement 7: `.env` is set for the weather + DEFCON pipelines

The Intelligence Stack reads env vars for home location, recipients, and AgentMail. Required minimum:

```bash
# AgentMail (sender account)
export AGENTMAIL_API_KEY=am_us_<your-key>
export AGENTMAIL_INBOX=<your-username>@agentmail.to

# Home location (for weather geographic scope filter)
export HOME_LAT=39.8645108
export HOME_LON=-84.1321902
export HOME_ZIP=45424
export HOME_WFO=ILN
export HOME_COUNTY="Montgomery County, OH"

# Recipients
export ALERT_RECIPIENTS=alice@example.com,bob@example.com
export DEFCON_ALERT_RECIPIENTS=alice@example.com,bob@example.com
```

**Never commit `.env`.** Use `.env.example` (in this repo) as your template and store the real file outside the repo, with env var pointing to it.

### Requirement 8: Install Python deps for sending email

```bash
pip install agentmail
```

Verify:

```bash
python -c "from agentmail import AgentMail; print('agentmail SDK OK')"
```

Expected: prints `agentmail SDK OK`. If `ModuleNotFoundError`, re-run `pip install agentmail`.

---

## Per-Cron Prerequisites (REQUIRED for each)

Every cron in `workflows/` assumes all of the above. **Additionally, each cron has its own minimum inputs:**

| Cron | Schedule | Min env vars | Skill chain |
|---|---|---|---|
| `cron-weather-watchdog.json` | daily 08:00 | `HOME_LAT`, `HOME_LON`, `HOME_ZIP`, `HOME_COUNTY`, `ALERT_RECIPIENTS` | `weather-pull` → `weather-monitor` → `weather-email-trigger` → `weather-email-send` |
| `cron-defcon-watchdog.json` | 3x daily 08/14/20 | `DEFCON_STATE_PATH`, `DEFCON_ALERT_RECIPIENTS` | `defcon-pull` → `defcon-monitor-email` → `defcon-email-trigger` → `defcon-email-send` |
| `agentmail-daily-healthcheck.json` | daily 09:00 | `AGENTMAIL_API_KEY`, `AGENTMAIL_INBOX`, `TELEGRAM_HOME_CHAT_ID` | `agentmail-onboard` skill (built-in) |

If any of those env vars are missing, the cron will fail at the point the skill needs them. There's no partial-success fallback — the email simply won't send.

---

## Verification Checklist (run before first cron tick)

After installing everything, run these in order:

```bash
# 1. OpenClaw binary works
openclaw --version

# 2. Telegram bot + chat ID are configured
echo "$TELEGRAM_BOT_TOKEN" | head -c 10
echo "$TELEGRAM_HOME_CHAT_ID"

# 3. Hermes can discover all 8 skills
hermes skills list | grep -E "weather-|defcon-" | wc -l   # → 8

# 4. duckbot-brain plugin is loaded + active
hermes plugins list | grep duckbot-brain
hermes memory status

# 5. DuckBot RAG Memory is reachable
cd ~/duckbot-rag-memory && ./duck-memory doctor

# 6. AgentMail SDK installed
python -c "from agentmail import AgentMail; AgentMail(api_key='$AGENTMAIL_API_KEY').inboxes.get(inbox_id='$AGENTMAIL_INBOX')"

# 7. All crons registered with OpenClaw
openclaw crons list | python -c "import json, sys; print(len(json.load(sys.stdin)))"

# 8. Manual cron run works
openclaw crons run --name "Weather Outlook Watchdog (Daily)"
# Expected: Telegram message arrives with "Weather outlook ..." format
```

If any step fails, **fix it before relying on unattended cron output**. The crons will not surface setup failures — they go silent instead.

---

## Failure Modes (what happens when setup is incomplete)

| Missing | Symptom |
|---|---|
| OpenClaw not installed | Crons silently don't fire |
| `TELEGRAM_BOT_TOKEN` missing | Cron output discarded, no Telegram delivery |
| Hermes skills not in `~/.hermes/skills/` | `hermes skills list` doesn't show them, crons fail with "skill not found" |
| duckbot-brain plugin not symlinked | Hermes falls back to built-in MEMORY.md, recall quality drops sharply |
| `LMSTUDIO_API_KEY` missing | Every Hermes session starts with zero recall context |
| `HOME_LAT` / `HOME_LON` missing | Weather skill pulls data for default location (0,0 = Atlantic ocean), all scope filters reject alerts |
| `AGENTMAIL_API_KEY` missing | Email step raises `AuthenticationError`, cron returns error |
| `ALERT_RECIPIENTS` empty | Email step raises `NoRecipientsError`, cron returns error |

**The crons don't paper over missing config. They fail visibly (status: error in cron history) or invisibly (silent if `deliver: local`).** Fix setup issues BEFORE relying on unattended operation.

---

## Why "recommendation" → "requirement"

Earlier versions of this doc used language like "we recommend" and "you may want to" for steps like the Telegram bot, LM Studio setup, and the memory provider plugin. In practice that produced two failure modes:

1. **Skipping the Telegram bot** → crons silently fail, user never knows
2. **Skipping the memory provider** → answers degrade silently across sessions

Both failures are invisible until something goes wrong. The reframing here is deliberate: these aren't optional best-practices. They're load-bearing dependencies. The cost of setting them up is small; the cost of skipping them is silent system degradation.

If a step here is genuinely optional for your use case, it will say so explicitly. Otherwise, treat every line above as a hard prerequisite.