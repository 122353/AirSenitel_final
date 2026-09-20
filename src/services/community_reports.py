import json
import os
import uuid
from datetime import datetime
from src.api.schemas import CommunityReportInput

REPORTS_FILE = "d:/AirSentinel/data/processed/community_reports.jsonl"

def _ensure_dir():
    os.makedirs(os.path.dirname(REPORTS_FILE), exist_ok=True)

def save_local_report(report: CommunityReportInput) -> dict:
    if not report.consent_to_store:
        raise ValueError("Cannot store report without user consent")
    if not report.report_text.strip():
        raise ValueError("Report text cannot be empty")
        
    _ensure_dir()
    
    record = {
        "report_id": f"REP-2026-{uuid.uuid4().hex[:6].upper()}",
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "locality_id": report.locality_id,
        "report_text": report.report_text,
        "language_code": report.language_code,
        "source_type": report.source_type,
        "consent_to_store": report.consent_to_store,
        "coarse_location_cell": report.coarse_location_cell
    }
    
    with open(REPORTS_FILE, 'a') as f:
        f.write(json.dumps(record) + '\n')
        
    return record

def list_local_reports(limit: int = 50) -> list[dict]:
    if not os.path.exists(REPORTS_FILE):
        return []
    reports = []
    with open(REPORTS_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    reports.append(json.loads(line))
                except Exception:
                    continue
    return reports[-limit:][::-1]
