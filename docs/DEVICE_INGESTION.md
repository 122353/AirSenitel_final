# Private device ingestion and inspection screening

This interface is an authority-operated pilot ingestion path. It does not discover
or connect all Delhi sensors. No unattended hardware gateway, machine credential,
government partnership or independently verified calibration is implied.

## Service contracts

The API must protect every registration, ingestion, device listing, observation
listing and inspection-screening route with `require_authority`. A valid Clerk
session token is used for these operations. Never embed provider secrets,
database URLs or long-lived device credentials in browser code or firmware.
The current path supports an authenticated operator or controlled backend adapter
submitting readings; a future unattended gateway needs a separate scoped and
revocable machine-authentication design.

After configuring the durable store, explicitly call
`devices_v2.initialize_devices()`. This adds `airv2_devices` and
`airv2_device_observations`; requests do not automatically create tables.
The service uses the same production PostgreSQL/local-only SQLite rules as
[the v2 security model](SECURITY_V2.md).

| Function | Input and result |
| --- | --- |
| `register_device(payload, actor)` | Validated registration JSON and authenticated identity; returns a device |
| `list_devices(limit=200)` | Private bounded registration list; maximum 1,000 |
| `ingest_observations(device_id, payload, actor)` | A `samples` array of 1–100 records; returns accepted count and immutable observation IDs |
| `recent_observations(hours=24, limit=2000)` | Private snapshot with `devices`, `observations`, query window and `truncated` |
| `micro_candidates(data, now=None)` | Pure analysis of the private snapshot; returns `candidates`, `coverage`, `reasons`, `methodology` |

A screening route can call
`micro_candidates(recent_observations(hours=2, limit=10000))`. Keep its response
private because it references precise device locations and registration IDs.

## Registration fields

Required fields are `physical_device_id`, `name`, `latitude`, `longitude`,
`location_accuracy_m`, `environment`, `calibration_reference`,
`calibration_valid_until`, and `supported_channels`. The only optional field is
`representativeness_radius_m`.

Coordinates must fall inside the configured Delhi/NCR discovery box: longitude
76.8–77.6 and latitude 28.3–29.0. This box is a pilot scope, not an administrative
boundary. Location accuracy must be a finite positive value no greater than
1,000 metres. The environment must explicitly be `indoor` or `outdoor`.

`physical_device_id` should be a stable manufacturer-and-serial identifier known
to the operator, up to 128 characters. The service normalizes Unicode, case and
whitespace and stores only a unique SHA-256 fingerprint. It does not retain or
return the raw identifier. Do not put passwords, API keys, resident information
or other secrets in this field. Hash uniqueness prevents accidentally registering
the same supplied identity twice; it cannot prove that two different strings
represent physically independent instruments. The database records the
authenticated registering actor. Fingerprints are not a substitute for operator
verification of hardware identity.

Calibration requires an operator-supplied reference and a timezone-aware future
valid-until timestamp. Both are recorded as an operator attestation, not a
calibration verified by AirSentinel. The service cannot verify a certificate from
its reference text alone. Registration should therefore follow a human check of
the instrument, installation and calibration record.

Supported channels are objects containing only `pollutant` and `unit`. Parameters
are `pm25`, `pm10`, `no2`, `so2`, `o3`, and `co`. Use `ug/m3`; CO may instead use
`mg/m3`. Register one unit per pollutant and up to six channels. Units are retained
as submitted; ingestion does not silently convert units.

Representativeness radius defaults to `null` and remains unknown. An explicitly
provided positive radius is labeled operator-attested and is not used to infer
area-wide readings. Location accuracy and representativeness are different
quantities. Neither a registration nor a 250 m inspection grid establishes the
physical range of an instrument.

## Observation ingestion

Each sample requires only `pollutant`, `value`, `unit`, and `observed_at`. A batch
contains no raw serial, actor identity or credential fields. The authenticated
route supplies the actor identity. The pollutant and unit must match a registered
channel. Values must be finite, non-negative numbers; booleans are rejected.
Supported ingestion limits are 5,000 ug/m3 for particulate matter, 100,000 ug/m3
for other channels in those units, and 100 mg/m3 for CO. These are input bounds,
not claims of instrument accuracy or safe exposure.

Timestamps require a timezone. Samples older than seven days or more than five
minutes in the future are rejected. Future-dated samples within clock tolerance
are stored but cannot enter screening until their observation time has arrived.
The whole batch commits atomically. A repeated device/pollutant/timestamp is a
409 conflict, including a duplicate already present with a different value.
Existing observations are never overwritten, and a conflicting batch adds none
of its otherwise-new samples.

Every observation retains the ingestion actor and an immutable snapshot of the
device's coordinates, environment, accuracy, calibration attestation, channel
configuration and identity fingerprint. There is no registration-edit API in
this first pilot; renewal or relocation needs a separately audited update
workflow before it is offered to operators.

Read queries are bounded to at most 72 hours, 10,000 observations and 1,000 device
registrations. Truncated data is clearly flagged, and screening refuses to infer
candidates from it. Query limits are not a database retention policy: retention,
operator-approved deletion and provider backup/WAL retention must be configured
for a real deployment. No unattended retention deletion runs in these services.

## Inspection screening rules

The 250 m grid is an approximate local planning grid. It is not measured spatial
resolution, microscopic source detection, a pollution contour or sensor coverage.
No interpolation is performed between instruments. The grid uses a fixed local
longitude scale, so its size is an approximation across the pilot box.

A device can contribute only when all of the following hold:

- It has an outdoor PM2.5 channel in ug/m3, a unique operator-attested physical
  identifier, an unexpired calibration attestation and location accuracy at most
  50 m.
- Its observations are less than two hours old and agree with its immutable
  registration snapshot.
- It has at least three unique observation timestamps spanning at least 20
  minutes. Conflicting duplicate timestamps or inconsistent metadata exclude the
  instrument.

Within each cell, the newest eligible observation anchors a comparison episode.
Each participating cell device must have sustained samples within the preceding
60 minutes and a final sample within 20 minutes of that anchor. At least two
distinct devices must individually have median PM2.5 greater than 75 ug/m3, and
the median across all participating device medians must also exceed 75 ug/m3.
Normal devices in the same cell are retained in that aggregate. Medians are
computed per device so a device transmitting more frequently cannot dominate.

At least two additional devices outside the cell, within 3 km of its centre,
must provide a contemporaneous background comparison. Each also needs at least
three timestamps spanning 20 minutes within the interval from 40 minutes before
to 20 minutes after the anchor, with its last sample within 20 minutes of the
anchor. Every qualifying nearby background device contributes to the background
median. The cell median must exceed that background by at least 20 ug/m3 and be
at least 1.5 times the background median.

All these thresholds are research screening heuristics. They are not statutory
AQI thresholds, validated health cutoffs or validated anomaly performance.
Output confidence is always `screening_only`; cause is always `unverified`.
Recommendations ask an operator to check calibration and physical independence,
inspect with a reference instrument, review weather/activity and instrument
faults, and record a human decision. They do not identify a polluter or authorize
enforcement. Missing, stale, sparse, indoor, poorly located, contradictory or
truncated evidence produces reasons and no candidate.

## Verification

Run `python -m unittest tests.test_devices_v2 tests.test_security_v2 -v`.
Tests use temporary local SQLite databases and synthetic measurements. They cover
registration deduplication and raw-identifier minimization, bounds and units,
time validation, batch rollback and concurrent duplicates, immutable snapshots,
query caps, a qualified synthetic inspection pattern, missing/background/stale
evidence, physical-identity duplication, indoor/uncalibrated/imprecise devices,
normal in-cell readings, and unverified output labels. Passing these tests does
not validate hardware calibration or real-world detection performance.
