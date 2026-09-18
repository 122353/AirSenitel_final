import React from 'react';
import Globe from '../components/3d/Globe';
import GlassCard from '../components/ui/GlassCard';
import MetricCard from '../components/ui/MetricCard';
import { Database, Network, Share2, ShieldCheck, CheckCircle2 } from 'lucide-react';

const MODELS = [
  { country: 'India', type: 'Spike Prediction (LSTM)', pollutants: ['PM2.5', 'NO2'], date: '2026-09-15', mae: '4.2', status: 'Active' },
  { country: 'China', type: 'Industrial Emission CNN', pollutants: ['SO2', 'CO'], date: '2026-09-12', mae: '3.8', status: 'Active' },
  { country: 'Brazil', type: 'Forest Fire Detection', pollutants: ['PM10', 'O3'], date: '2026-09-10', mae: '5.1', status: 'Validating' },
  { country: 'Russia', type: 'Winter Inversion Model', pollutants: ['PM2.5'], date: '2026-08-30', mae: '6.4', status: 'Active' },
  { country: 'South Africa', type: 'Mining Dust Spread', pollutants: ['PM10'], date: '2026-09-18', mae: '-', status: 'Syncing' },
];

export default function BRICSFederation() {
  return (
    <div className="space-y-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">BRICS Federation Network</h1>
        <p className="text-slate-400">Cross-border AI model sharing and coordinated climate action</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <MetricCard title="Partners Connected" value={5} subtitle="Full active mesh" icon={Network} color="cyan" />
        <MetricCard title="Federated Models" value={12} trend={20} subtitle="Models shared this month" icon={Share2} color="green" />
        <MetricCard title="Global Alerts Coordinated" value={142} trend={5} icon={ShieldCheck} color="blue" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[500px]">
        {/* Globe Container */}
        <GlassCard className="p-0 relative overflow-hidden h-full flex flex-col border-cyan-500/30 shadow-[0_0_30px_rgba(6,182,212,0.1)]">
          <div className="absolute top-4 left-4 z-10 flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 text-sm font-medium backdrop-blur-md">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse-ring" />
            Live Sync: Federated Hub
          </div>
          <div className="flex-1 relative">
            <Globe />
          </div>
        </GlassCard>

        {/* Model Registry */}
        <GlassCard className="p-5 h-full flex flex-col">
          <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            Federated Model Registry
          </h3>
          
          <div className="flex-1 overflow-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="border-b border-white/10 text-slate-400">
                  <th className="pb-3 font-medium">Node</th>
                  <th className="pb-3 font-medium">Model Specialization</th>
                  <th className="pb-3 font-medium">Target</th>
                  <th className="pb-3 font-medium">MAE</th>
                  <th className="pb-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {MODELS.map((model, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="py-4 text-white font-medium flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${model.status === 'Active' ? 'bg-green-500' : model.status === 'Validating' ? 'bg-amber-500' : 'bg-blue-500 animate-pulse'}`} />
                      {model.country}
                    </td>
                    <td className="py-4 text-slate-300">{model.type}</td>
                    <td className="py-4">
                      <div className="flex gap-1">
                        {model.pollutants.map(p => (
                          <span key={p} className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-slate-300">{p}</span>
                        ))}
                      </div>
                    </td>
                    <td className="py-4 text-slate-400">{model.mae}</td>
                    <td className="py-4">
                      {model.status === 'Active' ? (
                        <span className="text-green-400 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Active</span>
                      ) : (
                        <span className="text-amber-400">{model.status}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="mt-4 pt-4 border-t border-white/10 flex justify-between items-center text-xs text-slate-400">
            <span>Last aggregation: 12 mins ago</span>
            <button className="text-cyan-400 hover:text-cyan-300 transition-colors">Trigger Manual Sync</button>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
