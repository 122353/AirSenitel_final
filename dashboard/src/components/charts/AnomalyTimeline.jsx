import React from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, AlertTriangle, Info } from 'lucide-react';
import GlassCard from '../ui/GlassCard';

export default function AnomalyTimeline({ anomalies = [] }) {
  const getSeverityConfig = (severity) => {
    switch (severity) {
      case 'critical': return { color: 'bg-red-500', glow: 'shadow-[0_0_10px_rgba(239,68,68,0.8)]', icon: ShieldAlert, border: 'border-red-500/30' };
      case 'warning': return { color: 'bg-amber-500', glow: 'shadow-[0_0_10px_rgba(245,158,11,0.8)]', icon: AlertTriangle, border: 'border-amber-500/30' };
      default: return { color: 'bg-blue-500', glow: 'shadow-[0_0_10px_rgba(59,130,246,0.8)]', icon: Info, border: 'border-blue-500/30' };
    }
  };

  return (
    <GlassCard className="p-5 overflow-hidden">
      <h3 className="font-semibold text-lg text-slate-100 mb-6">Recent Detection Events</h3>
      
      <div className="relative">
        {/* Timeline Line */}
        <div className="absolute left-[27px] top-4 bottom-0 w-px bg-slate-700" />
        
        <div className="space-y-6">
          {anomalies.map((anomaly, idx) => {
            const config = getSeverityConfig(anomaly.severity);
            const Icon = config.icon;
            
            return (
              <motion.div 
                key={anomaly.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="relative flex items-start gap-4 cursor-pointer group"
              >
                {/* Marker */}
                <div className={`relative z-10 w-14 h-14 rounded-full flex items-center justify-center border-4 border-slate-900 ${config.color} ${config.glow} transition-transform group-hover:scale-110`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                
                {/* Content Card */}
                <div className={`flex-1 backdrop-blur-md bg-white/5 border ${config.border} rounded-xl p-4 transition-all group-hover:bg-white/10 group-hover:-translate-y-1`}>
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h4 className="text-white font-medium text-base">{anomaly.type}</h4>
                      <p className="text-cyan-400 text-sm">{anomaly.area}</p>
                    </div>
                    <span className="text-slate-400 text-xs bg-slate-800/80 px-2 py-1 rounded-md">
                      {new Date(anomaly.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-slate-300 text-sm">{anomaly.description}</p>
                  
                  {anomaly.action && (
                    <div className="mt-3 inline-flex items-center gap-1 text-xs text-green-400 bg-green-400/10 px-2 py-1 rounded">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
                      {anomaly.action}
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
          
          {anomalies.length === 0 && (
            <div className="text-center py-8 text-slate-500">
              No recent anomalies detected.
            </div>
          )}
        </div>
      </div>
    </GlassCard>
  );
}
