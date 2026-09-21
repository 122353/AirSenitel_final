# Early-warning research release

## What is implemented

The public landing page, India outlook and authenticated authority dashboard
share the same warning component. It automatically fetches six-pollutant,
six-hour regional-model screening. The default batch contains one representative
location for each of India's 36 states/union territories. Place search requests
other coordinates on demand. These are point forecasts, not administrative-area
measurements or an exhaustive all-city inventory.

`GET /api/v2/early-warning` provides the public model/context feed.
`GET /api/v2/authority/early-warning` requires the existing server-side authority
authorization. Case records, photos, local-device records and model-management
operations retain their separate private authorization boundaries.

## Three different signal types

1. **Future regional model watch:** current modeled value is below a robust rise
   threshold, and a future hourly point crosses it within six hours. Lead time is
   to the first crossing, not the later peak. All earlier chart points are model
   estimates too. The underlying CAMS global output is approximately 45 km and
   natively three-hourly; interpolated hourly values do not create microscopic
   resolution. This is deterministic screening of an external forecast, not a
   newly trained sensor/satellite AI fusion model.
2. **Ongoing modeled rise:** the model is already above its threshold. This is
   neither an advance warning nor a sensor-confirmed event.
3. **Selected-station evidence:** `/api/v2/monitoring` adds `station_warning`.
   Two consecutive, quality-accepted hourly observations above a pre-event
   baseline support an observed rise. Eligible future outputs from the existing
   station-specific persistence/ridge research model support a station forecast
   watch. Stale/archive/mobile/mixed-series/unsupported-unit data cannot warn.
   This lane describes only the explicitly selected station and pollutant, not
   every station or the currently searched locality.

The station-rise baseline requires 12 contiguous prior hours, excluding the two
latest hours. Both regional and station screens use median + max(35% of median,
3 × 1.4826 × MAD, pollutant-specific absolute-rise floor). Thresholds are research
engineering choices, not health limits. Concentration holdout metrics do not
establish sudden-event warning accuracy. Event recall, false-alert rate and
useful warning lead time still require prospective evaluation.

## Sources and quality

- CAMS via Open-Meteo supplies the six pollutant model series. Open-Meteo weather
  provides separately labeled context; it is not silently weighted into an
  untrained prediction score.
- OpenAQ supplies source-labeled station data to the existing station workflow.
  The directory is larger than the number of stations queried per refresh; the
  UI now displays both counts instead of implying every entry is live.
- The CPCB/data.gov.in adapter preserves published values and provenance. Unit
  semantics must be verified before these fields can train a concentration
  model or be displayed as a new official AQI.
- NASA FIRMS is optional fire-detection context, not imagery analysis or surface
  AQI. At the user's request it remains explicitly unavailable without a key.

See [SOURCE_INTEGRATIONS.md](SOURCE_INTEGRATIONS.md) for source credentials,
pagination, timestamp and rate/caching constraints. No credentials belong in
Git, frontend source, or client-prefixed environment variables.

## Operational boundaries

This release is cached, on-request screening with a two-minute browser refresh.
It is **not** a continuously running national ingestion/dispatch service.
Process-local caching/coalescing does not coordinate quotas across serverless
instances. Forecast values are not measurements, missing data is not clean air,
and a monitor's search distance is not its measurement coverage radius.

For a production nationwide early-warning service, the remaining work includes
durable scheduled collection and historical storage; feed access and licensing;
all-station ingestion quotas; locally calibrated sensor coverage; satellite
transport/fusion modeling; measured-event backtesting; and agreed notification
and authority response procedures. No external notification/dispatch is enabled.

## Verification

Offline tests cover timestamps, unit compatibility, missing/conflicting data,
first-crossing lead times, ongoing-versus-future distinctions, source failures,
cache expiry/coalescing, the real monitoring response contract, and denied
unauthenticated authority requests. Fixtures are synthetic test-only inputs;
the application does not serve those fixtures to users.

Live local verification returned 36 representative locations, six pollutants
each, weather context, and an on-demand Rohini result. The browser rendered
the warnings and timeline without console errors. This verifies plumbing, not
scientific predictive skill or nationwide microscopic coverage.
