import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

export const POLLUTANTS = [
  { id: 'pm25', label: 'PM₂.₅', name: 'Fine particles' },
  { id: 'pm10', label: 'PM₁₀', name: 'Coarse particles' },
  { id: 'no2', label: 'NO₂', name: 'Nitrogen dioxide' },
  { id: 'o3', label: 'O₃', name: 'Ozone' },
  { id: 'so2', label: 'SO₂', name: 'Sulphur dioxide' },
  { id: 'co', label: 'CO', name: 'Carbon monoxide' },
];
export const pollutantLabel = id => POLLUTANTS.find(p => p.id === id)?.label || id;
export const usableMeasurement = measurement => Boolean(measurement && Number.isFinite(measurement.value) && measurement.value >= 0 && measurement.quality?.status !== 'rejected' && Number.isFinite(new Date(measurement.observed_at).getTime()));
export const latestMeasurement = (station, pollutant) => station?.measurements?.filter(m => m.pollutant === pollutant && usableMeasurement(m)).sort((a, b) => new Date(b.observed_at) - new Date(a.observed_at))[0];
export const freshMeasurement = (measurement, mode = 'live', error = '') => {
  if (!usableMeasurement(measurement) || mode !== 'live' || error || measurement.fresh !== true) return false;
  const age = Date.now() - new Date(measurement.observed_at).getTime();
  return age >= 0 && age <= 3 * 60 * 60 * 1000;
};
export const valueLabel = value => typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 }).format(value) : '—';
export const dateLabel = value => value && Number.isFinite(new Date(value).getTime()) ? new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }).format(new Date(value)) + ' IST' : 'Timestamp unavailable';
export const ageLabel = value => {
  if (!value || !Number.isFinite(new Date(value).getTime())) return 'No timestamp';
  const mins = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  if (mins < 1440) return `${Math.floor(mins / 60)}h ${mins % 60}m ago`;
  return `${Math.floor(mins / 1440)}d ago`;
};
const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
export async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    throw new Error(typeof detail === 'string' ? detail : payload?.message || `Request could not be completed (${response.status}).`);
  }
  if (!payload || typeof payload !== 'object') throw new Error('The data service returned an unreadable response.');
  return payload;
}

const MonitoringContext = createContext(null);
export function MonitoringProvider({ children }) {
  const [stationId, setStationId] = useState('');
  const [pollutant, setPollutant] = useState('pm25');
  const [mode, setMode] = useState('live');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [receivedAt, setReceivedAt] = useState(null);
  const [tick, setTick] = useState(0);
  const requestRef = useRef(0);
  const refresh = useCallback(() => setTick(t => t + 1), []);
  useEffect(() => {
    const interval = setInterval(refresh, 60000);
    return () => clearInterval(interval);
  }, [refresh]);
  useEffect(() => {
    const controller = new AbortController();
    const id = ++requestRef.current;
    let timedOut = false;
    const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, 55000);
    setRefreshing(true);
    const query = new URLSearchParams({ pollutant, mode });
    if (stationId) query.set('station_id', stationId);
    api(`/api/v2/monitoring?${query}`, { signal: controller.signal })
      .then(result => {
        if (id !== requestRef.current) return;
        setData(result);
        setError('');
        setReceivedAt(new Date().toISOString());
      })
      .catch(err => {
        if (id === requestRef.current && (!controller.signal.aborted || timedOut)) setError(timedOut ? 'The data service took too long to respond. Try refreshing.' : err.message);
      })
      .finally(() => { clearTimeout(timeout); if (id === requestRef.current) { setLoading(false); setRefreshing(false); } });
    return () => { controller.abort(); clearTimeout(timeout); };
  }, [stationId, pollutant, mode, tick]);
  const changeStation = id => { setData(null); setLoading(true); setStationId(String(id)); };
  const changePollutant = id => { setData(null); setLoading(true); setPollutant(id); };
  const changeMode = value => { setData(null); setLoading(true); setMode(value); };
  const stations = Array.isArray(data?.stations) ? data.stations : [];
  const selectedStation = stations.find(s => String(s.id) === String(data?.selected_station_id || stationId)) || stations[0];
  const measurement = latestMeasurement(selectedStation, pollutant);
  return <MonitoringContext.Provider value={{ data, stations, selectedStation, measurement, stationId, setStationId: changeStation, pollutant, setPollutant: changePollutant, mode, setMode: changeMode, loading, refreshing, error, receivedAt, refresh }}>{children}</MonitoringContext.Provider>;
}
export const useMonitoring = () => useContext(MonitoringContext);
