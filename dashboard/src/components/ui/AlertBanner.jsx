import React from 'react';
import { AlertTriangle, Info, ShieldAlert, Radio } from 'lucide-react';

export default function AlertBanner({ alerts = [], onSelectAlert }) {
  if (!alerts || alerts.length === 0) return null;

  const getSeverityStyles = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-500/15 text-red-300 border-red-500/40 hover:bg-red-500/25';
      case 'warning': return 'bg-amber-500/15 text-amber-300 border-amber-500/40 hover:bg-amber-500/25';
      default: return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/40 hover:bg-cyan-500/25';
    }
  };

  const getIcon = (severity) => {
    switch (severity) {
      case 'critical': return <ShieldAlert className="w-3.5 h-3.5 mr-1.5 text-red-400 flex-shrink-0" />;
      case 'warning': return <AlertTriangle className="w-3.5 h-3.5 mr-1.5 text-amber-400 flex-shrink-0" />;
      default: return <Info className="w-3.5 h-3.5 mr-1.5 text-cyan-400 flex-shrink-0" />;
    }
  };

  return (
    <div className="group w-full overflow-hidden backdrop-blur-md bg-slate-900/80 border-y border-white/10 py-2.5 relative flex items-center shadow-lg select-none">
      {/* Live Badge */}
      <div className="absolute left-4 z-20 hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-red-500/20 border border-red-500/40 text-red-400 text-[11px] font-bold tracking-wide uppercase">
        <Radio className="w-3 h-3 animate-pulse" /> Live Telemetry Feed
      </div>

      {/* Edge Gradient Masks for Smooth In/Out */}
      <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-slate-950 via-slate-950/80 to-transparent z-10 pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-slate-950 via-slate-950/80 to-transparent z-10 pointer-events-none" />
      
      <div 
        className="flex whitespace-nowrap animate-marquee group-hover:[animation-play-state:paused] cursor-pointer"
        style={{ willChange: 'transform' }}
      >
        {/* Tripled list for ultra-smooth seamless looping across all screen widths */}
        {[...alerts, ...alerts, ...alerts].map((alert, i) => (
          <div 
            key={`${alert.id}-${i}`}
            onClick={() => onSelectAlert && onSelectAlert(alert)}
            className={`inline-flex items-center px-3.5 py-1 mx-2.5 rounded-full border text-xs font-medium transition-all ${getSeverityStyles(alert.severity)}`}
          >
            {alert.severity === 'critical' && (
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping mr-2" />
            )}
            {getIcon(alert.severity)}
            <span className="font-bold text-white mr-1.5">{alert.area}:</span>
            <span className="opacity-90">{alert.message}</span>
            <span className="ml-2.5 text-[10px] opacity-60 font-mono">
              {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
