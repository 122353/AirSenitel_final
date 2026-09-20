import { useCallback, useEffect, useState } from 'react';
import { Activity, AlertTriangle, ArrowRight, Database, MapPin, Radio, RefreshCw, Search, ShieldCheck, Satellite, Wind } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { EmptyState, PageHeading, StatusBadge } from '../App';
import { api, dateLabel, POLLUTANTS, pollutantLabel, valueLabel } from './data';
import IndiaCoverageMap from './IndiaCoverageMap';

const DEFAULT_PLACE = { label: 'Delhi, Delhi', latitude: 28.6139, longitude: 77.2090 };

export default function NationalIntelligence() {
  const [pollutant, setPollutant] = useState('pm25');
  const [overview, setOverview] = useState(null);
  const [selected, setSelected] = useState(DEFAULT_PLACE);
  const [assessment, setAssessment] = useState(null);
  const [query, setQuery] = useState('');
  const [places, setPlaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState('');

  const loadAssessment = useCallback(async (place, activePollutant = pollutant) => {
    const params = new URLSearchParams({ latitude: place.latitude, longitude: place.longitude, pollutant: activePollutant, label: place.label });
    const result = await api(`/api/v2/india/assessment?${params}`);
    setAssessment(result);
  }, [pollutant]);

  const selectPlace = useCallback(async place => {
    setSelected(place); setPlaces([]); setQuery(place.label); setLoading(true); setError('');
    try { await loadAssessment(place); } catch (err) { setError(err.message); setAssessment(null); } finally { setLoading(false); }
  }, [loadAssessment]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    Promise.all([
      api(`/api/v2/india/overview?pollutant=${pollutant}`, { signal: controller.signal }),
      api(`/api/v2/india/assessment?${new URLSearchParams({ latitude: selected.latitude, longitude: selected.longitude, pollutant, label: selected.label })}`, { signal: controller.signal }),
    ]).then(([national, local]) => { setOverview(national); setAssessment(local); })
      .catch(err => { if (!controller.signal.aborted) setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [pollutant]);

  const search = async event => {
    event.preventDefault();
    if (query.trim().length < 2) return;
    setSearching(true); setError('');
    try { const result = await api(`/api/v2/india/places?${new URLSearchParams({ query: query.trim(), limit: 8 })}`); setPlaces(result.places || []); } catch (err) { setPlaces([]); setError(err.message); } finally { setSearching(false); }
  };

  const model = assessment?.model || {};
  const ground = assessment?.ground || {};
  const spike = model.spike_screen || {};
  const chartData = (model.forecast_series || []).map(point => ({ ...point, label: point.valid_at ? new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }).format(new Date(point.valid_at)) : '' }));
  const watchCount = (overview?.cities || []).filter(city => city.risk === 'model_spike_watch').length;

  return <div className="page national-page">
    <PageHeading eyebrow="INDIA / MULTI-SCALE EARLY WARNING" title="From a national signal to a local investigation." description="Search any Indian city, village or postcode. AirSentinel uses the best available evidence without pretending a 45 km model grid is a street-level monitor." />
    <div className="national-controls">
      <form className="national-search" onSubmit={search}><Search size={17} /><input aria-label="Search an Indian city, village or postcode" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search city, village or postcode…" minLength={2} maxLength={80} /><button className="button primary" disabled={searching}>{searching ? <RefreshCw className="spin" size={14} /> : <Search size={14} />}Search India</button></form>
      <div className="pollutant-tabs" aria-label="National pollutant selection">{POLLUTANTS.map(item => <button key={item.id} className={pollutant === item.id ? 'active' : ''} onClick={() => setPollutant(item.id)} aria-pressed={pollutant === item.id}>{item.label}</button>)}</div>
    </div>
    {places.length ? <section className="place-results panel" aria-label="India place search results">{places.map(place => <button key={place.id} onClick={() => selectPlace({ label: place.label, latitude: place.latitude, longitude: place.longitude })}><span><strong>{place.name}</strong><small>{[place.admin2, place.admin1].filter(Boolean).join(', ')}{place.postcodes?.length ? ` · ${place.postcodes.slice(0, 3).join(', ')}` : ''}</small></span><ArrowRight size={15} /></button>)}</section> : null}
    {error ? <div className="notice danger" role="alert"><AlertTriangle size={17} /><span>{error}</span></div> : null}
    <div className="metrics-strip national-metrics"><Metric icon={MapPin} label="Selected place" value={selected.label} sub={`${selected.latitude.toFixed(4)}, ${selected.longitude.toFixed(4)}`} /><Metric icon={Wind} label={`${pollutantLabel(pollutant)} model estimate`} value={loading ? '…' : valueLabel(model.value)} sub={model.unit || 'No model value'} /><Metric icon={AlertTriangle} label="Next 6h model watch" value={loading ? '…' : spike.status === 'model_spike_watch' ? `${spike.lead_time_hours}h lead` : spike.status === 'no_model_spike_signal' ? 'No signal' : 'Unavailable'} sub={spike.status === 'model_spike_watch' ? `Peak ${valueLabel(spike.peak_value)} ${model.unit || ''}` : 'Coarse regional screen'} /><Metric icon={Activity} label="National watchlist flags" value={overview ? watchCount : '—'} sub={`${overview?.cities?.length || 0} bounded watchlist cities`} /></div>
    <section className="panel national-map-panel"><div className="panel-heading"><div><span className="eyebrow">PAN-INDIA / REGIONAL MODEL SCREEN</span><h2>National early-warning map</h2></div><StatusBadge status="delayed">~45 km model grid</StatusBadge></div><IndiaCoverageMap cities={overview?.cities || []} selected={selected} pollutant={pollutant} onSelect={selectPlace} /><div className="map-caption"><span><Satellite size={14} />CAMS global atmospheric model via Open-Meteo; watchlist values are estimates.</span><span>Search supports other Indian places on demand · not official AQI</span></div></section>
    <div className="national-detail-grid">
      <section className="panel"><div className="panel-heading"><div><span className="eyebrow">BEFORE THE SPIKE / SIX-HOUR SCREEN</span><h2>{selected.label}</h2></div><StatusBadge status={spike.status === 'model_spike_watch' ? 'delayed' : 'live'}>{spike.status === 'model_spike_watch' ? 'Verify locally' : 'No model spike signal'}</StatusBadge></div>{chartData.length ? <div className="national-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={chartData} margin={{ top: 12, right: 20, bottom: 5, left: 0 }}><CartesianGrid stroke="#1f3138" vertical={false} /><XAxis dataKey="label" tick={{ fill: '#718b98', fontSize: 9 }} axisLine={false} tickLine={false} /><YAxis tick={{ fill: '#718b98', fontSize: 9 }} axisLine={false} tickLine={false} width={45} /><Tooltip contentStyle={{ background: '#17242c', border: '1px solid #36514e', borderRadius: 6, fontSize: 10 }} formatter={value => [`${valueLabel(value)} ${model.unit || ''}`, pollutantLabel(pollutant)]} /><Line dataKey="value" stroke="#65e0b4" strokeWidth={2} dot={false} isAnimationActive={false} />{Number.isFinite(spike.screening_threshold) ? <ReferenceLine y={spike.screening_threshold} stroke="#e5b979" strokeDasharray="5 5" /> : null}</LineChart></ResponsiveContainer></div> : <EmptyState icon={Activity} title="Forecast series unavailable">The regional model did not return enough points for this location.</EmptyState>}<div className="chart-foot"><span>{spike.message || 'Waiting for the model screen.'}</span><span>{model.temporal_resolution}</span></div></section>
      <section className="panel source-panel"><div className="panel-heading"><div><span className="eyebrow">BEST AVAILABLE EVIDENCE</span><h2>Measured, modelled, or missing</h2></div><ShieldCheck size={18} /></div><EvidenceRow icon={Radio} title="Nearest fixed monitor" value={ground.status === 'fresh' || ground.status === 'delayed' ? `${ground.station_name} · ${valueLabel(ground.reading?.value)} ${ground.reading?.unit || ''}` : ground.status === 'not_configured' ? 'Ground-station connector not configured' : 'No usable nearby station returned'} detail={ground.distance_km != null ? `${ground.distance_km} km search distance · no coverage radius inferred` : ground.message} /><EvidenceRow icon={Satellite} title="Fallback model" value={model.status === 'available' ? `${valueLabel(model.value)} ${model.unit || ''} · ${dateLabel(model.valid_at)}` : 'Unavailable'} detail="CAMS global estimate at approximately 45 km resolution. Not official AQI or a neighbourhood reading." /><EvidenceRow icon={Database} title="Microscopic layer" value="Local sensor cluster required" detail="250 m cells organize human inspection only after multiple calibrated local and background devices corroborate a signal." /><div className="ledger-footer"><i className="legend-dot amber" />Never average station measurements and model estimates into one disguised city AQI.</div></section>
    </div>
    <section className="panel national-watchlist"><div className="panel-heading"><div><span className="eyebrow">BOUNDED NATIONAL WATCHLIST</span><h2>Regional signals to verify <span className="heading-count">{overview?.cities?.length || 0}</span></h2></div>{loading ? <RefreshCw className="spin" size={17} /> : <Activity size={17} />}</div>{overview?.cities?.length ? <div className="table-scroll"><table><thead><tr><th>City</th><th>{pollutantLabel(pollutant)} estimate</th><th>Next 6h screen</th><th>Lead / peak</th><th>Evidence</th></tr></thead><tbody>{overview.cities.map(city => <tr key={city.name}><td><button className="text-link city-select" onClick={() => selectPlace({ label: `${city.name}, ${city.state}`, latitude: city.latitude, longitude: city.longitude })}>{city.name}<small>{city.state}</small></button></td><td><span className="table-value">{valueLabel(city.model?.value)}</span> <small className="inline-unit">{city.model?.unit}</small></td><td><StatusBadge status={city.risk === 'model_spike_watch' ? 'delayed' : 'live'}>{city.risk === 'model_spike_watch' ? 'Model rise · verify' : 'No model spike signal'}</StatusBadge></td><td className="muted-text">{city.risk === 'model_spike_watch' ? `${city.model.spike_screen.lead_time_hours}h · ${valueLabel(city.model.spike_screen.peak_value)} ${city.model.unit || ''}` : '—'}</td><td className="muted-text">CAMS global · ~45 km</td></tr>)}</tbody></table></div> : <EmptyState icon={Activity} title={loading ? 'Loading national watchlist…' : 'National source unavailable'}>Search a location again after the model source recovers.</EmptyState>}</section>
    <div className="evidence-boundary"><ShieldCheck size={18} /><div><strong>What AirSentinel can and cannot do.</strong><p>It can screen every valid India coordinate with a regional atmospheric model and escalate selected places for local verification. It cannot produce microscopic AQI where no local surface instruments exist. Satellite aerosol, weather and citizen reports improve context; calibrated ground sensors remain necessary for neighbourhood claims.</p></div></div>
  </div>;
}

function Metric({ icon: Icon, label, value, sub }) { return <div className="metric"><span className="metric-label"><Icon size={14} />{label}</span><strong>{value}</strong><small>{sub}</small></div>; }
function EvidenceRow({ icon: Icon, title, value, detail }) { return <div className="ledger-row"><span className="ledger-icon"><Icon size={17} /></span><div><strong>{title}</strong><p>{value}</p>{detail ? <small>{detail}</small> : null}</div></div>; }
