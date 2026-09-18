import React, { useState } from 'react';
import SensorCoverage3D from '../components/3d/SensorCoverage3D';
import GlassCard from '../components/ui/GlassCard';
import { useSensorNetwork } from '../hooks/useSensorNetwork';
import { Layers, Maximize, MapPin, Activity } from 'lucide-react';

export default function SensorMap3D() {
  const { sensors, loading } = useSensorNetwork();
  const [activePollutant, setActivePollutant] = useState('pm25');
  const [showRange, setShowRange] = useState(true);
  const [selectedSensor, setSelectedSensor] = useState(null);

  return (
    <div className="absolute inset-0 overflow-hidden bg-slate-950">
      {/* 3D Canvas Background */}
      <div className="absolute inset-0">
        {!loading && (
          <SensorCoverage3D 
            sensors={sensors} 
            activePollutant={activePollutant}
            showRange={showRange}
            onSensorClick={setSelectedSensor}
          />
        )}
      </div>

      {/* Overlay UI - Top Left Controls */}
      <div className="absolute top-6 left-6 z-10 w-80 space-y-4">
        <GlassCard className="p-4 backdrop-blur-xl bg-slate-900/60 border-white/10">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Layers className="w-5 h-5 text-cyan-400" /> Layer Controls
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="text-xs text-slate-400 mb-2 block uppercase tracking-wider">Active Pollutant</label>
              <div className="grid grid-cols-3 gap-2">
                {['pm25', 'pm10', 'no2', 'o3', 'so2', 'co'].map(p => (
                  <button
                    key={p}
                    onClick={() => setActivePollutant(p)}
                    className={`px-2 py-1.5 rounded text-xs font-medium transition-colors ${
                      activePollutant === p ? 'bg-cyan-500 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                    }`}
                  >
                    {p.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="pt-4 border-t border-white/10 flex items-center justify-between">
              <span className="text-sm text-slate-300">Show Prediction Radius</span>
              <button 
                onClick={() => setShowRange(!showRange)}
                className={`w-12 h-6 rounded-full relative transition-colors ${showRange ? 'bg-cyan-500' : 'bg-slate-700'}`}
              >
                <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${showRange ? 'left-7' : 'left-1'}`} />
              </button>
            </div>
          </div>
        </GlassCard>

        {/* Selected Sensor Info */}
        {selectedSensor && (
          <GlassCard className="p-4 backdrop-blur-xl bg-slate-900/80 border-cyan-500/30 shadow-[0_0_20px_rgba(6,182,212,0.1)]">
            <div className="flex justify-between items-start mb-4">
              <h3 className="font-bold text-white text-lg flex items-center gap-2">
                <MapPin className="w-4 h-4 text-cyan-400" />
                {selectedSensor.name}
              </h3>
              <button onClick={() => setSelectedSensor(null)} className="text-slate-400 hover:text-white">&times;</button>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-slate-800/50 p-3 rounded-lg">
                <div className="text-xs text-slate-400 mb-1">PM2.5</div>
                <div className={`text-xl font-bold ${selectedSensor.pm25 > 150 ? 'text-red-400' : 'text-green-400'}`}>
                  {selectedSensor.pm25}
                </div>
              </div>
              <div className="bg-slate-800/50 p-3 rounded-lg">
                <div className="text-xs text-slate-400 mb-1">Status</div>
                <div className="text-sm font-medium text-slate-200 capitalize flex items-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${selectedSensor.status === 'active' ? 'bg-green-500' : 'bg-amber-500'}`} />
                  {selectedSensor.status}
                </div>
              </div>
            </div>
            <button className="w-full py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors flex items-center justify-center gap-2">
              <Activity className="w-4 h-4" /> View Detailed Telemetry
            </button>
          </GlassCard>
        )}
      </div>

      {/* Legend - Bottom Right */}
      <div className="absolute bottom-6 right-6 z-10 pointer-events-none">
        <GlassCard className="p-4 backdrop-blur-xl bg-slate-900/60 border-white/10">
          <h4 className="text-xs text-slate-400 mb-3 uppercase tracking-wider">Severity Scale</h4>
          <div className="space-y-2 text-sm text-slate-300">
            <div className="flex items-center gap-3"><div className="w-3 h-3 rounded-full bg-red-500" /> Critical (&gt;150)</div>
            <div className="flex items-center gap-3"><div className="w-3 h-3 rounded-full bg-orange-500" /> Very High</div>
            <div className="flex items-center gap-3"><div className="w-3 h-3 rounded-full bg-amber-500" /> High</div>
            <div className="flex items-center gap-3"><div className="w-3 h-3 rounded-full bg-green-500" /> Moderate/Low</div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
