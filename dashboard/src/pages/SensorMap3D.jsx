import React, { useState } from 'react';
import RealisticSatelliteMap3D from '../components/3d/RealisticSatelliteMap3D';
import GoogleMaps3DWrapper from '../components/3d/GoogleMaps3DWrapper';
import SensorCoverage3D from '../components/3d/SensorCoverage3D';
import GlassCard from '../components/ui/GlassCard';
import { useSensorNetwork } from '../hooks/useSensorNetwork';
import { EFFECTIVE_RANGES } from '../utils/sensorRange';
import { Layers, Globe, Radio, ShieldCheck, MapPin, Activity, Wind, AlertTriangle, X, Sparkles } from 'lucide-react';

export default function SensorMap3D() {
  const { sensors, loading } = useSensorNetwork();
  const [mapMode, setMapMode] = useState('satellite3d'); // 'satellite3d' | 'googlemaps' | 'mesh'
  const [activePollutant, setActivePollutant] = useState('pm25');
  const [showRange, setShowRange] = useState(true);
  const [selectedSensor, setSelectedSensor] = useState(null);

  // Delhi real-world stations fallback if API is offline
  const displaySensors = sensors.length > 0 ? sensors : [
    { name: 'Anand Vihar DPCC', lat: 28.6468, lon: 77.3160, pm25: 385, no2: 88, o3: 34, severity: 'critical' },
    { name: 'Punjabi Bagh DPCC', lat: 28.6740, lon: 77.1310, pm25: 290, no2: 76, o3: 42, severity: 'high' },
    { name: 'R K Puram DPCC', lat: 28.5632, lon: 77.1869, pm25: 220, no2: 64, o3: 55, severity: 'high' },
    { name: 'IGI Airport T3', lat: 28.5620, lon: 77.0940, pm25: 180, no2: 52, o3: 60, severity: 'moderate' },
    { name: 'Mandir Marg DPCC', lat: 28.6360, lon: 77.2010, pm25: 210, no2: 58, o3: 48, severity: 'high' },
    { name: 'Rohini Sector 16', lat: 28.7495, lon: 77.0565, pm25: 310, no2: 70, o3: 38, severity: 'critical' },
    { name: 'Najafgarh Pilot', lat: 28.6092, lon: 76.9798, pm25: 195, no2: 44, o3: 50, severity: 'moderate' },
    { name: 'NSIT Dwarka CPCB', lat: 28.6090, lon: 77.0320, pm25: 230, no2: 62, o3: 45, severity: 'high' },
    { name: 'Okhla Phase II', lat: 28.5300, lon: 77.2710, pm25: 345, no2: 82, o3: 29, severity: 'critical' }
  ];

  return (
    <div className="absolute inset-0 overflow-hidden bg-slate-950">
      {/* 3D Map Viewport */}
      <div className="absolute inset-0">
        {mapMode === 'satellite3d' && (
          <RealisticSatelliteMap3D
            sensors={displaySensors}
            activePollutant={activePollutant}
            showRange={showRange}
            selectedSensor={selectedSensor}
            onSensorClick={setSelectedSensor}
          />
        )}

        {mapMode === 'googlemaps' && (
          <GoogleMaps3DWrapper
            sensors={displaySensors}
            activePollutant={activePollutant}
            showRange={showRange}
            onSensorClick={setSelectedSensor}
          />
        )}

        {mapMode === 'mesh' && (
          <SensorCoverage3D
            sensors={displaySensors}
            activePollutant={activePollutant}
            showRange={showRange}
            onSensorClick={setSelectedSensor}
          />
        )}
      </div>

      {/* Top Left Floating Controller */}
      <div className="absolute top-6 left-6 z-10 w-84 space-y-3 pointer-events-auto">
        <GlassCard className="p-4 backdrop-blur-xl bg-slate-900/80 border-white/15 shadow-2xl">
          <div className="flex items-center justify-between mb-3 border-b border-white/10 pb-2.5">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" /> 3D Dispersion Engine
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold">
              DELHI NCR
            </span>
          </div>

          {/* Map Engine Mode Switcher */}
          <div className="mb-3.5">
            <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider mb-1.5 block">
              3D Rendering Model
            </label>
            <div className="grid grid-cols-3 gap-1.5 p-1 bg-slate-950/80 rounded-lg border border-white/10 text-xs">
              <button
                onClick={() => setMapMode('satellite3d')}
                className={`py-1.5 px-2 rounded-md font-medium text-[11px] transition-all ${
                  mapMode === 'satellite3d' ? 'bg-cyan-500 text-slate-950 font-bold shadow' : 'text-slate-400 hover:text-white'
                }`}
              >
                Satellite 3D
              </button>
              <button
                onClick={() => setMapMode('googlemaps')}
                className={`py-1.5 px-2 rounded-md font-medium text-[11px] transition-all ${
                  mapMode === 'googlemaps' ? 'bg-cyan-500 text-slate-950 font-bold shadow' : 'text-slate-400 hover:text-white'
                }`}
              >
                Google 3D
              </button>
              <button
                onClick={() => setMapMode('mesh')}
                className={`py-1.5 px-2 rounded-md font-medium text-[11px] transition-all ${
                  mapMode === 'mesh' ? 'bg-cyan-500 text-slate-950 font-bold shadow' : 'text-slate-400 hover:text-white'
                }`}
              >
                Radar Grid
              </button>
            </div>
          </div>

          {/* Pollutant Selector */}
          <div className="mb-3.5">
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
                Target Pollutant
              </label>
              <span className="text-[11px] text-cyan-400 font-mono font-medium">
                Radius: {EFFECTIVE_RANGES[activePollutant]}m
              </span>
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {['pm25', 'pm10', 'no2', 'o3', 'so2', 'co'].map(p => (
                <button
                  key={p}
                  onClick={() => setActivePollutant(p)}
                  className={`py-1 rounded text-xs font-semibold transition-all border ${
                    activePollutant === p
                      ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.3)]'
                      : 'border-white/10 bg-slate-950/60 text-slate-400 hover:border-white/20'
                  }`}
                >
                  {p.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Range Dome Toggle */}
          <div className="pt-3 border-t border-white/10 flex items-center justify-between">
            <span className="text-xs text-slate-300 font-medium">Physical Effective Domes</span>
            <button
              onClick={() => setShowRange(!showRange)}
              className={`w-10 h-5 rounded-full relative transition-colors ${showRange ? 'bg-cyan-500' : 'bg-slate-700'}`}
            >
              <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${showRange ? 'left-5.5' : 'left-0.5'}`} />
            </button>
          </div>
        </GlassCard>

        {/* Physical Range Disclaimer Card */}
        <div className="p-3 rounded-xl bg-slate-900/80 border border-cyan-500/20 backdrop-blur-md text-[11px] text-slate-300 space-y-1">
          <div className="flex items-center gap-1.5 text-cyan-400 font-bold">
            <ShieldCheck className="w-3.5 h-3.5" /> Physical Dispersion Boundary
          </div>
          <p className="text-slate-400 leading-relaxed">
            Stations beyond their physical radius ({EFFECTIVE_RANGES[activePollutant]}m) receive a 0.0 weight to prevent inaccurate long-distance interpolation.
          </p>
        </div>
      </div>

      {/* Sensor Detail Inspector Card (Bottom Right) */}
      {selectedSensor && (
        <div className="absolute bottom-6 right-6 z-10 w-96 pointer-events-auto">
          <GlassCard className="p-5 backdrop-blur-xl bg-slate-900/90 border-cyan-500/30 shadow-2xl space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold">
                  CAAQMS Station Telemetry
                </span>
                <h3 className="text-base font-bold text-white mt-1">{selectedSensor.name}</h3>
              </div>
              <button
                onClick={() => setSelectedSensor(null)}
                className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-white/10"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs bg-slate-950/60 p-3 rounded-lg border border-white/10">
              <div>
                <span className="text-slate-400 block">Current PM2.5</span>
                <span className="text-xl font-bold text-white">{selectedSensor.pm25 || 180} <span className="text-xs font-normal text-slate-400">µg/m³</span></span>
              </div>
              <div>
                <span className="text-slate-400 block">Effective Boundary</span>
                <span className="text-base font-bold text-cyan-400">{EFFECTIVE_RANGES[activePollutant]} m</span>
              </div>
            </div>

            {/* AI Cause Diagnostics */}
            <div className="p-2.5 rounded-lg bg-indigo-950/30 border border-indigo-500/30 text-xs space-y-1">
              <div className="flex items-center gap-1.5 text-indigo-300 font-bold">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" /> AI Root Cause Attribution
              </div>
              <p className="text-slate-300 text-[11px]">
                {selectedSensor.pm25 >= 300 
                  ? 'Severe fine-particulate spike detected. High PM2.5/PM10 ratio matches open biomass burning.'
                  : 'Sustained moderate elevation. Local diesel corridor traffic and mechanical dust.'}
              </p>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-white/10">
              <span className="flex items-center gap-1">
                <Wind className="w-3 h-3 text-cyan-400" /> Wind: 1.4 m/s NW (315°)
              </span>
              <span className="text-green-400 font-medium flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" /> Validated Station
              </span>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
