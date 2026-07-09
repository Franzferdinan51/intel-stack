# Extending the Stack

The weather pipeline is just **one application** of a more general pattern:

```
pull → monitor → trigger → send
```

You can reuse the same architecture for other intelligence domains. This doc walks through adding a new one.

## Pattern Reuse

Each of the four weather skills has a job that doesn't depend on weather specifics:

| Weather skill | Generalized role | Reusable? |
|---|---|---|
| `weather-pull` | Pull data from a public API | Yes — copy structure, swap endpoints |
| `weather-monitor` | Detect state changes over time | Yes — generic enough as-is |
| `weather-email-trigger` | Decide if/when to alert + scope + cooldown | Yes — works for any domain |
| `weather-email-send` | Render HTML + send | Yes — copy template structure |

To extend, replace each weather-specific bit with your domain's logic. The contracts (input/output JSON shapes) stay the same.

## Example: Seismic Monitor (USGS Earthquakes)

### Step 1: Define the scope

```python
# .env additions
HOME_LAT=39.8645108
HOME_LON=-84.1321902
SEISMIC_MIN_MAGNITUDE=2.5          # ignore smaller quakes
SEISMIC_RADIUS_KM=200              # only alert for quakes within 200km
```

### Step 2: Create `seismic-pull` skill

Copy `skills/weather-pull/` to `skills/seismic-pull/`. Change the SKILL.md to point at:

- `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude=<LAT>&longitude=<LON>&maxradiuskm=<RADIUS>&minmagnitude=<MAG>`

Update the output contract to include `magnitude`, `depth_km`, `place`, `time_utc`.

### Step 3: Create `seismic-monitor` skill

Copy `skills/weather-monitor/`. Change the level mapping:

```python
def compute_level(pulled):
    quakes = pulled.get("recent_quakes", [])
    max_mag = max((q["magnitude"] for q in quakes), default=0)

    if max_mag >= 5.0: return "emergency"
    if max_mag >= 4.0: return "warning"
    if max_mag >= 3.0: return "watch"
    return "none"
```

### Step 4: Create `seismic-email-trigger`

Copy `skills/weather-email-trigger/`. Same logic — scope filter on lat/lon, cooldown rules, level mapping.

### Step 5: Create `seismic-email-send`

Copy `skills/weather-email-send/`. New subject prefixes:

- Level 1: `Seismic Watch - <Area> - M<mag> detected`
- Level 2: `URGENT UPDATE: M<mag> earthquake near <Area>`
- Level 3: `Seismic Alert: M<mag> - <distance> from <Area>`
- Level 4: `WAKE-UP CALL: Aftershock risk elevated near <Area>`

### Step 6: Wire up the cron

Drop `cron-seismic-watchdog.json` into the cron list. Runs every 30 min (USGS doesn't refresh faster than that for most regions).

## Other Domains

| Domain | Data source | State file |
|---|---|---|
| Weather | NWS / SPC / FEMA / radar | `state/weather-<ZIP>.json` |
| Seismic | USGS Earthquake API | `state/seismic-<ZIP>.json` |
| Civic (local gov) | City RSS feeds, county alert system | `state/civic-<ZIP>.json` |
| Air quality | AirNow API | `state/air-quality-<ZIP>.json` |
| Financial (crypto) | CoinGecko, on-chain events | `state/crypto-<symbol>.json` |

Each one follows the same pattern. The state file is namespaced by domain + identifier.

## Sharing State Across Domains

If you want `seismic-monitor` to know about `weather-monitor` state (e.g. "is there a tornado watch AND an earthquake?"), just have it read the other domain's state file:

```python
weather_state = json.loads(Path("~/.openclaw/workspace/state/weather-45424.json").expanduser().read_text())
seismic_state = json.loads(Path("~/.openclaw/workspace/state/seismic-45424.json").expanduser().read_text())

if weather_state.get("current_level") == "emergency" and seismic_state.get("current_level") != "none":
    # Compound emergency: amplify the alert
    ...
```

This is how you build multi-domain correlation without coupling the skills.

## Anti-Patterns

❌ **Don't merge domains into one giant skill.** Keep them separate so each can evolve independently.

❌ **Don't make `weather-email-send` aware of seismic.** It only knows how to send. Domain knowledge lives in `weather-monitor` and `weather-email-trigger`.

❌ **Don't share HTML templates across domains.** Each domain has its own visual language (red for storms, brown for quakes, etc.).

❌ **Don't auto-fire level 4 across all domains.** Each domain's level 4 needs its own confirmation policy.

## Contributing a New Domain

1. Fork the repo
2. Add `skills/<domain>-pull/`, `skills/<domain>-monitor/`, etc.
3. Add `workflows/cron-<domain>-watchdog.json`
4. Add a new section to this doc with the data source + state file path
5. Open a PR

We'll review for: scope-filter correctness, anti-injection compliance, level-mapping rationale, and template safety.