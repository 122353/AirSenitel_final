# AirSentinel release manifest

## Primary handoff

- `AirSentinel_Submission_Package.zip` — curated secret-free review package.
- `docs/RELEASE_PACKAGE_README.md` — scope, run commands, exclusions and external owner steps.
- `deploy/build-submission-package.ps1` — deterministic allowlisted archive builder.

## Judge-facing artifacts

- `README.md`
- `docs/FINAL_PROJECT_REPORT.md`
- `docs/AirSentinel_Final_Project_Report.docx`
- `docs/AirSentinel_Final_Project_Report.pdf`
- `docs/AirSentinel_Hackathon_Pitch_Deck.pptx`
- `docs/FLOWCHARTS.md` and four non-federated workflow images
- `docs/DEMO_VIDEO_SCRIPT.md` and `docs/DEMO_RUNBOOK.md`
- `docs/SHORT_PROJECT_DESCRIPTION.md`
- `docs/SUBMISSION_CHECKLIST.md`

## Working applications and tests

- `app.py` — reviewed aggregate public dashboard.
- `citizen_app.py` — consented pending-review report interface.
- `authority_app.py` — local review demonstration; production mode is view-only.
- `src/api/main.py` — private authenticated API boundary.
- `tests/` — 38 offline access, provenance, ingestion and cloud-adapter safety tests.

## Included reviewed evidence

- Application/API aggregate CSVs and historical prototype case/metric tables.
- `data/reference/approved_data_source_registry.csv`
- `data/reference/brics_observation_contract.csv`
- `data/reference/monitoring_areas.csv`
- `data/reference/pollutant_registry.csv`
- Data-source, fallback, locality and model-card documentation.

## Deployment and security

- `Dockerfile` for the private API/private authority paths.
- `Dockerfile.public` plus the temporary public allowlist deployment path.
- Pinned `requirements.txt`, `requirements-google-cloud.txt` and `requirements-dev.txt`.
- `deploy/` bootstrap, BigQuery, Firebase, Cloud Run, verification and packaging scripts.
- Deny-by-default `firestore.rules` and `storage.rules`.

## Intentionally excluded from the ZIP

- `.env`, API keys, service-account files and other credentials.
- `.git`, virtual environments, `node_modules` and cache directories.
- Raw source downloads, citizen report JSONL and authority audit JSONL.
- Trained `.joblib` binaries and large model feature tables.
- Render/inspection output and document/deck builder dependencies.
- Retired experimental federated code, registry, metrics and diagram.

The excluded materials are unnecessary for judge review and could create disclosure, size or narrative risk. The archive still runs the three local applications, private API and full test suite against the packaged reviewed example/aggregate data.
