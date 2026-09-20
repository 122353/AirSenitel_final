import json
import os
import uuid
from datetime import datetime
from src.api.schemas import CaseActionInput

AUDIT_FILE = "d:/AirSentinel/data/processed/case_action_audit.jsonl"

def _ensure_dir():
    os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)

def overlay_review_state(cases: list[dict]) -> list[dict]:
    _ensure_dir()
    if not os.path.exists(AUDIT_FILE):
        return cases
    
    latest_states = {}
    with open(AUDIT_FILE, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            action = json.loads(line)
            latest_states[action['case_id']] = action['outcome_status']
            
    for case in cases:
        case_id = case.get('case_id')
        if case_id in latest_states:
            case['review_state'] = latest_states[case_id]
            
    return cases

def read_case_actions(case_id: str) -> list[dict]:
    _ensure_dir()
    if not os.path.exists(AUDIT_FILE):
        return []
        
    actions = []
    with open(AUDIT_FILE, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            action = json.loads(line)
            if action['case_id'] == case_id:
                actions.append(action)
    return actions

def save_case_action(case_id: str, action: CaseActionInput) -> dict:
    _ensure_dir()
    ts = datetime.utcnow().isoformat() + "Z"
    record = {
        "action_id": str(uuid.uuid4()),
        "case_id": case_id,
        "timestamp": ts,
        "timestamp_utc": ts,
        "actor_role": action.actor_role,
        "action_type": action.action_type,
        "outcome_status": action.outcome_status,
        "review_note": action.review_note
    }
    
    with open(AUDIT_FILE, 'a') as f:
        f.write(json.dumps(record) + '\n')
        
    return record
