import { useMemo } from 'react';
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Activity, ArrowUpRight } from 'lucide-react';
import { dateLabel, pollutantLabel, useMonitoring, valueLabel, usableMeasurement } from './data';

export default function EvidenceChart({ expanded = false }) {
  const { data, pollutant, loading } = useMonitoring();
  const history = data?.history;
  const forecast = data?.forecast;
  const unit = history?.unit || '';
  const points = useMemo(() => {
    const measured = (history?.points || []).filter(p => usableMeasurement(p) && (!unit || p.unit === unit)).map(p => ({ timestamp: new Date(p.observed_at).getTime(), measured: p.value })).sort((a, b) => a.timestamp - b.timestamp);
    const withGaps = measured.flatMap((point, index) => index && point.timestamp - measured[index - 1].timestamp > 90 * 60000 ? [{ timestamp: measured[index - 1].timestamp + 60000, measured: null }, point] : [point]);
    const predicted = (forecast?.points || []).filter(p => Number.isFinite(p.value) && (!p.unit || p.unit === unit) && Number.isFinite(new Date(p.observed_at).getTime())).map(p => ({ timestamp: new Date(p.observed_at).getTime(), forecast: p.value, model: p.model || forecast?.model, horizon: p.horizon_hours, band: Number.isFinite(p.lower) && Number.isFinite(p.upper) ? [p.lower, p.upper] : undefined }));
    return [...withGaps, ...predicted].sort((a, b) => a.timestamp - b.timestamp);
  }, [history, forecast, unit]);
  return <section className={`panel chart-panel ${expanded ? 'expanded-chart' : ''}`}>
    <div className="panel-heading"><div><span className="eyebrow">THE OBSERVATION WINDOW</span><h2>{pollutantLabel(pollutant)} · measured & forecast</h2></div><span className="subtle-tag">{unit || 'Unit pending'}</span></div>
    {points.length ? <div className="chart-container" role="img" aria-label={`${pollutantLabel(pollutant)} time series: ${history?.points?.length || 0} measured observations and ${forecast?.points?.length || 0} forecast points. Units ${unit}.`}>
      <ResponsiveContainer width="100%" height="100%"><ComposedChart data={points} margin={{ top: 15, right: 16, left: -17, bottom: 4 }}>
        <defs><linearGradient id="measurementFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#56e2b0" stopOpacity={0.2} /><stop offset="100%" stopColor="#56e2b0" stopOpacity={0} /></linearGradient></defs>
        <CartesianGrid stroke="#1c2a32" strokeDasharray="3 5" vertical={false} />
        <XAxis dataKey="timestamp" type="number" domain={['dataMin', 'dataMax']} scale="time" tickFormatter={t => new Date(t).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })} tick={{ fill: '#84949e', fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={38} />
        <YAxis tick={{ fill: '#84949e', fontSize: 11 }} axisLine={false} tickLine={false} domain={[0, 'auto']} />
        <Tooltip content={({ active, payload, label }) => active && payload?.length ? <div className="chart-tooltip"><strong>{dateLabel(label)}</strong>{payload.filter(p => p.dataKey !== 'band').map(p => <p key={p.dataKey}><span style={{ color: p.color }}>{p.dataKey === 'forecast' ? `Forecast · ${p.payload.model?.replaceAll('_', ' ') || 'research model'} · ${p.payload.horizon}h` : p.name}</span><b>{valueLabel(p.value)} {unit}</b></p>)}{payload.some(p => p.dataKey === 'band') ? <small>Band supplied by the forecast model</small> : null}</div> : null} />
        <Area type="linear" dataKey="band" stroke="none" fill="#dfb97a" fillOpacity={0.12} legendType="none" isAnimationActive={false} connectNulls={false} />
        <Area type="linear" dataKey="measured" name="Measured" stroke="#56e2b0" strokeWidth={2} fill="url(#measurementFill)" isAnimationActive={false} connectNulls={false} />
        <Line type="linear" dataKey="forecast" name={`Forecast · ${forecast?.model_label || forecast?.model || 'research model'}`} stroke="#e5bb78" strokeWidth={2} strokeDasharray="5 5" dot={false} isAnimationActive={false} connectNulls={false} />
        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 16 }} iconType="plainline" />
      </ComposedChart></ResponsiveContainer>
    </div> : <div className="empty-chart"><Activity size={28} /><h3>{loading ? 'Connecting to observation history' : 'A clear view starts with real observations'}</h3><p>{loading ? 'Fetching time-stamped station measurements.' : history?.message || 'No usable time series is available for this station and pollutant. Choose another station or view the research archive.'}</p></div>}
    <div className="chart-foot"><span><span className="legend-dash" /> {forecast?.points?.length ? `${forecast.model_label || forecast.model || 'Model output'} · research forecast` : 'Forecast waiting for sufficient fresh history'}</span><span>Time in IST <ArrowUpRight size={12} /></span></div>
    {forecast?.evaluation ? <p className="panel-note">Evaluation: {typeof forecast.evaluation === 'string' ? forecast.evaluation : forecast.evaluation.status?.replaceAll('_', ' ') || 'See model card'}</p> : null}
    {expanded && forecast?.evaluation?.horizons?.length ? <div className="table-scroll"><table><thead><tr><th>Horizon</th><th>Selected model</th><th>Holdout MAE</th><th>Holdout RMSE</th><th>Test rows</th></tr></thead><tbody>{forecast.evaluation.horizons.map(h => <tr key={h.horizon_hours}><td>{h.horizon_hours}h</td><td>{(h.selected_model || h.model || forecast.model)?.replaceAll('_', ' ')}</td><td>{valueLabel(h.mae)} {unit}</td><td>{valueLabel(h.rmse)} {unit}</td><td>{h.test_rows ?? '—'}</td></tr>)}</tbody></table></div> : null}
  </section>;
}
