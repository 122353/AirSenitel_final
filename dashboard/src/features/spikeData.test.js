import test from 'node:test';
import assert from 'node:assert/strict';
import { isRecentSpike, observedChartPoints, verificationPayload } from './spikeData.js';

test('verification payload obeys strict server integer identity and sends no client reading', () => {
  assert.deepEqual(verificationPayload({ id: 'spike-test', pollutant: 'pm25', value: 999 }, '17', ' note ', true),
    { station_id: 17, pollutant: 'pm25', event_id: 'spike-test', notes: 'note', consent: true });
  for (const id of ['', null, -1, 'bad', 1.5]) assert.throws(() => verificationPayload({}, id, '', true));
});
test('freshness is measured from observation, rejects future and stale events', () => {
  const now = Date.parse('2026-09-21T12:00:00Z');
  assert.equal(isRecentSpike('2026-09-21T10:00:00Z', now), true);
  for (const stamp of ['2026-09-21T08:59:00Z', '2026-09-21T12:01:00Z', null, 'bad']) assert.equal(isRecentSpike(stamp, now), false);
});
test('chart excludes provisional, forecast, other instruments and units; preserves missing-hour gaps', () => {
  const point = { value: 20, unit: 'µg/m³', station_id: 17, sensor_id: 1700, pollutant: 'pm25', averaging_period: 'hour', quality: { status: 'valid' }, observed_at: '2026-09-21T08:00:00Z' };
  const history = { unit: 'µg/m³', station_id: 17, sensor_id: 1700, pollutant: 'pm25', points: [point,
    { ...point, observed_at: '2026-09-21T11:00:00Z', value: 45 },
    { ...point, quality: { status: 'provisional' } }, { ...point, value: null },
    { ...point, station_id: 18 }, { ...point, sensor_id: 1701 }, { ...point, pollutant: 'co' },
    { ...point, unit: 'mg/m³' }, { ...point, averaging_period: 'instant' }] };
  const points = observedChartPoints(history);
  assert.equal(points.length, 3);
  assert.deepEqual(points.map(p => p.value), [20, null, 45]);
});
