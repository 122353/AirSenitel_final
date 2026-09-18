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
        "report_id": str(uuid.uuid4()),
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
