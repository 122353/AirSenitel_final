# Deployment status

## Ready and locally verified

- Public aggregate dashboard source and a separate allowlisted public image path.
- Citizen interface and privacy-minimised text/photo/voice contracts.
- Private FastAPI with fail-closed production authentication.
- Authority interface whose production Cloud Run mode is view-only; writes must use the authorised private API and durable audit storage.
- Pinned containers, deny-by-default Firebase rules, BigQuery/Firebase/Gemini/Maps/Earth Engine/language adapters and readiness checks.
- Cloud Run bootstrap/deployment/verification scripts.
- Thirty-eight passing offline tests and independently verified submission ZIP.

## Feature-gated Google path

- Gemini explanation and in-memory photo description are disabled until a reviewed Secret Manager value and audit policy exist.
- Firebase citizen storage is disabled until Auth, rules, retention and abuse-response ownership are configured.
- BigQuery is disabled until dataset region, IAM, retention/default expiry and cost policy are approved.
- Maps and Earth Engine are contextual only and require a restricted key/registered project.
- Translation, Speech-to-Text and Text-to-Speech are optional accessibility paths and remain disabled until consent/language QA is complete.
- Vertex AI is only an optional host for a promoted conventional model; no deep or federated model is claimed.
- No Cloud Function is deployed because an approved event source, idempotency contract and operational owner were not supplied.

## Account-bound execution still required

1. Create/select the team-owned GCP project, billing account, region and retention policy.
2. Authenticate `gcloud`, approve least-privilege IAM and run `deploy/gcp-bootstrap.ps1`.
3. Add reviewed secrets through Secret Manager; configure Firebase Auth/rules and governed BigQuery tables.
4. Deploy the private API, private authority view and public allowlisted dashboard.
5. Run negative/positive identity tests, persistence tests and verify every generated URL.
6. Insert only tested URLs into the deck, GitHub README and submission form.

No live deployment, public URL, government approval or external partnership is claimed in the repository.
