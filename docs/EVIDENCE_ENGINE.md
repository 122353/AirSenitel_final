# Evidence engine v2

`src.services.monitoring_v2.build_snapshot(station_id=None, pollutant="pm25", mode="live")`
returns a JSON-ready dictionary. The API owns authentication, HTTP caching/rate
limits, and device storage. This service reads only `OPENAQ_API_KEY` from the
server environment and never includes it in response data. It has no device
credentials and does not send messages, publish reports, or issue enforcement.

## Response contract

| Field | Meaning |
| --- | --- |
| `schema_version` | `2.0` |
| `status` | `live`, `partial`, `delayed`, or `unavailable`; refers to the selected pollutant/station |
| `requested_mode` | `live` or `archive` |
| `stations` | Actual fetched location metadata, sensor/pollutant units, point coordinates, optional latest measurements and provenance |
| `selected_station_id`, `selected_pollutant` | Explicit selection, with no silent station substitution for a supplied ID |
| `history` | A single station/sensor/pollutant/unit series in `points`, original timestamps, rejected row count, query completeness |
| `forecast` | Persistence/trained ridge research result with `status`, `points`, origin, units, chronological evaluation and interval coverage |
| `candidates`, `candidate_status` | Corroborated station anomaly review packets and evidence availability; causes remain unverified |
| `coverage` | Query bounding box, pagination completeness, discovered count, limited measurement-fetch scope |
| `sources` | Availability, provenance, delays, upstream labels |
| `weather` | Separately labelled Open-Meteo weather model context |

Measurements contain `station_id`, `sensor_id`, `pollutant`, `value`, `unit`,
`original_unit`, `observed_at`, `collected_at`, `age_hours`, `fresh`,
`quality: {status, reasons, upstream_flags}`, `averaging_period`, `source` and
`source_url`. Quality states are `valid` (basic checks and explicit no upstream
flags), `provisional` (upstream quality flags unavailable), and `rejected`.
Even `valid` is not an instrument calibration or regulatory certification.

Chart only the supplied station/unit series. Display its unit and timestamps.
Do not turn a missing series into zero, interpolate gaps silently, combine ppb
with mass concentration, or draw a station sensing circle. Both
`search_distance_km` and `representativeness_radius_km` default to null. The
corroboration station-distance field is a geometric distance, not a sensing
radius or proof of a local plume. There is no locality geometry in this service.

## Bounded collection

Live station discovery queries OpenAQ v3 within longitude/latitude bounding box
`76.8,28.3,77.6,29.0`, filtered to India. This box includes Delhi/NCR; it is not a
Delhi administrative boundary or an inventory of all physical hardware. Up to
four pages of 500 locations are fetched. String totals such as `>100` remain
unknown totals; hitting a page limit or a repeated page reports incomplete.
Metadata count and the count of stations whose measurements were requested are
separate fields. Only the selected station and at most two eligible nearby
stations have latest values and seven days of hourly history fetched. All other
stations remain discoverable/selectable without being presented as checked-live.

There are at most two unique snapshot collections in flight per process and
three concurrent requests per collection, six seconds per request, bounded
JSON/archive bytes and CSV rows, and a 45-second total collection deadline.
Simultaneous identical queries share one shielded task, so one disconnected
caller cannot cancel another caller's collection. Excess distinct requests return
`status: overloaded`, `error_code: snapshot_capacity`, and
`retry_after_seconds: 15`; the API maps this to HTTP 429 with `Retry-After`.
Cache entries last 60 seconds; at most 24 snapshot query combinations and four
credential-scoped station-discovery results are retained. Discovery itself is
coalesced across station/pollutant queries, with a 25-second collection deadline.
Failure results are cached briefly as well to avoid immediate retry bursts.

These controls and caches are process-local. They do not enforce a distributed
limit or guarantee the shared OpenAQ credential cannot exhaust its quota across
workers/instances. Public deployments require an edge or distributed request
rate limit and upstream-quota monitoring. The response labels this limitation
in `request_protection`. Failure states
contain sanitized codes, never upstream bodies or credentials.

Without a key, or for explicit archive mode, only known archive locations 17 and
235 are attempted for three eligible days. Values and coordinates are read from
the downloaded records, never constants. The public archive is written 72 hours
after each local day ends; the minimum delay and actual observation time remain
visible. These records cannot create current forecasts or candidates, and their
unavailable upstream quality flags remain explicit. Missing files yield missing
data. Provider/licence information absent from archive files is left unknown.

## Forecast and anomaly gates

Persistence repeats the latest valid hourly observation. It is an untrained
baseline. It requires 48
same-station/sensor/pollutant/unit points, at least 75% hourly completeness,
strictly nonfuture timestamps, and no upstream quality flags. A forecast origin
older than three hours blocks current predictions. Forecast points already in
the past are omitted.

The first half of the ordered series provides initial history, the next quarter
calibrates absolute residual intervals, and the newest quarter evaluates them.
Each rolling forecast uses only its own earlier origin. Calibration never uses
the heldout quarter. One-, three- and four-hour outputs each require at least
eight calibration and eight heldout pairs with exact time offsets. Evaluation
includes dates, MAE, RMSE, row counts, empirical interval coverage and predictions.
90% intervals are empirical research intervals, not guaranteed coverage under
changing pollution conditions. Stale valid data may retain historical evaluation
while current predictions stay empty.

With at least 120 valid hourly observations, a trained autoregressive ridge
candidate is also fitted. Its five inputs are lags 1, 2, 3, 6 and 24: lag 1 is the
latest value available at forecast origin, and lag 24 is 23 hours earlier. A
separate direct model predicts each 1-, 3- and 4-hour target. Input centering and
scaling use fitting data only. A fixed ridge penalty of 1.0 applies to the five
standardized coefficients, with an unpenalized intercept; a bounded standard
library linear solver avoids adding a numerical framework dependency. The same
nonnegative output constraint applies throughout evaluation and current output.

For this comparison, the chronological split is first 50% fitting, next 15%
validation for model selection, next 15% interval calibration, and final 20%
untouched holdout. Both models use the same exact lag/target pairs. The lower
validation MAE selects the model for each horizon, with persistence winning ties.
After selection, ridge is refitted using only the fitting and validation periods;
calibration and holdout never enter coefficients. The model is fixed through
later rolling-origin evaluation, while each prediction may use measurements
already observed by its own origin. Both candidates' heldout MAE, RMSE and
interval coverage are reported. No model is selected using those heldout scores.
Validation and calibration targets whose forecast origins precede the last
target used in the corresponding fit are purged before scoring. With contiguous
hourly history, this removes the first horizon-minus-one rows of each evaluation
split. Every scored origin is at or after its model's fit cutoff. After purging,
at least 24 initial fitting examples and eight examples in each validation,
calibration and heldout split are required. Purged counts and origin/fit cutoffs
are reported per horizon. Refitting may use all train/validation targets that
precede calibration; the purge applies to scoring, not to data already available
at the later refit cutoff.
Missing exact lags or insufficient split counts decline the trained comparison
and retain the existing persistence evaluation.

`forecast.model` is `persistence`, `ridge_autoregression`, or `horizon_selected`
when choices differ by horizon. Each forecast point and horizon metric carries
its selected model. `trained_model` is true only when an actually fitted ridge
was selected; `evaluation.trained_candidate` separately reports whether a ridge
candidate was fitted and compared even when persistence won. Training row counts,
target date limits and a training-data fingerprint document each final fit. The
fit is ephemeral for the bounded response; no pickle or model artifact is loaded
or saved. This is a small trained research candidate, not evidence of validated
machine learning, an operational forecast, or a random forest implementation.

An anomaly screening rule compares a fresh observation with 24 preceding valid
hours: excess must exceed both 50% of the prior median and three robust standard
deviations (1.4826 times MAD). A candidate additionally requires an anomaly at a
separate station, for the same pollutant and unit, within one hour. These gates
are transparent screening choices, not health or legal thresholds. Concurrent
stations are supporting context and may share an upstream provider. Every
candidate requests human review, has unknown locality geometry, and has no cause
attribution or enforcement permission. Absence of candidates is not evidence
that every locality is safe.

Mobile stations and stations whose mobility is unknown cannot create or
corroborate locality candidates, and current station forecasts are withheld for
them. Their metadata remains visible with `location_precision` set to
`mobile_initial_point` or `mobility_unknown_point`; only explicitly stationary
locations receive `station_point`. OpenAQ mobile-location metadata coordinates
can describe the first position, not the current position. Archive CSVs do not
confirm station mobility, so this remains unknown in archive mode.

## References and checks

- [OpenAQ location metadata](https://docs.openaq.org/resources/locations)
- [OpenAQ latest endpoint semantics](https://docs.openaq.org/resources/latest)
- [OpenAQ hourly measurements](https://docs.openaq.org/api/operations/sensor_hourly_measurements_get_v3_sensors__sensors_id__hours_get)
- [OpenAQ archive structure and publication delay](https://docs.openaq.org/aws/about)
- [Open-Meteo weather model API](https://open-meteo.com/en/docs)

Offline checks: `python -m unittest tests.test_monitoring_v2 -v`. Fixtures cover
missing/stale/future/flagged data, units, conflicting duplicates, no radius,
chronological leakage, corroboration, archive provenance, key scoping,
pagination limits and upstream failures. Tests do not access real credentials.
