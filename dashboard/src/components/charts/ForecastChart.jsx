import React, { useState } from 'react';
import { 
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Scatter 
} from 'recharts';
import GlassCard from '../ui/GlassCard';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const observed = payload.find(p => p.dataKey === 'observed');
    const predicted = payload.find(p => p.dataKey === 'predicted');
    const interval = payload.find(p => p.dataKey === 'interval_high');
    const anomaly = payload.find(p => p.dataKey === 'anomaly');

    return (
      <div className="backdrop-blur-md bg-slate-900/90 border border-white/20 p-4 rounded-xl shadow-2xl">
        <p className="text-slate-300 text-xs mb-3">{new Date(label).toLocaleTimeString()}</p>
        
        {observed && (
          <div className="flex justify-between items-center gap-4 mb-1">
            <span className="text-slate-400 text-sm">Observed:</span>
            <span className="text-white font-bold">{observed.value.toFixed(1)}</span>
          </div>
        )}
        
        {predicted && (
          <div className="flex justify-between items-center gap-4 mb-1">
            <span className="text-cyan-400 text-sm">Predicted:</span>
            <span className="text-cyan-400 font-bold">{predicted.value.toFixed(1)}</span>
          </div>
        )}

        {interval && interval.payload.interval_low !== undefined && (
          <div className="flex justify-between items-center gap-4 mb-1">
            <span className="text-slate-500 text-xs">95% CI:</span>
            <span className="text-slate-500 text-xs">
              [{interval.payload.interval_low.toFixed(1)} - {interval.payload.interval_high.toFixed(1)}]
            </span>
          </div>
        )}

        {anomaly && anomaly.value && (
          <div className="mt-2 pt-2 border-t border-white/10 text-red-400 text-xs font-semibold flex items-center gap-1">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
            Anomaly Detected
          </div>
        )}
      </div>
    );
  }
  return null;
};

export default function ForecastChart({ forecasts = [], title = "AI Spike Forecast vs Observed" }) {
  const [horizon, setHorizon] = useState('3h');

  // Format data for Recharts Area (needs array of [low, high])
  const chartData = forecasts.map(d => ({
    ...d,
    ci: d.interval_low !== null ? [d.interval_low, d.interval_high] : null,
    anomaly: d.observed && d.interval_high && d.observed > d.interval_high ? d.observed : null
  }));

  return (
    <GlassCard className="p-5 h-full flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <h3 className="font-semibold text-lg text-slate-100">{title}</h3>
        <div className="flex bg-slate-800/50 rounded-lg p-1">
          {['1h', '3h', '4h'].map(h => (
            <button
              key={h}
              onClick={() => setHorizon(h)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                horizon === h ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {h}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} opacity={0.4} />
            <XAxis 
              dataKey="timestamp" 
              tickFormatter={(tick) => new Date(tick).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              stroke="#64748b" 
              fontSize={12}
              tickMargin={10}
            />
            <YAxis stroke="#64748b" fontSize={12} tickMargin={10} />
            <Tooltip content={<CustomTooltip />} />
            
            {/* Confidence Interval Area */}
            <Area 
              type="monotone" 
              dataKey="ci" 
              stroke="none" 
              fill="#06b6d4" 
              fillOpacity={0.1} 
              isAnimationActive={false}
            />
            
            {/* Predicted Line */}
            <Line 
              type="monotone" 
              dataKey="predicted" 
              stroke="#06b6d4" 
              strokeWidth={2} 
              strokeDasharray="5 5" 
              dot={false}
              isAnimationActive={false}
            />
            
            {/* Observed Line */}
            <Line 
              type="monotone" 
              dataKey="observed" 
              stroke="#f8fafc" 
              strokeWidth={2} 
              dot={false}
              isAnimationActive={false}
            />

            {/* Anomaly Markers */}
            <Scatter 
              dataKey="anomaly" 
              fill="#ef4444" 
              line={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      
      <div className="flex justify-center gap-6 mt-4 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-slate-100" /> Observed
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 border-t-2 border-dashed border-cyan-400" /> Predicted
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-3 bg-cyan-400/20" /> 95% Confidence
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-red-500" /> Anomaly
        </div>
      </div>
    </GlassCard>
  );
}
