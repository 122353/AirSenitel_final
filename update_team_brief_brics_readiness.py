"""Append BRICS Track 2 readiness notes to the team brief once."""

from pathlib import Path

from docx import Document


DOCUMENT_PATH = Path(
    r"C:\Users\Rupesh\Documents\Codex\2026-08-25\referenced-chatgpt-conversation-this-is-an"
) / "AirSentinel_Team_Workflow_and_Plan.docx"
HEADING = "BRICS Track 2 readiness and phased delivery"


def add_bullet(document: Document, text: str) -> None:
    document.add_paragraph(text, style="List Bullet")


document = Document(DOCUMENT_PATH)
if any(paragraph.text == HEADING for paragraph in document.paragraphs):
    print("BRICS readiness section already exists; no change made.")
else:
    document.add_page_break()
    document.add_heading(HEADING, level=1)
    document.add_paragraph(
        "AirSentinel aligns with Track 2 — Clean Air & Climate Resilience by "
        "demonstrating an India-first, local-to-national early-warning pilot and "
        "a later simulated federated BRICS model-sharing proof. It is not connected "
        "to BRICS government systems and must never claim cross-border deployment."
    )

    document.add_heading("Evidence-based interoperability need", level=2)
    document.add_paragraph(
        "Public BRICS environment statements call for greater uniformity in air-quality "
        "data generation, quality control, quality assurance and monitoring networks. "
        "The project treats these as collaboration priorities, not as verified security "
        "weaknesses. The team must never scan, test or try to access a government system."
    )

    document.add_heading("AirSentinel safeguards", level=2)
    add_bullet(document, "Canonical record contract: pollutant, unit, UTC timestamp, locality resolution, source, quality flag and evidence tier before modelling.")
    add_bullet(document, "No invented AQI in uncovered localities; show coverage, freshness and confidence instead.")
    add_bullet(document, "Residual anomaly case: unexpected spike — cause unverified, with nearby-station and context checks before human review.")
    add_bullet(document, "Data sovereignty: raw citizen, home-device and station records stay local; only approved model updates and aggregate metrics may be shared in the simulated federation.")
    add_bullet(document, "Trustworthy authority workflow: deduplicated case, evidence snapshot, owner, due time, review status and recorded outcome.")
    add_bullet(document, "Human safeguards: no automated enforcement, no source attribution from a single signal, and privacy-safe community reporting.")

    document.add_heading("Re-divided delivery phases", level=2)
    add_bullet(document, "Phases 0–3 complete: environment, eight-city visibility, Chennai baseline validation and transparent sustainability risk guidance.")
    add_bullet(document, "Phase 2.5: execute direct 1-, 3- and 4-hour forecast comparison with chronological validation and uncertainty.")
    add_bullet(document, "Phase 2.6: execute multi-scale, multi-pollutant data discovery and coverage validation for city and locality pilots.")
    add_bullet(document, "Phase 3.5: unexpected-spike and hidden-hotspot anomaly cases with corroboration and human review.")
    add_bullet(document, "Phase 4: public/authority dashboard, case queue, audit trail, privacy controls and pilot metrics.")
    add_bullet(document, "Phase 4A: canonical BRICS observation contract, source validation and simulated node registry.")
    add_bullet(document, "Phases 5–8: community evidence, advanced-model comparison only after data gates pass, federated simulation, Google Cloud deployment and submission package.")

    document.save(DOCUMENT_PATH)
    print(f"Updated: {DOCUMENT_PATH}")
