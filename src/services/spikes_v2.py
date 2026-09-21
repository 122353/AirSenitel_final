"""Measured station-rise feed and server-bound human-verification evidence.

This is a view of the bounded monitoring sample, not a streaming national alert
network. Forecasts, regional model estimates and delayed archive observations
cannot enter the event list. Verification is a private review request, never an
automatic confirmation of a pollution source or an external emergency dispatch.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math

from .forecast_v2 import iso, parse_time
from .station_warning_v2 import screen_station


def _number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)


def _fresh(value, now):
    stamp = parse_time(value)
    return stamp is not None and timedelta(0) <= now - stamp <= timedelta(hours=3)


def _event(station, evidence, *, pollutant, now, basis, threshold):
    """Normalize only a currently qualified, fixed-station measured event."""
    stamp = parse_time(evidence.get('observed_at'))
    if (not station or station.get('is_mobile') is not False
            or evidence.get('station_id') != station.get('id')
            or evidence.get('pollutant') != pollutant
            or not _fresh(stamp, now)
            or not all(_number(value) for value in (evidence.get('value'), evidence.get('baseline'), threshold))
            or evidence['value'] <= threshold
            or not isinstance(evidence.get('unit'), str) or not evidence['unit'].strip()):
        return None
    event = {
        'station_id': station['id'], 'name': station.get('name'),
        'pollutant': pollutant, 'unit': evidence['unit'],
        'value': evidence['value'], 'baseline': evidence['baseline'],
        'threshold': threshold, 'observed_at': iso(stamp),
        'latitude': station.get('latitude'), 'longitude': station.get('longitude'),
        'verification_status': 'unverified', 'basis': basis,
        'source': 'OpenAQ v3 hourly station observations',
        'source_url': f"https://api.openaq.org/v3/locations/{station['id']}",
        'evidence_class': 'ground_station_observation',
        'official_aqi': False, 'source_attribution': None,
        'enforcement_allowed': False, 'representativeness_radius_km': None,
        'corroboration': [],
        'message': 'A measured station rise requires human verification. It does not identify a local pollution source or certify an emergency.',
    }
    # Binding the ID to the actual evidence also rejects a revised source value
    # submitted from an older browser view, not merely a different timestamp.
    identity = {key: event[key] for key in ('station_id', 'pollutant', 'unit', 'value', 'baseline', 'threshold', 'observed_at')}
    event['id'] = 'spike-' + hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return event


def spike_feed(snapshot: dict, *, now: datetime | None = None) -> dict:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stations = snapshot.get('stations') or []
    indexed = {s.get('id'): s for s in stations}
    selected = indexed.get(snapshot.get('selected_station_id'))
    pollutant = snapshot.get('selected_pollutant')
    warning = screen_station(snapshot, now=now)
    sources = snapshot.get('sources') or []
    live_ground = (snapshot.get('requested_mode') == 'live'
                   and snapshot.get('status') in {'live', 'partial'}
                   and any(s.get('id') == 'openaq_v3' and s.get('live') is True for s in sources))
    by_observation = {}
    if live_ground and warning.get('status') == 'observed_rise':
        event = _event(selected, {**warning, 'value': warning.get('current')},
                       pollutant=pollutant, now=now, basis='two_consecutive_hourly_rises',
                       threshold=warning.get('threshold'))
        if event:
            event['rise_observed_since'] = warning.get('rise_observed_since')
            by_observation[(event['station_id'], pollutant, event['observed_at'])] = event
    for candidate in snapshot.get('candidates') or [] if live_ground else []:
        baseline, excess_gate = candidate.get('baseline'), candidate.get('screening_threshold')
        if not _number(baseline) or not _number(excess_gate) or candidate.get('status') != 'human_review_required':
            continue
        peers = [p for p in candidate.get('corroboration') or []
                 if p.get('station_id') != candidate.get('station_id')
                 and indexed.get(p.get('station_id'), {}).get('is_mobile') is False
                 and _fresh(p.get('observed_at'), now)
                 and _fresh(candidate.get('observed_at'), now)
                 and abs((parse_time(p['observed_at']) - parse_time(candidate['observed_at'])).total_seconds()) <= 3600]
        if not peers:
            continue
        event = _event(indexed.get(candidate.get('station_id')), candidate,
                       pollutant=pollutant, now=now, basis='concurrent_station_anomalies',
                       threshold=baseline + excess_gate)
        if event:
            identity = (event['station_id'], pollutant, event['observed_at'])
            if identity not in by_observation:
                by_observation[identity] = event
            by_observation[identity]['corroboration'] = peers
    events = sorted(by_observation.values(), key=lambda e: (e['observed_at'], e['station_id']), reverse=True)
    return {
        'status': snapshot.get('status', 'unavailable'),
        'detection_status': 'unverified_spikes' if events else 'no_qualified_spike' if live_ground else 'unavailable',
        'generated_at': snapshot.get('generated_at') or iso(now), 'evaluated_at': iso(now),
        'requested_mode': 'live', 'data_mode': 'live' if live_ground else 'unavailable',
        'selected_station_id': snapshot.get('selected_station_id'), 'selected_station': selected,
        'selected_pollutant': pollutant, 'stations': stations,
        'history': snapshot.get('history') or {'points': []},
        'station_warning': warning, 'candidate_status': snapshot.get('candidate_status') or {},
        'events': events, 'sources': sources, 'source': 'OpenAQ v3 hourly station observations',
        'coverage': {**(snapshot.get('coverage') or {}),
                     'screening_scope': 'selected_station_and_queried_peers',
                     'continuously_monitored_all_india': False,
                     'message': 'Only the selected station and queried peers are screened. Discovered station metadata is not live nationwide monitoring.'},
        'refresh_seconds': 60, 'external_notifications': 'not_connected',
        'message': 'Refreshes every minute while open; upstream observations are hourly and may arrive late. An empty list is not an all-clear.',
        'limitations': [
            'Research screening thresholds are not legal air-quality limits or validated emergency thresholds.',
            'All events remain unverified; peer elevations do not prove a shared local source.',
            'No assumed sensing radius, microscopic coverage, or observations for unmonitored areas.',
            'Verification requests enter a private operator queue; no government or emergency dispatch is connected.',
        ],
    }


def verification_report(event: dict, notes: str) -> dict:
    """Store a readable trusted snapshot without relabeling it citizen sensor data."""
    description = '\n'.join([
        'SUDDEN SPIKE — VERIFICATION REQUEST (not a verified event)',
        f"Event: {event['id']}",
        f"Station: {str(event.get('name') or '')[:200]} (OpenAQ {event['station_id']})",
        f"Observation: {event['observed_at']}",
        f"Pollutant: {event['pollutant']}; value: {event['value']} {event['unit']}",
        f"Baseline: {event['baseline']} {event['unit']}; screening threshold: {event['threshold']} {event['unit']}",
        f"Screen basis: {event['basis']}; peer context count: {len(event['corroboration'])}",
        f"Source: {event['source_url']}",
        'Evidence was rechecked by the server on submission. Human review is required; source attribution and locality coverage remain unverified. No external alert has been sent.',
        'Requester note (unverified): ' + notes.strip(),
    ])
    return {'kind': 'citizen_report', 'description': description,
            'latitude': event.get('latitude'), 'longitude': event.get('longitude'),
            'consent_to_store': True}
