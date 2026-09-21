# Optional official evidence in early warning

`src/services/official_sources_v2.py` provides `await get_source_context(latitude=None, longitude=None, *, now=None, client=None)`. It returns `generated_at`, `scope`, `sources`, and `limitations`. These are separate contextual evidence feeds, not an assertion that a trained satellite/station fusion model exists.

## Configure server-only credentials

| Setting | Purpose |
| --- | --- |
| `CPCB_DATA_GOV_API_KEY` | An authorized data.gov.in API key. Do not put it in the browser or Git. |
| `CPCB_DATA_GOV_RESOURCE_ID` | Resource UUID; defaults to the existing project resource `3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`. Confirm this resource and access with your provider account. |
| `NASA_FIRMS_MAP_KEY` | A NASA FIRMS MAP_KEY requested from [FIRMS](https://firms.modaps.eosdis.nasa.gov/api/area/). |
| `FIRMS_MAP_KEY` | Compatibility alias if `NASA_FIRMS_MAP_KEY` is absent. |

Missing credentials produce `not_configured`, not invented readings. Rejected keys, rate limits, invalid responses and timeouts produce sanitized statuses without exposing credentials in URLs or messages. No shared demonstration key is used. Environment variables must be set in the actual deployed production environment; an example file does not enable a feed.

## NASA fire context

The adapter requests `VIIRS_NOAA20_NRT` for country `IND` and a two-calendar-day lookback from the documented [FIRMS API](https://firms.modaps.eosdis.nasa.gov/api/). The product is a thermal-anomaly/active-fire detection feed. The [NASA FIRMS FAQ](https://www.earthdata.nasa.gov/data/tools/firms/faq) describes VIIRS's nominal 375 m product and global near-real-time latency after overpass. Neither that pixel size nor the observation location is the precision of an air-quality measurement.

Records retain position, UTC acquisition time, fire radiative power in MW, confidence, and data-age flags. A 24-hour freshness threshold is an application context window, not a NASA certification of current burning. Low/unknown confidence is flagged. Absence of fire records does **not** mean clean air or absence of burning. Detections do not establish surface PM2.5, exposure, plume direction, stubble burning, industrial responsibility or a future pollution event. Wind transport, emissions and surface calibration would be needed before incorporating them into a predictive fusion model.

This adapter does not download or analyze satellite imagery, aerosol optical depth, or atmospheric column products. An imagery overlay elsewhere in the application is not numerical model ingestion. NOAA-20 is used rather than implying that every NASA sensor is connected.

## Government snapshot

The [CPCB real-time AQI catalogue on data.gov.in](https://www.data.gov.in/catalog/real-time-air-quality-index) is the provenance link. The authorized resource is accessed only through `api.data.gov.in/resource/{UUID}`, with `api-key`, JSON format, offset and limit parameters. No undocumented CPCB portal scraping or CAPTCHA bypass occurs.

The adapter preserves station, city/state, coordinates, `pollutant_id`, timestamp and `pollutant_min`, `pollutant_max`, `pollutant_avg` as **published values**. Units and index-versus-concentration semantics remain unverified. Consequently every record has `units_verified: false`, `unit: null`, and `quality_flags: ["units_unverified", ...]`; these numbers must not be plotted as µg/m³ or used to compute a new AQI/fit a concentration forecast. Finite nonnegative numerical parsing is a quality check, not proof of calibration. Invalid coordinates are rejected; missing/nonfinite/negative values become null. A timestamp without an offset is interpreted explicitly as Asia/Kolkata; source changes require revalidation.

Three hours is the current-station freshness threshold. Future or unparseable timestamps are not fresh. The current snapshot cannot create historical training data; successive snapshots need authorized scheduled archival and quality review.

## Bounds and output semantics

- NASA and government requests run concurrently, each with an 18-second total budget and eight-second individual request timeout. Each response is capped at 6 MB; redirects are rejected.
- Government reads up to six pages of 1,000 records. Partial pagination/failures and received/rejected counts are explicit. NASA parsing is bounded at 20,000 rows.
- National snapshots use a 15-minute, at-most-eight-entry in-process cache; unavailable responses are cached for one minute. Local calls reuse national snapshots and select evidence within 100 km for contextual review only. **That radius is not sensor measurement coverage or a plume model.**
- Up to 300 latest records are returned per source, with `records_in_scope`, `records_returned` and `display_truncated`. Fresh/stale counts refer to all parsed records in the selected scope, not just the displayed subset.
- `available` means the provider response parsed, not that all records are fresh or that air is safe. `delayed` means records exist but none meets the freshness window. `partial` means retrieval coverage is incomplete; inspect freshness separately.
- This cache is neither durable nor shared across serverless instances. Cold instances can refetch. A durable scheduled collector, deployment-wide rate coordination, historical calibration and alert delivery are separate operational work. Credentials alone do not establish continuous nationwide monitoring.

## Offline verification

`python -m unittest tests.test_official_sources_v2` uses synthetic mocked payloads. It checks configuration boundaries, unit honesty, timestamps, pagination, partial failures, coordinate/size caps, local scoping, NASA context labeling and credential redaction. A passing mocked suite is not proof of a working production key; verify sanitized statuses on the deployed early-warning response as well.
