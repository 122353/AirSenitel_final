# Sudden spikes and verification

The public `#/spikes` route and the private operator workspace's **Sudden spikes** tab show measured station rises. They are separate from forecast watches. Both use `GET /api/v2/spikes`, which reuses the monitoring service's source cache and bounded collection budget.

## What is screened

- Only the selected fixed station and the queried peers, for the selected pollutant. The India station directory is not a continuously monitored nationwide alert network.
- A selected-station signal requires 12 contiguous quality-accepted baseline hours, excluding the two most recent hours. Both recent hours must exceed the median baseline plus the largest of 35% of baseline, three scaled median absolute deviations, or the pollutant-specific concentration floor.
- Existing concurrent-station anomaly candidates can also appear. They use their existing screening rules; their excess threshold is converted to an absolute concentration for display.
- Duplicate station/pollutant/observation events are merged. The event ID binds the concentration, baseline, threshold, unit, timestamp and station identity.
- Current signals require a working OpenAQ source, confirmed fixed-station identity, and measurements no more than three hours old. Forecast values and archived observations cannot create a measured-spike request.

The page checks every 60 seconds while mounted, not continuously in the background. Upstream hourly reporting and source latency limit response time. These thresholds are research screens, not calibrated event probabilities, legal AQI limits, proof of a source, or certified emergencies.

## Private verification workflow

1. A user selects **Request verification** on a currently eligible signal.
2. Sign-in is required. The user supplies optional notes and explicit storage consent.
3. `POST /api/v2/spikes/verification` authenticates first, validates input, and recomputes the event against the current source snapshot. Mismatched, stale, revised or forecast-only evidence is rejected with HTTP409.
4. Trusted station evidence is stored as a private `citizen_report`, headed `SUDDEN SPIKE — VERIFICATION REQUEST`, using the existing case store and rate limits. No new schema or authorization bypass is introduced.
5. The returned private receipt supports the existing **Community reports → Withdraw a previous report** flow. Treat the receipt as a withdrawal credential.
6. Approved operators find the request under **Case review**, record their checks and use the existing audited review states. Closing a review is not automatic verification or source certification.

No government notification, email, SMS, emergency dispatch, or public declaration of verification is sent. NASA remains explicitly unavailable unless configured separately.

## Verification

Backend regression tests: `tests/test_spikes_v2.py` (synthetic, offline fixtures only).

Frontend contract/quality tests: from `dashboard`, run `node --test src/features/spikeData.test.js`.

Build: from `dashboard`, run `npm run build`.

Check the live page for source timestamps and coverage. Do not create false production cases to exercise the review flow. Backend tests cover creation, private review access, invalid evidence rejection and receipt withdrawal with an isolated temporary database; this does not substitute for a signed-in production user acceptance test.
