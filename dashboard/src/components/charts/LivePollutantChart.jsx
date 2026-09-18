import React, { useState } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceArea 
} from 'recharts';
import { WHO_THRESHOLDS, POLLUTANT_COLORS } from '../../utils/pollutantThresholds';
import GlassCard from '../ui/GlassCard';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="backdrop-blur-md bg-slate-900/90 border border-white/20 p-4 rounded-xl shadow-2xl">
        <p className="text-slate-300 text-xs mb-3">{new Date(label).toLocaleTimeString()}</p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2">
          {payload.map((entry, index) => (
            <div key={index} className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
              <span className="text-slate-300 text-sm w-12">{entry.name.toUpperCase()}</span>
              <span className="text-white font-bold text-sm text-right w-12">{entry.value}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export default function LivePollutantChart({ data, title = "Real-time Pollutant Levels" }) {
  const [timeRange, setTimeRange] = useState('1h');
  const [visibleLines, setVisibleLines] = useState({
    pm25: true, pm10: true, no2: false, o3: false, so2: false, co: false
  });

  const toggleLine = (dataKey) => {
    setVisibleLines(prev => ({ ...prev, [dataKey]: !prev[dataKey] }));
  };

  const renderCustomLegend = () => {
    return (
      <div className="flex flex-wrap justify-center gap-4 mt-4">
        {Object.entries(POLLUTANT_COLORS).map(([key, color]) => (
          <button
            key={key}
            onClick={() => toggleLine(key)}
            className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs transition-all ${
              visibleLines[key] ? 'bg-white/10 text-white' : 'bg-transparent text-slate-500 hover:text-slate-300'
            }`}
          >
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: visibleLines[key] ? color : 'transparent', border: `1px solid ${color}` }} />
            {key.toUpperCase()}
          </button>
        ))}
      </div>
    );
  };

  return (
    <GlassCard className="p-5 h-full flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <h3 className="font-semibold text-lg text-slate-100">{title}</h3>
        <div className="flex bg-slate-800/50 rounded-lg p-1">
          {['1h', '6h', '24h', '7d'].map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                timeRange === range ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} opacity={0.4} />
            <XAxis 
              dataKey="timestamp" 
              tickFormatter={(tick) => new Date(tick).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              stroke="#64748b" 
              fontSize={12}
              tickMargin={10}
              minTickGap={30}
            />
            <YAxis stroke="#64748b" fontSize={12} tickMargin={10} />
            <Tooltip content={<CustomTooltip />} />
            
            {/* WHO Threshold References for PM2.5 (visible only if PM2.5 is toggled) */}
            {visibleLines.pm25 && (
              <>
                <ReferenceArea y1={0} y2={WHO_THRESHOLDS.pm25[0]} fill="#22c55e" fillOpacity={0.05} />
                <ReferenceArea y1={WHO_THRESHOLDS.pm25[0]} y2={WHO_THRESHOLDS.pm25[1]} fill="#eab308" fillOpacity={0.05} />
                <ReferenceArea y1={WHO_THRESHOLDS.pm25[1]} y2={WHO_THRESHOLDS.pm25[2]} fill="#f97316" fillOpacity={0.05} />
                <ReferenceArea y1={WHO_THRESHOLDS.pm25[2]} fill="#ef4444" fillOpacity={0.05} />
              </>
            )}

            {Object.entries(POLLUTANT_COLORS).map(([key, color]) => (
              visibleLines[key] && (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={color}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6, fill: color, stroke: '#1e293b', strokeWidth: 2 }}
                  isAnimationActive={false} // Disable to prevent jerky re-renders on every tick, handled smoothly by data shift
                />
              )
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      {renderCustomLegend()}
    </GlassCard>
  );
}
