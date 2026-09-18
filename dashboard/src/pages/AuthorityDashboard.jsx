import React from 'react';
import MetricCard from '../components/ui/MetricCard';
import AlertBanner from '../components/ui/AlertBanner';
import LivePollutantChart from '../components/charts/LivePollutantChart';
import ForecastChart from '../components/charts/ForecastChart';
import AnomalyTimeline from '../components/charts/AnomalyTimeline';
import GlassCard from '../components/ui/GlassCard';
import { useLiveData } from '../hooks/useLiveData';
import { Briefcase, AlertOctagon, Target, Clock, ExternalLink } from 'lucide-react';

const MOCK_ALERTS = [
  { id: 1, severity: 'critical', area: 'Anand Vihar', message: 'PM2.5 spike exceeded 400 µg/m³ threshold. Emergency dust control protocols activated.', timestamp: Date.now() },
  { id: 2, severity: 'warning', area: 'Punjabi Bagh', message: 'Predictive model forecasts severe NO2 accumulation in 3 hours due to traffic congestion.', timestamp: Date.now() - 1000 * 60 * 15 },
  { id: 3, severity: 'info', area: 'Dwarka Sector 10', message: 'Sensor DPCC-DWK back online after maintenance.', timestamp: Date.now() - 1000 * 60 * 45 }
];

const MOCK_FORECAST = Array.from({ length: 12 }).map((_, i) => ({
  timestamp: new Date(Date.now() - (11 - i) * 3600000).toISOString(),
  observed: i < 8 ? 60 + Math.random() * 40 + Math.sin(i) * 20 : null,
  predicted: 65 + Math.random() * 30 + Math.sin(i) * 20,
  interval_low: 50 + Math.sin(i) * 15,
  interval_high: 95 + Math.sin(i) * 25
}));

const MOCK_ANOMALIES = [
  { id: 1, type: 'Unexplained PM2.5 Spike', severity: 'critical', area: 'Okhla Industrial Estate', timestamp: Date.now() - 1000 * 60 * 10, description: 'Rapid increase from 120 to 350 µg/m³ within 15 minutes. Not correlated with weather patterns.', action: 'Dispatched enforcement team' },
  { id: 2, type: 'NO2 Pattern Anomaly', severity: 'warning', area: 'ITO Junction', timestamp: Date.now() - 1000 * 60 * 45, description: 'Sustained NO2 elevation despite low traffic volume reported.', action: 'Under review' }
];

const MOCK_CASES = [
  { id: 'CAS-8892', area: 'Okhla Phase II', category: 'Industrial', severity: 'critical', status: 'open', time: '10 mins ago' },
  { id: 'CAS-8891', area: 'Bawana', category: 'Waste Burning', severity: 'high', status: 'in-progress', time: '1 hour ago' },
  { id: 'CAS-8888', area: 'Ashok Vihar', category: 'Construction', severity: 'moderate', status: 'closed', time: '3 hours ago' }
];

export default function AuthorityDashboard() {
  const { data: liveData } = useLiveData();

  return (
    <div className="space-y-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Central Authority Dashboard</h1>
        <p className="text-slate-400">Delhi NCR Regional Air Quality Command Center</p>
      </header>

      <div className="-mx-6 mb-8">
        <AlertBanner alerts={MOCK_ALERTS} />
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="Active Enforcement Cases" value={24} trend={12} icon={Briefcase} color="amber" />
        <MetricCard title="Predicted Spikes (Next 4h)" value={3} trend={-2} icon={AlertOctagon} color="red" />
        <MetricCard title="Sensor Network Coverage" value={98.5} subtitle="Percentage of critical zones covered" icon={Target} color="green" />
        <MetricCard title="Avg Response Time" value="45m" trend={-15} icon={Clock} color="cyan" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[400px]">
        <LivePollutantChart data={liveData} title="Network-wide Average (Delhi)" />
        <ForecastChart forecasts={MOCK_FORECAST} />
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <GlassCard className="p-5 h-full">
            <h3 className="font-semibold text-lg text-slate-100 mb-4">Live Case Queue</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-slate-400">
                    <th className="pb-3 font-medium">Case ID</th>
                    <th className="pb-3 font-medium">Area</th>
                    <th className="pb-3 font-medium">Category</th>
                    <th className="pb-3 font-medium">Severity</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Time</th>
                    <th className="pb-3 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {MOCK_CASES.map(c => (
                    <tr key={c.id} className="border-b border-white/5 hover:bg-white/5 transition-colors group cursor-pointer">
                      <td className="py-4 text-cyan-400">{c.id}</td>
                      <td className="py-4 text-white">{c.area}</td>
                      <td className="py-4 text-slate-300">{c.category}</td>
                      <td className="py-4">
                        <span className={`px-2 py-1 rounded text-xs ${
                          c.severity === 'critical' ? 'bg-red-500/20 text-red-400' :
                          c.severity === 'high' ? 'bg-amber-500/20 text-amber-400' :
                          'bg-blue-500/20 text-blue-400'
                        }`}>
                          {c.severity.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-4">
                        <span className={`px-2 py-1 rounded-full border text-xs ${
                          c.status === 'open' ? 'border-red-500/50 text-red-400' :
                          c.status === 'in-progress' ? 'border-amber-500/50 text-amber-400' :
                          'border-green-500/50 text-green-400'
                        }`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="py-4 text-slate-400">{c.time}</td>
                      <td className="py-4">
                        <ExternalLink className="w-4 h-4 text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </div>
        <div className="xl:col-span-1">
          <AnomalyTimeline anomalies={MOCK_ANOMALIES} />
        </div>
      </div>
    </div>
  );
}
