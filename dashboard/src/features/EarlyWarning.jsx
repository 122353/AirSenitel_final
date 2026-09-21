import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Clock3, Database, MapPin, Radio, RefreshCw, Search, ShieldCheck, Wind } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, dateLabel, POLLUTANTS, pollutantLabel, useMonitoring, valueLabel } from './data';
import './early-warning.css';

const IndiaCoverageMap = lazy(() => import('./IndiaCoverageMap'));
const REFRESH_MS = 120000;
const timeLabel = value => Number.isFinite(Number(value)) ? new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }).format(new Date(Number(value))) : '—';
const leadLabel = hours => Number.isFinite(hours) && hours > 0 ? hours < 1 ? `${Math.round(hours * 60)} min` : `${valueLabel(hours)} hr` : '—';
const placeName = place => place ? `${place.name || place.label}${place.state ? `, ${place.state}` : ''}` : 'Select a location';
const statusLabel = status => ({ forecast_watch: 'Forecast watch', model_current_rise: 'Modelled rise now', no_model_spike_signal: 'No model rise signal', insufficient_data: 'Insufficient data' })[status] || 'Awaiting data';
const signalTime = row => row?.first_crossing_at || null;

/** Both workspaces share this evidence view. The private endpoint is only mounted inside AccessGate. */
export default function EarlyWarning({ authority = false, getToken }) {
  const [feed, setFeed] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const [target, setTarget] = useState(null);
  const [selectedId, setSelectedId] = useState('');
  const [pollutant, setPollutant] = useState('pm25');
  const [query, setQuery] = useState('');
  const [places, setPlaces] = useState([]);
  const [searchError, setSearchError] = useState('');
  const [searching, setSearching] = useState(false);
  const [mapOpen, setMapOpen] = useState(false);
  const requestId = useRef(0);
  const searchController = useRef(null);
  const refresh = useCallback(() => setTick(value => value + 1), []);

  useEffect(() => { const interval = setInterval(refresh, REFRESH_MS); return () => clearInterval(interval); }, [refresh]);
  useEffect(() => () => searchController.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController();
    const id = ++requestId.current;
    let timedOut = false;
    const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, 55000);
    setLoading(true);
    const load = async () => {
      const params = new URLSearchParams();
      if (target) { params.set('latitude', target.latitude); params.set('longitude', target.longitude); params.set('label', target.label); }
      const options = { signal: controller.signal };
      if (authority) {
        const token = await getToken?.();
        if (!token) throw new Error('Your operator session expired. Sign in again to reload this workspace.');
        options.headers = { Authorization: `Bearer ${token}` };
      }
      return api(`/api/v2/${authority ? 'authority/' : ''}early-warning${params.size ? `?${params}` : ''}`, options);
    };
    load().then(result => {
      if (id !== requestId.current || controller.signal.aborted) return;
      setFeed(result); setError('');
      if (!selectedId && result.alerts?.some(item => item.kind === 'forecast_watch')) {
        setPollutant(result.alerts.find(item => item.kind === 'forecast_watch').pollutant);
      }
      setSelectedId(previous => result.locations?.some(item => item.id === previous) ? previous : result.alerts?.find(item => item.kind === 'forecast_watch')?.location_id || result.locations?.[0]?.id || '');
    }).catch(err => {
      if (id === requestId.current && (!controller.signal.aborted || timedOut)) {
        setError(timedOut ? 'The warning feed timed out. Please retry.' : err.message);
        // Never retain private evidence after a failed authorization / refresh.
        if (authority) setFeed(null);
      }
    }).finally(() => { clearTimeout(timeout); if (id === requestId.current) setLoading(false); });
    return () => { controller.abort(); clearTimeout(timeout); };
  }, [target, tick, authority, getToken]);

  const search = async event => {
    event.preventDefault();
    if (query.trim().length < 2) return;
    searchController.current?.abort();
    const controller = new AbortController(); searchController.current = controller;
    setSearching(true); setSearchError(''); setPlaces([]);
    try {
      const result = await api(`/api/v2/india/places?${new URLSearchParams({ query: query.trim(), limit: 8 })}`, { signal: controller.signal });
      if (!controller.signal.aborted) { setPlaces(result.places || []); if (!result.places?.length) setSearchError('No matching Indian place found. Try a nearby town or district.'); }
    } catch (err) { if (!controller.signal.aborted) setSearchError(err.message); }
    finally { if (!controller.signal.aborted) setSearching(false); }
  };
  const changeTarget = place => {
    searchController.current?.abort(); setSearching(false); setPlaces([]); setSearchError(''); setFeed(null); setError(''); setSelectedId('');
    setTarget(place ? { latitude: place.latitude, longitude: place.longitude, label: place.label || placeName(place) } : null);
    if (place) setQuery(place.label || placeName(place)); else setQuery('');
  };
  const locations = feed?.locations || [];
  const selected = locations.find(item => item.id === selectedId) || locations[0];
  const selectedSignal = selected?.pollutants?.[pollutant];
  const alerts = (feed?.alerts || []).filter(item => item.kind === 'forecast_watch' && new Date(item.first_crossing_at).getTime() > Date.now());
  const firstAlert = [...alerts].filter(item => Number.isFinite(item.lead_time_hours) && item.lead_time_hours > 0).sort((a, b) => a.lead_time_hours - b.lead_time_hours)[0];
  const coverage = feed?.coverage || {};
  const currentModel = feed?.summary?.model_current_rise_count;
  const stale = Boolean(error || (feed?.generated_at && Date.now() - new Date(feed.generated_at).getTime() > 10 * 60000));
  const chooseAlert = item => { setSelectedId(item.location_id); setPollutant(item.pollutant); };
  const mapCities = useMemo(() => locations.filter(item => Number.isFinite(item.pollutants?.[pollutant]?.current)).map(item => ({ ...item, risk: item.pollutants?.[pollutant]?.status === 'forecast_watch' ? 'model_spike_watch' : undefined, model: { value: item.pollutants?.[pollutant]?.current, unit: item.pollutants?.[pollutant]?.unit } })), [locations, pollutant]);
  const chooseMapPlace = useCallback(place => {
    const existing = locations.find(item => item.latitude === place.latitude && item.longitude === place.longitude);
    if (existing) setSelectedId(existing.id);
  }, [locations]);

  return <section className="early-warning" aria-label={authority ? 'Operator early-warning board' : 'Public early-warning board'} aria-busy={loading}>
    <div className="ew-toolbar">
      <div className="ew-feed-status"><span className={`ew-status-dot ${stale || feed?.status !== 'available' ? 'uncertain' : ''}`} /><span>{loading ? 'Checking forecast sources' : stale ? 'Warning feed needs refresh' : feed?.status === 'available' ? 'Forecast screen updated' : feed?.status === 'partial' ? 'Partial forecast assessment' : 'Warning feed unavailable'}<small>{feed ? dateLabel(feed.generated_at) : 'No current assessment received'} · checks every 2 min</small></span></div>
      <button className="button secondary" onClick={refresh} disabled={loading}><RefreshCw size={14} className={loading ? 'spin' : ''} />Refresh warnings</button>
    </div>
    {error ? <div className="notice danger" role="alert">{error}{feed ? ' Previous results below are not a current alert.' : ''}</div> : null}
    {feed?.status === 'unavailable' ? <div className="notice amber" role="status">No usable regional forecast assessment was returned. Any zero counts describe received signals, not an absence of pollution risk.</div> : feed?.status === 'partial' ? <div className="notice amber" role="status">Some location–pollutant assessments are missing. Counts and charts cover only the available data.</div> : null}
    {stale && !error ? <div className="notice amber" role="status">This response is older than 10 minutes. Treat the displayed watches as an earlier assessment until refresh succeeds.</div> : null}
    <div className="ew-overview">
      <div className="ew-priority"><span className="ew-kicker"><Clock3 size={14} />NEXT SIX HOURS · RESEARCH SCREEN</span><h2>{loading && !feed ? 'Checking the horizon…' : firstAlert ? <>First model rise in <em>{leadLabel(firstAlert.lead_time_hours)}</em></> : !feed || feed.status === 'unavailable' ? 'The forecast is unavailable.' : alerts.length ? 'Forecast watches need review.' : 'No forecast rise flagged.'}</h2><p>{firstAlert ? `${placeName(firstAlert)} · ${pollutantLabel(firstAlert.pollutant)} crosses the screening threshold at ${dateLabel(firstAlert.first_crossing_at)}.` : !feed ? 'A missing feed cannot tell us that the air is safe.' : currentModel ? 'Some model values are already elevated. These are not advance predictions or sensor-confirmed events.' : 'This is a regional model screen, not a guarantee that a local pollution event will not happen.'}</p><div className="ew-scope"><MapPin size={13} />{target ? target.label : 'India · state / UT representative locations'}<span>~45 km model grid</span></div></div>
      <div className="ew-stats">
        <div><span>Forecast watches</span><strong>{feed ? feed.summary?.forecast_watch_count ?? alerts.length : '—'}</strong><small>Location–pollutant signals · not confirmed</small></div>
        <div><span>Modelled rises now</span><strong>{feed ? currentModel ?? '—' : '—'}</strong><small>Already in the model · no advance lead</small></div>
        <div><span>Locations assessed</span><strong>{feed ? coverage.assessed_locations ?? locations.length : '—'}<i> / {coverage.requested_locations ?? '—'}</i></strong><small>{target ? 'On-demand coordinate' : `${coverage.states_uts_represented ?? '—'} states / UTs represented · not every locality`}</small></div>
      </div>
    </div>
    <div className="ew-location-bar">
      <form className="ew-search" onSubmit={search}><Search size={17} /><input aria-label="Search India for a local forecast" placeholder="Search a city, village or postcode" value={query} onChange={event => setQuery(event.target.value)} minLength={2} maxLength={80} /><button type="submit" className="button secondary" disabled={searching}>{searching ? 'Searching…' : 'Find place'}</button></form>
      {target ? <button className="text-link" onClick={() => changeTarget(null)}>Back to India watchlist <ArrowUpRight size={14} /></button> : <span className="ew-search-hint">Other Indian locations available on demand</span>}
    </div>
    {searchError ? <p className="ew-search-error" role="status">{searchError}</p> : null}
    {places.length ? <div className="ew-search-results">{places.map(place => <button key={place.id || `${place.latitude}:${place.longitude}`} onClick={() => changeTarget(place)}><span>{place.label || place.name}<small>{[place.admin2, place.admin1].filter(Boolean).join(', ')}</small></span><ArrowRight size={15} /></button>)}</div> : null}
    <div className="ew-workbench">
      <section className="ew-chart-panel">
        <div className="ew-section-heading"><div><span className="ew-kicker">LOCATION OUTLOOK</span><label className="ew-place-select"><span className="sr-only">Select forecast location</span><select value={selected?.id || ''} onChange={event => setSelectedId(event.target.value)} disabled={!locations.length}>{!locations.length ? <option value="">Awaiting location data</option> : locations.map(item => <option key={item.id} value={item.id}>{placeName(item)}</option>)}</select><ArrowDownRight size={17} /></label></div><span className={`ew-signal-tag ${selectedSignal?.status || ''}`}>{statusLabel(selectedSignal?.status)}</span></div>
        <div className="ew-pollutants" aria-label="Forecast pollutant">{POLLUTANTS.map(item => <button key={item.id} onClick={() => setPollutant(item.id)} className={pollutant === item.id ? 'active' : ''} aria-pressed={pollutant === item.id}><span>{item.label}</span><small>{valueLabel(selected?.pollutants?.[item.id]?.current)}</small></button>)}</div>
        <OutlookChart signal={selectedSignal} pollutant={pollutant} generatedAt={feed?.generated_at} loading={loading} />
        <div className="ew-chart-caption"><span><i className="ew-line past" />Earlier model values</span><span><i className="ew-line forecast" />Model forecast</span><span><i className="ew-line threshold" />Screening threshold</span><span>µg/m³ · IST</span></div>
        <div className="ew-chart-details"><div><span>First crossing</span><strong>{signalTime(selectedSignal) ? dateLabel(signalTime(selectedSignal)) : !selectedSignal || selectedSignal.status === 'insufficient_data' ? 'Unavailable' : 'No future crossing'}</strong></div><div><span>Advance lead</span><strong>{selectedSignal?.status === 'forecast_watch' ? leadLabel(selectedSignal.lead_time_hours) : 'Not applicable'}</strong></div><div><span>Peak model value</span><strong>{valueLabel(selectedSignal?.peak_value)} <small>{selectedSignal?.unit === 'ug/m3' ? 'µg/m³' : selectedSignal?.unit || ''}</small></strong></div></div>
        <p className="ew-model-note">Past values in this chart are modelled, not ground measurements. Thresholds screen for unusual rises; they are not official AQI bands or validated alert probabilities.</p>
      </section>
      <section className="ew-alert-panel"><div className="ew-section-heading"><div><span className="ew-kicker">FORECAST WATCHES</span><h3>Review before the rise</h3></div><span className="ew-count">{alerts.length}</span></div><div className="ew-alert-list">{alerts.length ? [...alerts].sort((a, b) => (a.lead_time_hours ?? Infinity) - (b.lead_time_hours ?? Infinity)).map(item => <button className={`ew-alert ${selected?.id === item.location_id && pollutant === item.pollutant ? 'selected' : ''}`} key={item.id || `${item.location_id}:${item.pollutant}`} onClick={() => chooseAlert(item)}><span className="ew-alert-title">{item.name}<ArrowUpRight size={15} /></span><span className="ew-alert-meta">{pollutantLabel(item.pollutant)} · {leadLabel(item.lead_time_hours)} lead</span><span className="ew-alert-crossing">Crosses {valueLabel(item.threshold)} µg/m³ · {dateLabel(item.first_crossing_at)}</span><span className="ew-alert-proof">Model only · local verification needed</span></button>) : <div className="ew-quiet"><Activity size={26} /><h3>{loading && !feed ? 'Screening locations…' : !feed || feed.status === 'unavailable' ? 'No assessment available' : 'No future rise flagged'}</h3><p>{feed && feed.status !== 'unavailable' ? 'No threshold crossing was returned in the next six hours for assessed locations. Unobserved local events remain possible.' : 'The source has not provided a usable assessment. This is not an all-clear.'}</p></div>}</div><div className="ew-alert-foot"><ShieldCheck size={14} /><span>{authority ? 'Review local measurements before escalating. No external dispatch is connected.' : 'A watch prompts verification. It does not establish a pollution source.'}</span></div></section>
    </div>
    <div className="ew-bottom-grid"><WeatherContext weather={selected?.weather} /><div className="ew-coverage"><Database size={17} /><div><h3>Coverage, without the guesswork</h3><p>{coverage.forecast_locations ?? 0} locations have model forecasts. {feed?.summary?.insufficient_count ?? '—'} location–pollutant assessments lack sufficient data. {target ? 'This assessment is for the selected coordinate only.' : 'State / UT representatives are a bounded watchlist, not continuous monitoring of every Indian city.'}</p><p>Where no surface monitor exists, the model is regional context—not a measured street-level AQI.</p></div></div></div>
    <StationSignal />
    {feed?.official_context ? <SourceContext context={feed.official_context} /> : null}
    <details className="ew-map-disclosure" onToggle={event => setMapOpen(event.currentTarget.open)}><summary>Explore the geographic watchlist <span>Real map · pitched view <ArrowUpRight size={14} /></span></summary>{mapOpen ? <Suspense fallback={<div className="map-loading">Loading India map…</div>}><IndiaCoverageMap cities={mapCities} selected={Number.isFinite(selectedSignal?.current) ? selected : null} pollutant={pollutant} onSelect={chooseMapPlace} /></Suspense> : null}<p>Dots are representative forecast locations with usable model values, not ground sensors. Unavailable locations remain in the location selector.</p></details>
    <details className="ew-method"><summary>Sources & screening limits</summary><p>CAMS atmospheric forecasts via Open-Meteo · hourly, approximately 45 km grid. Weather is shown separately. NASA imagery/fire detections and government observations, when connected, are context—not a validated fused predictor.</p>{(feed?.limitations || []).map((item, index) => <p key={index}>{typeof item === 'string' ? item : item.message || item.label || ''}</p>)}<p>No system can guarantee advance detection of every sudden release. Street-level claims need fresh, calibrated local sensors and evaluation against real events.</p></details>
  </section>;
}

function OutlookChart({ signal, pollutant, generatedAt, loading }) {
  const points = useMemo(() => (signal?.series || []).map(point => ({ timestamp: new Date(point.valid_at).getTime(), past: point.phase === 'past_model' && Number.isFinite(point.value) ? point.value : null, forecast: point.phase === 'forecast' && Number.isFinite(point.value) ? point.value : null })).filter(point => Number.isFinite(point.timestamp)).sort((a, b) => a.timestamp - b.timestamp), [signal]);
  const now = new Date(generatedAt).getTime();
  const inRangeNow = Number.isFinite(now) && points.length && now >= points[0].timestamp && now <= points[points.length - 1].timestamp;
  return points.length ? <div className="ew-chart" role="img" aria-label={`${pollutantLabel(pollutant)} regional model: ${points.length} hourly values, past model and future forecast, micrograms per cubic metre. ${statusLabel(signal?.status)}.`}><ResponsiveContainer width="100%" height="100%"><LineChart data={points} margin={{ top: 24, right: 21, bottom: 8, left: -10 }}><CartesianGrid stroke="#29353b" vertical={false} /><XAxis dataKey="timestamp" type="number" domain={['dataMin', 'dataMax']} scale="time" tickFormatter={timeLabel} axisLine={false} tickLine={false} minTickGap={32} tick={{ fill: '#92a4aa', fontSize: 10 }} /><YAxis domain={[0, 'auto']} axisLine={false} tickLine={false} tick={{ fill: '#92a4aa', fontSize: 10 }} width={54} /><Tooltip content={({ active, payload, label }) => active && payload?.length ? <div className="chart-tooltip"><strong>{dateLabel(label)}</strong>{payload.filter(item => Number.isFinite(item.value)).map(item => <p key={item.dataKey}><span>{item.dataKey === 'past' ? 'Past model' : 'Model forecast'}</span><b>{valueLabel(item.value)} µg/m³</b></p>)}</div> : null} />{Number.isFinite(signal?.threshold) ? <ReferenceLine y={signal.threshold} stroke="#8c7e60" strokeDasharray="3 5" ifOverflow="extendDomain" /> : null}{inRangeNow ? <ReferenceLine x={now} stroke="#a7b5ba" strokeDasharray="2 4" label={{ value: 'Now', position: 'insideTopLeft', fill: '#a7b5ba', fontSize: 10 }} /> : null}<Line type="linear" dataKey="past" stroke="#93a5ae" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} /><Line type="linear" dataKey="forecast" stroke="#edbd76" strokeWidth={2.5} strokeDasharray="5 4" dot={{ r: 2, fill: '#edbd76', strokeWidth: 0 }} activeDot={{ r: 4 }} isAnimationActive={false} connectNulls={false} /></LineChart></ResponsiveContainer></div> : <div className="ew-chart-empty"><Activity size={26} /><strong>{loading ? 'Loading model timeline…' : 'Not enough model data'}</strong><p>Missing points stay missing. Choose another location or retry the source.</p></div>;
}

function WeatherContext({ weather }) {
  return <section className="ew-weather"><div><Wind size={17} /><h3>Weather context</h3><span>{weather?.status === 'available' ? dateLabel(weather.valid_at) : weather?.status === 'partial' ? 'Partial weather data' : 'Unavailable'}</span></div><dl><div><dt>Wind</dt><dd>{valueLabel(weather?.wind_speed_10m)} <small>{weather?.units?.wind_speed_10m || 'm/s'}</small></dd></div><div><dt>Direction</dt><dd>{valueLabel(weather?.wind_direction_10m)}<small>°</small></dd></div><div><dt>Humidity</dt><dd>{valueLabel(weather?.relative_humidity_2m)}<small>%</small></dd></div><div><dt>Rain</dt><dd>{valueLabel(weather?.precipitation)} <small>mm</small></dd></div></dl></section>;
}

function SourceContext({ context }) {
  // Provenance stays distinct from forecasts. Missing connectors never become substitute readings.
  const sources = Array.isArray(context.sources) ? context.sources : Object.entries(context).filter(([, value]) => value && typeof value === 'object' && !Array.isArray(value)).map(([key, value]) => ({ name: key.replaceAll('_', ' '), ...value }));
  if (!sources.length) return null;
  return <section className="ew-source-context"><div className="ew-section-heading"><div><span className="ew-kicker">SEPARATE EVIDENCE LAYERS</span><h3>Government & satellite sources</h3></div><Database size={17} /></div><div>{sources.map((source, index) => <article key={source.id || source.name || index}><h4>{source.label || source.name || 'Source context'}</h4><span className="ew-source-status">{String(source.status || 'unavailable').replaceAll('_', ' ')}</span><p>{source.reason || source.message || source.description || 'Source records available as context; not used to trigger forecast watches.'}</p>{source.coverage ? <small>{source.coverage.records_returned ?? 0} records returned{Number.isFinite(source.freshness?.fresh_records) ? ` · ${source.freshness.fresh_records} within source freshness window` : ''}{source.coverage.partial ? ' · partial query' : ''}</small> : null}<small>{source.freshness?.latest_observed_at ? `Latest: ${dateLabel(source.freshness.latest_observed_at)}` : 'No verified observation timestamp'}</small><p>{source.id === 'nasa_firms' ? 'Satellite fire detections are not surface PM₂.₅ or proof of a local pollution source.' : source.id === 'cpcb_data_gov' ? 'Government-published snapshots. Units are unverified in this feed; values are not used as concentration forecasts or official AQI.' : 'Missing source records do not mean clean air.'}</p>{typeof source.source_url === 'string' && /^https:\/\//.test(source.source_url) ? <a className="text-link" href={source.source_url} target="_blank" rel="noreferrer">Source documentation <ArrowUpRight size={12} /></a> : null}</article>)}</div></section>;
}

function StationSignal() {
  const { data, error, loading, stations, selectedStation, setStationId, pollutant } = useMonitoring();
  const signal = data?.station_warning;
  const disabled = Boolean(error || !signal || signal.status === 'archive');
  const observed = !disabled && signal.status === 'observed_rise';
  const forecast = !disabled && signal.status === 'forecast_watch';
  const label = observed ? 'Observed rise at this station' : forecast ? 'Station forecast watch' : disabled ? 'No current station assessment' : signal.status === 'no_qualified_signal' ? 'No qualified rise signal' : 'Insufficient current evidence';
  return <section className={`ew-station-signal ${observed || forecast ? 'flagged' : ''}`}><div className="ew-section-heading"><div><span className="ew-kicker"><Radio size={14} />GROUND-STATION SIGNAL · SEPARATE FROM REGIONAL MODEL</span><h3>{label}</h3></div><span className="ew-signal-tag">Selected monitor only</span></div><div className="ew-station-body"><div><label className="ew-station-select"><span>Measured evidence location</span><select aria-label="Select ground-station signal" value={selectedStation?.id || ''} disabled={!stations.length} onChange={event => setStationId(event.target.value)}>{!stations.length ? <option value="">{loading ? 'Loading station directory…' : 'No station directory'}</option> : stations.map(station => <option value={station.id} key={station.id}>{station.name}</option>)}</select></label><p>{error ? 'Station refresh failed. Previous observations cannot establish a current event.' : signal?.message || 'Waiting for enough fresh station observations to assess a sudden rise.'}</p></div><dl><div><dt>{pollutantLabel(signal?.pollutant || pollutant)} measured</dt><dd>{valueLabel(disabled ? null : signal?.current)} <small>{signal?.unit || ''}</small></dd></div><div><dt>{forecast ? 'First future crossing' : 'Observation time'}</dt><dd className="ew-station-time">{disabled ? 'Unavailable' : dateLabel(forecast ? signal.first_crossing_at : signal.observed_at)}</dd></div>{forecast ? <div><dt>Advance lead</dt><dd>{leadLabel(signal.lead_time_hours)}</dd></div> : null}</dl></div><div className="ew-station-foot">{observed ? 'A rise already observed is detection, not an advance prediction. ' : forecast ? `${signal.model_label || 'Station research model'} · ${signal.trained_model ? 'fitted model' : 'research forecast'} · ` : ''}This monitor is not automatically representative of the searched place. No citywide or microscopic coverage is assumed.</div></section>;
}
