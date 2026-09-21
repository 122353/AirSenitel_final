import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@clerk/react';
import { Activity, ArrowDownToLine, ArrowUpRight, CheckCircle2, Clock3, RefreshCw, ShieldCheck, Zap } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { PageHeading, EmptyState } from '../App';
import { AccessGate } from './Authentication';
import { api, dateLabel, pollutantLabel, POLLUTANTS, valueLabel } from './data';
import { isRecentSpike, observedChartPoints, verificationPayload } from './spikeData';
import './spikes.css';

export default function SuddenSpikes() {
  return <div className="page spikes-page"><PageHeading eyebrow="GROUND EVIDENCE / OBSERVED CHANGES" title="Sudden spikes." description="See measured pollution rises, inspect the evidence and ask an operator to verify. Predictions stay in Early warning." action={<Link to="/" className="button secondary">View forecast watches<ArrowUpRight size={15} /></Link>} /><SpikeWorkspace /></div>;
}

export function SpikeWorkspace({ authority = false, onReview }) {
  const [stationId, setStationId] = useState('');
  const [pollutant, setPollutant] = useState('pm25');
  const [data, setData] = useState(null);
  const [directory, setDirectory] = useState([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [tick, setTick] = useState(0);
  const [checkedAt, setCheckedAt] = useState(null);
  const [request, setRequest] = useState(null);
  useEffect(() => { const timer = setInterval(() => setTick(n => n + 1), 60000); return () => clearInterval(timer); }, []);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const timeout = setTimeout(() => controller.abort(), 55000);
    setBusy(true);
    const query = new URLSearchParams({ pollutant });
    if (stationId) query.set('station_id', stationId);
    api(`/api/v2/spikes?${query}`, { signal: controller.signal }).then(result => {
      if (!active) return;
      setData(result); setDirectory(result.stations || []); setError(''); setCheckedAt(new Date().toISOString());
    }).catch(err => {
      if (!active) return;
      setData(null); setError(controller.signal.aborted ? 'The source check timed out. Try again.' : err.message);
    }).finally(() => { clearTimeout(timeout); if (active) setBusy(false); });
    return () => { active = false; controller.abort(); clearTimeout(timeout); };
  }, [stationId, pollutant, tick]);
  const changeSelection = (setter, value) => { setData(null); setError(''); setCheckedAt(null); setRequest(null); setter(value); };
  const events = (data?.events || []).filter(event => isRecentSpike(event.observed_at));
  const warning = data?.station_warning;
  const available = data?.data_mode === 'live' && data?.detection_status !== 'unavailable';
  const requestCurrent = !busy && !error && events.some(event => event.id === request?.event.id);
  return <div className="spike-workspace">
    <div className="spike-controls panel"><label className="field"><span>Monitoring station</span><select aria-label="Spike monitoring station" value={data?.selected_station_id || stationId} onChange={e => changeSelection(setStationId, e.target.value)} disabled={!directory.length}><option value="" disabled>{directory.length ? 'Choose a station' : 'Loading station directory…'}</option>{directory.map(station => <option key={station.id} value={station.id}>{station.name}</option>)}</select></label><label className="field"><span>Pollutant</span><select aria-label="Spike pollutant" value={pollutant} onChange={e => changeSelection(setPollutant, e.target.value)}>{POLLUTANTS.map(p => <option key={p.id} value={p.id}>{p.label} · {p.name}</option>)}</select></label><button className="button secondary" disabled={busy} onClick={() => setTick(n => n + 1)}><RefreshCw size={15} className={busy ? 'spin' : ''} />{busy ? 'Checking…' : 'Check now'}</button></div>
    <div className="spike-refresh"><span><Clock3 size={13} />Auto-check every 60s · sensor reporting may be delayed</span><span>{checkedAt ? `Last check ${dateLabel(checkedAt)}` : 'Awaiting first source check'}</span></div>
    {error ? <div className="notice danger" role="alert">{error} No current spike claims are shown until the feed recovers.</div> : null}
    <section className={`panel spike-summary ${events.length ? 'has-signals' : ''}`} aria-live="polite"><span className="spike-symbol"><Zap size={26} /></span><div><span className="eyebrow">MEASURED, NOT PREDICTED</span><h2>{!data && busy ? 'Checking ground observations…' : !available ? 'Spike detection unavailable' : events.length ? `${events.length} observed ${events.length === 1 ? 'rise needs' : 'rises need'} verification` : 'No qualifying spike in this check'}</h2><p>{!available ? 'A current source response is required. Missing or delayed data is never treated as clean air.' : events.length ? 'These are screening signals, not confirmed incidents. Ask for review before drawing a local conclusion.' : warning?.message || 'Evidence may be insufficient. No signal does not mean the air is safe.'}</p></div><div className="spike-coverage"><strong>{data?.coverage?.latest_stations_requested ?? '—'}</strong><span>stations queried<br />selected station + bounded peers</span></div></section>
    <div className="spike-layout"><MeasuredChart data={data} pollutant={pollutant} /><aside className="panel spike-method"><span className="eyebrow">HOW TO READ THIS</span><h2>A signal starts a check.</h2><ol><li><strong>Observe the rise</strong><p>Valid hourly station readings are compared with a prior baseline. Missing hours and unsupported units can prevent detection.</p></li><li><strong>Ask for verification</strong><p>A signed-in request saves the server-checked station evidence to the private operator queue.</p></li><li><strong>Review before action</strong><p>An operator checks the readings and records follow-up. A request is not proof of a pollution source.</p></li></ol>{authority ? <button className="button secondary" onClick={onReview}><ShieldCheck size={15} />Open verification queue</button> : <Link to="/authority" className="text-link">Operator review workspace<ArrowUpRight size={14} /></Link>}</aside></div>
    <section className="spike-signals"><div className="spike-section-heading"><div><span className="eyebrow">VERIFICATION INBOX</span><h2>Observed signals</h2></div><span className="subtle-tag">Station points only</span></div>{events.length ? <div className="spike-event-list">{events.map(event => <article className="panel spike-event" key={event.id}><div className="spike-event-header"><span className="status-badge pending_review"><i />Unverified observed rise</span><span>{dateLabel(event.observed_at)}</span></div><h3>{event.name}</h3><div className="spike-reading"><strong>{valueLabel(event.value)}<small>{event.unit}</small></strong><span>{pollutantLabel(event.pollutant)}<br />Baseline {valueLabel(event.baseline)} · screen {valueLabel(event.threshold)}</span></div><p>{event.basis === 'two_consecutive_hourly_rises' ? 'Two consecutive accepted hours above the pre-event screen.' : 'A quality-screened measured anomaly. Inspect the evidence during review.'}</p>{event.corroboration?.length ? <p className="panel-note">{event.corroboration.length} other station signal(s) support review, not a shared local cause or neighbourhood boundary.</p> : null}<div className="spike-event-footer"><span>OpenAQ station evidence · human review required</span><button className="button primary" disabled={busy || Boolean(error)} onClick={() => setRequest({ event, stationId: data.selected_station_id })}><ShieldCheck size={15} />Request verification</button></div></article>)}</div> : <div className="panel"><EmptyState icon={Activity} title={busy && !data ? 'Waiting for evidence' : !available ? 'Detection unavailable' : 'No reviewable spike available'}>A verification request appears only when a recent measured rise passes the screening rules. Stale readings, model predictions and unqueried stations cannot create a measured-spike request.</EmptyState></div>}</section>
    {request ? <section className="spike-request" aria-label="Spike verification request"><div className="spike-section-heading"><h2>Verify: {request.event.name}</h2><button className="button secondary" onClick={() => setRequest(null)}>Close request</button></div><AccessGate><VerificationForm key={request.event.id} event={request.event} stationId={request.stationId} eligible={requestCurrent} /></AccessGate></section> : null}
    <div className="notice amber"><ShieldCheck size={16} /><span>Coverage is limited to the queried stations, not continuous monitoring of every Indian station or neighbourhood. Source cadence and data gaps limit detection speed. No government dispatch or external alerts are connected.</span></div>
  </div>;
}

function MeasuredChart({ data, pollutant }) {
  const history = data?.history;
  const unit = history?.unit || '';
  const points = useMemo(() => observedChartPoints(history), [history]);
  const threshold = data?.station_warning?.threshold;
  return <section className="panel spike-chart"><div className="panel-heading"><div><span className="eyebrow">SELECTED STATION / ACCEPTED HISTORY</span><h2>{pollutantLabel(pollutant)} observed trend</h2></div><span className="subtle-tag">{unit || 'No unit'}</span></div><p className="spike-chart-station">{data?.selected_station?.name || 'Waiting for station evidence'}</p>{points.length ? <div className="spike-chart-canvas" role="img" aria-label={`${pollutantLabel(pollutant)} quality-accepted hourly measurements. Units ${unit}. Gaps are not interpolated.`}><ResponsiveContainer width="100%" height="100%"><LineChart data={points} margin={{ top: 20, right: 24, bottom: 8, left: -10 }}><CartesianGrid stroke="#26333a" strokeDasharray="3 5" vertical={false} /><XAxis type="number" dataKey="time" domain={['dataMin', 'dataMax']} tickFormatter={t => new Date(t).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })} tick={{ fill: '#96a7af', fontSize: 10 }} minTickGap={42} axisLine={false} tickLine={false} /><YAxis domain={[0, 'auto']} tick={{ fill: '#96a7af', fontSize: 10 }} axisLine={false} tickLine={false} /><Tooltip content={({ active, payload, label }) => active && payload?.length ? <div className="chart-tooltip"><strong>{dateLabel(label)}</strong><p>Measured <b>{valueLabel(payload[0].value)} {unit}</b></p></div> : null} /><Line type="linear" dataKey="value" stroke="#65e0b4" strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />{Number.isFinite(threshold) ? <ReferenceLine y={threshold} stroke="#e5b979" strokeDasharray="5 5" ifOverflow="extendDomain" /> : null}</LineChart></ResponsiveContainer></div> : <EmptyState icon={Activity} title="No quality-accepted history">{history?.message || 'Valid hourly measurements are required to draw this trend. No substitute or forecast values are plotted.'}</EmptyState>}<div className="chart-foot"><span>Measured history · no forecast values</span><span>{Number.isFinite(threshold) ? `Dashed line: screening threshold ${valueLabel(threshold)}` : 'Screening baseline unavailable'}</span></div></section>;
}

function VerificationForm({ event, stationId, eligible }) {
  const { getToken } = useAuth();
  const [notes, setNotes] = useState('');
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [receipt, setReceipt] = useState('');
  const submit = async e => {
    e.preventDefault(); if (!consent || !eligible || busy) return;
    setBusy(true); setError('');
    try {
      const token = await getToken(); if (!token) throw new Error('Please sign in again to request verification.');
      const result = await api('/api/v2/spikes/verification', { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(verificationPayload(event, stationId, notes, consent)) });
      if (!result.receipt) throw new Error('No private receipt was returned. Check with an operator before retrying.');
      setReceipt(result.receipt);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  const saveReceipt = () => {
    const url = URL.createObjectURL(new Blob([`VayuNirikshak private verification receipt\n\n${receipt}\n\nKeep private. Community reports > Withdraw a previous report allows withdrawal.\n`], { type: 'text/plain' }));
    const link = document.createElement('a'); link.href = url; link.download = 'vayunirikshak-verification-receipt.txt'; link.click(); URL.revokeObjectURL(url);
  };
  if (receipt) return <div className="panel success-panel" role="status"><CheckCircle2 size={30} /><h2>Verification requested.</h2><p>The evidence is in the private operator queue, pending review—not confirmed. Save your private receipt to withdraw the request later.</p><div className="receipt">{receipt}</div><button className="button primary" onClick={saveReceipt}><ArrowDownToLine size={15} />Save private receipt</button><Link className="text-link" to="/report">Withdraw through Community reports</Link></div>;
  return <form className="panel form-body spike-verification-form" onSubmit={submit}><h3>Request a human evidence check</h3><p>{pollutantLabel(event.pollutant)} {valueLabel(event.value)} {event.unit} · {dateLabel(event.observed_at)}. The server checks this signal again before accepting your request.</p><label className="field"><span>Additional context (optional)</span><textarea maxLength={1500} value={notes} onChange={e => setNotes(e.target.value)} placeholder="What would you like the operator to check? Avoid personal addresses and contact details." /></label><label className="check-field"><input type="checkbox" required checked={consent} onChange={e => setConsent(e.target.checked)} /><span>I consent to private storage and operator review of this station evidence, my account identity and these notes. This request does not confirm an incident or trigger external dispatch.</span></label>{!eligible ? <p className="notice amber">The signal is being rechecked or is no longer current. Submission is paused until it qualifies again.</p> : null}{error ? <p className="inline-message error" role="alert">{error}</p> : null}<button className="button primary" disabled={!consent || !eligible || busy}>{busy ? <RefreshCw className="spin" size={15} /> : <ShieldCheck size={15} />}{busy ? 'Checking and submitting…' : 'Send verification request'}</button></form>;
}
