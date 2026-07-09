---
name: weather-pull
description: Pull weather data for a single location from NWS, NOAA, FEMA, local sources.
metadata:
  hermes:
    tags: [Weather, NWS, NOAA, FEMA, Intelligence, Pull]
version: 0.1.0
author: Hermes
---

# Weather Pull

Pulls weather, alert, and hazard data for a **single geographic point** from verified public sources. Does NOT send any email. Does NOT make escalation decisions — it just gathers and returns structured JSON. Caller decides what to do with it.

## When to Use

- User asks "check the weather for <location>" / "what's NWS saying" / "pull radar" / "any storms near <zip>?".
- Another skill (e.g. `weather-monitor`) needs fresh data on a schedule.
- Pre-flight before sending an alert — confirm the threat is real before firing `weather-email-send`.

## Scope — Geographic Pin

- **Single location at a time.** Driven by `HOME_LAT` / `HOME_LON` env vars or explicit override.
- **Forecast office**: NWS office that covers the home point. Determined by NWS API metadata.
- **County / zone**: Pulled from NWS `county` and `forecastZone` fields.
- **Other locations**: ONLY pulled if the user explicitly requests them. Never auto-expand scope.

## Prerequisites

- No API keys needed — all sources are public.
- `requests` or `urllib` (stdlib is fine; `web_extract` tool is preferred for HTML pages).
- Python 3.10+.

## How to Run

Invoke through the `terminal` tool or `web_extract`. Run the source list in parallel where possible.

## Quick Reference

- NWS Point: `https://forecast.weather.gov/MapClick.php?lat=<LAT>&lon=<LON>`
- NWS Active Alerts (API): `https://api.weather.gov/alerts/active?point=<LAT>,<LON>`
- NWS ILN (example WFO): `https://api.weather.gov/offices/ILN`
- NWS ILN homepage (example): `https://www.weather.gov/iln/`
- SPC Outlooks: `https://www.spc.noaa.gov/products/outlook/`
- SPC Day 1: `https://www.spc.noaa.gov/products/outlook/day1otlk.html`
- FEMA IPAWS (archive): `https://www.fema.gov/api/open/v1/IpawsArchivedAlerts`
- Local radar (replace station code): `https://radar.weather.gov/ridge/standard/<STATION>_loop.gif`

## Procedure

1. **NWS Point Forecast** through `web_extract`:
   ```
   url: https://forecast.weather.gov/MapClick.php?lat=<LAT>&lon=<LON>
   char_limit: 8000
   ```
   Extract: current temp/wind/humidity/pressure, 7-day forecast, hazards banner.

2. **NWS Active Alerts (API)** through `web_extract` (returns JSON):
   ```
   url: https://api.weather.gov/alerts/active?point=<LAT>,<LON>
   ```
   Headers to set if using curl: `User-Agent: intelligence-stack/1.0`.
   Extract: `features[].properties.{event,headline,severity,areaDesc,expires}`.

3. **NWS Forecast Discussion (AFD)** through `web_extract`:
   ```
   url: https://forecast.weather.gov/product.php?site=NWS&product=AFD&issuedby=<WFO>
   ```
   Extract: the latest AFD — gives the meteorologist's reasoning + threat assessment for the local area.

4. **SPC Day 1 Outlook** through `web_extract`:
   ```
   url: https://www.spc.noaa.gov/products/outlook/day1otlk.html
   ```
   Extract: categorical risk (TSTM/MRGL/SLGT/ENH/MDT/HIGH), tornado probability, wind probability, hail probability. Confirm the home county is in the outlook area.

5. **FEMA IPAWS (if a major event is unfolding)** — only check this when an alert is already active:
   ```
   url: https://www.fema.gov/api/open/v1/IpawsArchivedAlerts?$filter=contains(areaDesc,'<COUNTY>')
   ```
   Extract: any WEA (Wireless Emergency Alert) or EAS issuances for the county.

6. **Local radar + regional news** (last, for ground truth) through `web_extract`:
   ```
   urls:
     - https://radar.weather.gov/ridge/standard/<STATION>_loop.gif
     - <local TV station URL>
   ```
   Extract: current radar loop + any local-news-only reports (power outages, road closures).

7. **Compile and return** a structured summary with these fields:
   - `current`: temp, wind, humidity, pressure, conditions
   - `forecast_7day`: short text per day
   - `active_alerts`: list of {event, severity, expires, headline}
   - `spc_day1`: categorical, tornado_prob, wind_prob, hail_prob
   - `afd_discussion`: 1-paragraph meteorologist assessment
   - `fema_ipaws`: list of WEAs (or `none`)
   - `local`: regional news summary
   - `escalation_signal`: `none` / `watch` / `warning` / `emergency` (rough triage only — caller decides)
   - `pulled_at`: UTC timestamp
   - `sources_ok`: list of source names that returned data (so the caller knows what failed)

## Pitfalls

- **NWS API requires a User-Agent.** Bare curl/requests will get 403. Set `User-Agent` to anything reasonable (`intelligence-stack/1.0`).
- **forecast.weather.gov URLs are HTML.** Use `web_extract`, not the API. The API endpoints are `api.weather.gov/*`.
- **api.weather.gov returns GeoJSON.** `features[].properties.event` is the alert type — common values: `Tornado Watch`, `Tornado Warning`, `Severe Thunderstorm Warning`, `Flash Flood Warning`, `Special Weather Statement`.
- **SPC outlooks only refresh every few hours.** Don't poll more than once per 30 min — there's no new data before that.
- **County names vs zone codes.** Counties are sometimes listed as `<ST>Z###` (state + zone number) in NWS products, not by name. Match on either.
- **Forecast office vs airport code.** A WFO is a 3-letter code (e.g. `ILN` = Wilmington OH). An airport code is 4 letters (e.g. `KDAY` = Dayton airport). Don't conflate.
- **Don't pull multiple locations by default.** If the user asks for another city, pull that city — but don't auto-expand the home location's scope.
- **FEMA IPAWS is for verification, not primary alerting.** It's authoritative for WEAs but laggy and bureaucratic. Use NWS first.

## Verification

```bash
python -c "
import urllib.request, json, os
lat, lon = os.getenv('HOME_LAT', '39.8645108'), os.getenv('HOME_LON', '-84.1321902')
req = urllib.request.Request(
    f'https://api.weather.gov/alerts/active?point={lat},{lon}',
    headers={'User-Agent': 'intelligence-stack/1.0'}
)
data = json.loads(urllib.request.urlopen(req, timeout=10).read())
print('OK alerts:', len(data.get('features', [])))
"
```

Expected: `OK alerts: 0` or higher. If 403, the User-Agent is missing. If connection refused, the host has no outbound HTTPS — check the network.