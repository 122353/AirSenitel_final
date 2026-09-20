"""Read-only integration check. Reuses the dev runner's private config loader."""
import argparse
import asyncio
from collections import Counter
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.dev_v2 import configuration

parser = argparse.ArgumentParser()
parser.add_argument('--env-file', action='append', default=[])
parser.add_argument('--source-zip')
parser.add_argument('--store', default='sqlite')
parser.add_argument('--station-id', type=int)
parser.add_argument('--pollutant', default='pm25')
args = parser.parse_args()
os.environ.update(configuration(args))
from src.services.monitoring_v2 import build_snapshot

async def main():
    result = await build_snapshot(args.station_id, args.pollutant, 'live')
    history = result.get('history', {})
    forecast = result.get('forecast', {})
    for horizon in forecast.get('evaluation', {}).get('horizons', []):
        horizon.pop('test_predictions', None)
    print(json.dumps({
        'status': result.get('status'), 'message': result.get('message'),
        'station_count': len(result.get('stations', [])), 'selected_station_id': result.get('selected_station_id'),
        'coverage': result.get('coverage'), 'history_status': history.get('status'),
        'history_count': len(history.get('points', [])), 'unit': history.get('unit'),
        'quality_counts': dict(Counter(p.get('quality', {}).get('status') for p in history.get('points', []))),
        'quality_reasons': dict(Counter(r for p in history.get('points', []) for r in p.get('quality', {}).get('reasons', []))),
        'first_time': (history.get('points') or [{}])[0].get('observed_at'),
        'latest_time': (history.get('points') or [{}])[-1].get('observed_at'),
        'forecast': forecast, 'candidate_status': result.get('candidate_status'),
        'source_statuses': result.get('sources'), 'weather_status': result.get('weather', {}).get('status')
    }, indent=2, ensure_ascii=True))

asyncio.run(main())
