import React from 'react';
import { AlertTriangle, Info, ShieldAlert } from 'lucide-react';

export default function AlertBanner({ alerts = [] }) {
  if (!alerts || alerts.length === 0) return null;

  const getSeverityStyles = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-500/20 text-red-300 border-red-500/50';
      case 'warning': return 'bg-amber-500/20 text-amber-300 border-amber-500/50';
      default: return 'bg-blue-500/20 text-blue-300 border-blue-500/50';
    }
  };

  const getIcon = (severity) => {
    switch (severity) {
      case 'critical': return <ShieldAlert className="w-4 h-4 mr-2" />;
      case 'warning': return <AlertTriangle className="w-4 h-4 mr-2" />;
      default: return <Info className="w-4 h-4 mr-2" />;
    }
  };

  return (
    <div className="w-full overflow-hidden backdrop-blur-md bg-slate-900/60 border-y border-white/10 py-2 relative flex items-center">
      <div className="absolute left-0 top-0 bottom-0 w-16 bg-gradient-to-r from-slate-900 to-transparent z-10" />
      <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-slate-900 to-transparent z-10" />
      
      <div className="flex whitespace-nowrap animate-marquee">
        {/* Duplicate the list for seamless looping */}
        {[...alerts, ...alerts].map((alert, i) => (
          <div 
            key={`${alert.id}-${i}`}
            className={`inline-flex items-center px-4 py-1 mx-3 rounded-full border text-sm cursor-pointer hover:bg-opacity-40 transition-colors ${getSeverityStyles(alert.severity)}`}
          >
            {alert.severity === 'critical' && <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse-ring mr-2" />}
            {getIcon(alert.severity)}
            <span className="font-semibold mr-2">{alert.area}:</span>
            <span>{alert.message}</span>
            <span className="ml-3 text-xs opacity-70">{new Date(alert.timestamp).toLocaleTimeString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
