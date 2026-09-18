# AirSentinel deployment guide

The complete command-by-command guide is in `deploy/README_GOOGLE_CLOUD.md`.

## Intended service boundary

- **Public dashboard:** reviewed aggregate artifacts only; may be unauthenticated.
- **FastAPI backend:** private Cloud Run service; citizen/report endpoints require verified identity in production.
- **Authority portal:** private Cloud Run view; production Streamlit is read-only and any write must use the authenticated private API or an approved portal with durable audit storage.

## Before running deployment

1. Team owns a Google Cloud project with billing and a chosen India-appropriate region/data-retention decision.
2. `gcloud` is installed and authenticated by an authorised owner.
3. APIs and least-privilege service accounts are created through the supplied scripts.
4. Secrets are entered directly into Secret Manager, never this repository.
5. Firebase Auth, Firestore/Storage rules, retention, moderation and deletion processes are reviewed.
6. Public/authority access decisions are approved and tested with separate identities.

## Important truth boundary

This repository contains deployable code and scripts, but no GCP project, billing account, credentials or public URL is available in the local environment. Therefore it does not claim a real deployment. After the team runs the scripts, save the verified URLs in `docs/DEPLOYMENT_STATUS.md` and retest the complete flow.
