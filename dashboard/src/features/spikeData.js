export function isRecentSpike(value, now = Date.now()) {
  const age = now - new Date(value).getTime();
  return Boolean(value) && Number.isFinite(age) && age >= 0 && age <= 3 * 3600000;
}

export function verificationPayload(event, stationId, notes, consent) {
  const id = Number(stationId);
  if (!Number.isSafeInteger(id) || id <= 0) throw new Error('Select a valid station before requesting verification.');
  return { station_id: id, pollutant: event.pollutant, event_id: event.id, notes: notes.trim(), consent };
}

export function observedChartPoints(history) {
  const accepted = (history?.points || []).filter(p => p.quality?.status === 'valid'
    && p.averaging_period === 'hour' && Number.isFinite(p.value) && p.value >= 0
    && p.unit === history.unit && p.station_id === history.station_id && p.sensor_id === history.sensor_id
    && p.pollutant === history.pollutant && Number.isFinite(new Date(p.observed_at).getTime()))
    .map(p => ({ time: new Date(p.observed_at).getTime(), value: p.value }))
    .sort((a, b) => a.time - b.time).slice(-48);
  return accepted.flatMap((point, i) => i && point.time - accepted[i - 1].time > 90 * 60000
    ? [{ time: accepted[i - 1].time + 60000, value: null }, point] : [point]);
}
