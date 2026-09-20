# V2 rebuild and release runbook

## Scope

The rebuild starts from GitHub commit `03b2f22bd7b34bec248673b5dd2f2ddcd748ffe3` on a separate `codex/authority-live-evidence` branch. The September 18 complete ZIP remains unchanged. No old Git history is rewritten.

The earlier dashboard displayed generated values and its API exposed review actions without server-side authorization. Local development uses `backend/main.py`; the root Vercel service uses `api_service.py`, mounting the evidence API at `/api` because current Vercel Services preserve the original public path. The top-level web rewrite selects `/index.html` for every non-API route without changing the browser-visible path, so direct SPA routes such as `/authority` work. Both APIs load `src/api/operational.py`. The compatibility module `src/api/main.py` also delegates to that protected API. Root `pyproject.toml` defines the lightweight v2 dependencies; `requirements.txt` remains the independent legacy research dependency set.

## Data and detection

- `/api/v2/monitoring` discovers OpenAQ metadata in a stated Delhi/NCR bounding box, then queries the selected station and two nearby comparison points within bounded request/time limits. The metadata count is not the count of online sensors, complete Delhi coverage or an administrative boundary.
- Every measurement retains its pollutant, original unit, timestamp, provider, licence and quality. Unknown quality stays provisional. Rejected and stale values cannot silently qualify as fresh evidence.
- A lag-based ridge regressor competes against persistence using earlier validation. Separate calibration and final holdout avoid choosing a model on its test score. Scoring origins are purged at split boundaries. Short histories, missing lags and stale inputs produce explicit limitations; forecasts are research outputs.
- Weather and satellite imagery are context, not street-level ground measurements or source attribution. Delayed archive readings are labelled historical, not live.
- Station positions have no invented 5 km representativeness radius. Changing a search radius cannot create spatial evidence.
- Private local-device ingestion uses registered operator-attested hardware identities, immutable timestamped measurements and explicit units. Local PM2.5 screening requires precise outdoor locations, sustained fresh samples, multi-device agreement and contemporaneous nearby background data.
- A 250 m inspection cell is an operational grouping, not microscopic sensing or validated measurement resolution. Physical independence and calibration still require verification; no qualified evidence means no candidate.

## People and privacy

Citizen reporting is separate from the public monitor. Verified sign-in and consent are required. Optional photos are decoded, size-limited and re-encoded without EXIF. Reports are private; receipt-based withdrawal removes content/photo/location/reading and redacts identity, retaining a minimal audit tombstone. Backup retention requires an operator policy.

Every authority route requires a signed Clerk session, active session/user verification, a verified primary email and a server-only allowlist match. Case actions use optimistic versions and transactional audit writes. No browser header or editable user metadata grants a government role.

Model exchange supports validated metadata, checksums, quarantine, human approval and export. It is **not deployed federated learning**, executable model sharing, a BRICS partnership or international resource dispatch. No external authority email/SMS, official complaint filing or automatic enforcement is connected.

## Release checklist

The two previously working Vercel projects were paused at the user's request. The third final-repository project had no working production deployment. Keep production paused until explicitly approved.

1. Use one canonical project, the repository root and the Vercel Services framework configuration. Do not deploy the React folder as a standalone Python project.
2. Supply server-only `OPENAQ_API_KEY`, `CLERK_SECRET_KEY`, `AUTHORITY_ALLOWED_EMAILS`, `DATABASE_URL`, `REPORT_HASH_SECRET`, plus `AIRSENTINEL_STORE=postgres`. Public production requires a production Clerk instance.
3. Set `CLERK_AUTHORIZED_PARTIES` to exact HTTPS origins, without wildcards or localhost. Set the matching `VITE_CLERK_PUBLISHABLE_KEY`.
4. Explicitly initialise only the additive `airv2_*` tables using `case_store_v2.initialize_store()` and `devices_v2.initialize_devices()` against the intended database. Do not reset legacy tables or deploy SQLite on Vercel.
5. Keep deployment protection enabled for review. Verify deep links, API routing, real upstream data, signed-out 401s, a denied non-reviewer account and a real approved reviewer session.
6. Inspect packaged files and browser bundles for private credentials. Never upload `.env`, local databases, raw citizen evidence, dependency folders or archived executables to GitHub.
7. Test a clearly labelled temporary report through private review and withdrawal, without external dispatch.
8. Resume/promote only after user approval; then check runtime errors and configure monitoring, data retention and distributed quota protection.

The tested local configuration uses a previously approved **development** Clerk integration and explicit local SQLite. This is not a claim that production identity/database wiring is complete. Registered-device support is an ingestion path, not an automatic connection to every privately owned purifier or government instrument.

## Primary documentation

- [OpenAQ locations](https://docs.openaq.org/resources/locations), [latest observations](https://docs.openaq.org/resources/latest), [delayed archive](https://docs.openaq.org/aws/about)
- [Open-Meteo](https://open-meteo.com/en/docs)
- [NASA GIBS](https://nasa-gibs.github.io/gibs-api-docs/access-basics/)
- [EPA sensor siting](https://www.epa.gov/air-sensor-toolbox/guide-siting-and-installing-air-sensors)
- [Vercel Services](https://vercel.com/docs/services)
