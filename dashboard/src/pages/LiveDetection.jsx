import React from 'react';
import { useSensorNetwork } from '../hooks/useSensorNetwork';
import { useLiveData } from '../hooks/useLiveData';
import GlassCard from '../components/ui/GlassCard';
import LivePollutantChart from '../components/charts/LivePollutantChart';
import { Activity, Radio } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function LiveDetection() {
  const { sensors, loading } = useSensorNetwork();
  const { data: liveData } = useLiveData();

  return (
    <div className="space-y-6">
      <header className="mb-6 flex justify-between items-end">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
            </div>
            <h1 className="text-3xl font-bold text-white">Live Detection Feed</h1>
          </div>
          <p className="text-slate-400">High-frequency real-time stream from Delhi IoT network</p>
        </div>
        <div className="flex items-center gap-2 bg-white/5 border border-white/10 px-4 py-2 rounded-lg text-sm text-slate-300">
          <Activity className="w-4 h-4 text-green-400" /> System Polling at 3s intervals
        </div>
      </header>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left Column: Network Stats & Sensor Grid */}
        <div className="xl:col-span-2 space-y-6">
          <GlassCard className="p-0 overflow-hidden h-64">
             <LivePollutantChart data={liveData} title="Aggregate Network Readings" />
          </GlassCard>

          <h2 className="text-xl font-semibold text-white mt-8 mb-4 flex items-center gap-2">
            <Radio className="w-5 h-5 text-cyan-400" /> Active Edge Nodes
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {loading ? (
              <div className="col-span-full py-12 text-center text-slate-500">Connecting to sensor network...</div>
            ) : (
              sensors.map((sensor, i) => (
                <motion.div 
                  key={sensor.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <GlassCard hover className="p-4 relative overflow-hidden group">
                    <div className="flex justify-between items-start mb-3">
                      <h3 className="font-medium text-white truncate pr-4">{sensor.name}</h3>
                      <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${sensor.status === 'active' ? 'bg-green-500' : 'bg-amber-500'}`} />
                    </div>
                    
                    <div className="flex items-end justify-between">
                      <div>
                        <div className="text-xs text-slate-500 mb-1">PM2.5</div>
                        <div className={`text-2xl font-bold ${
                          sensor.severity === 'critical' ? 'text-red-500' :
                          sensor.severity === 'very_high' ? 'text-orange-500' :
                          sensor.severity === 'high' ? 'text-amber-500' : 'text-green-500'
                        }`}>
                          {sensor.pm25} <span className="text-xs font-normal opacity-70">µg/m³</span>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-slate-500 mb-1">NO2</div>
                        <div className="text-lg font-semibold text-slate-300">{sensor.no2}</div>
                      </div>
                    </div>
                    
                    {/* Background severity glow */}
                    <div className={`absolute -right-4 -bottom-4 w-16 h-16 rounded-full blur-2xl opacity-20 ${
                      sensor.severity === 'critical' ? 'bg-red-500' : 'bg-transparent'
                    }`} />
                  </GlassCard>
                </motion.div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Live Event Stream */}
        <div className="xl:col-span-1">
          <GlassCard className="p-5 h-[calc(100vh-140px)] flex flex-col">
            <h3 className="font-semibold text-lg text-slate-100 mb-4 flex items-center justify-between">
              Event Stream
              <span className="text-xs bg-slate-800 px-2 py-1 rounded text-cyan-400">Live</span>
            </h3>
            
            <div className="flex-1 overflow-y-auto pr-2 space-y-4">
              <AnimatePresence>
                {[...sensors].sort((a,b) => b.pm25 - a.pm25).slice(0, 5).map((sensor, i) => (
                  <motion.div
                    key={`${sensor.id}-${sensor.pm25}`}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition-colors"
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-sm font-medium text-slate-200">{sensor.name}</span>
                      <span className="text-xs text-slate-500">Just now</span>
                    </div>
                    {sensor.pm25 > 150 ? (
                      <p className="text-sm text-red-400">Severe spike detected: PM2.5 at {sensor.pm25}</p>
                    ) : (
                      <p className="text-sm text-slate-400">Normal telemetry received. PM2.5: {sensor.pm25}</p>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
