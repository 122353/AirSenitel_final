import React from 'react';
import PollutantColumns from '../components/3d/PollutantColumns';
import GlassCard from '../components/ui/GlassCard';
import MetricCard from '../components/ui/MetricCard';
import { Wind, Navigation } from 'lucide-react';

const CITIES = [
  { name: 'Delhi', pm25: 185, risk: 'Critical', action: 'Red Alert Declared', temp: 32, humidity: 45 },
  { name: 'Mumbai', pm25: 85, risk: 'Moderate', action: 'Standard Monitoring', temp: 29, humidity: 75 },
  { name: 'Kolkata', pm25: 142, risk: 'High', action: 'Industrial Advisory', temp: 34, humidity: 80 },
  { name: 'Chennai', pm25: 45, risk: 'Low', action: 'None', temp: 31, humidity: 65 },
  { name: 'Bangalore', pm25: 65, risk: 'Moderate', action: 'Traffic Diversion Pilot', temp: 26, humidity: 55 },
  { name: 'Hyderabad', pm25: 90, risk: 'High', action: 'Construction Ban', temp: 30, humidity: 40 },
  { name: 'Ahmedabad', pm25: 110, risk: 'High', action: 'Dust Control Active', temp: 36, humidity: 30 },
  { name: 'Pune', pm25: 75, risk: 'Moderate', action: 'Standard Monitoring', temp: 28, humidity: 60 },
];

export default function NationalOverview() {
  return (
    <div className="space-y-6 flex flex-col h-[calc(100vh-3rem)]">
      <header className="mb-2">
        <h1 className="text-3xl font-bold text-white mb-2">National Overview</h1>
        <p className="text-slate-400">Macro-level analysis across major economic corridors</p>
      </header>

      {/* Top 3D View */}
      <div className="relative w-full h-[40vh] rounded-2xl overflow-hidden border border-white/10 shadow-2xl">
        <PollutantColumns cities={CITIES} />
        
        {/* Overlay Label */}
        <div className="absolute top-4 left-4 pointer-events-none">
          <GlassCard className="px-4 py-2 backdrop-blur-md bg-slate-900/50">
            <h3 className="font-semibold text-white flex items-center gap-2">
              <Navigation className="w-4 h-4 text-cyan-400" /> Relative PM2.5 Volumes
            </h3>
          </GlassCard>
        </div>
      </div>

      {/* City Cards Grid */}
      <div className="flex-1 overflow-y-auto pr-2 pb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {CITIES.map(city => (
            <GlassCard key={city.name} className="p-4" hover glow={city.risk === 'Critical' ? 'red' : ''}>
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-bold text-white">{city.name}</h3>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  city.risk === 'Critical' ? 'bg-red-500/20 text-red-400' :
                  city.risk === 'High' ? 'bg-orange-500/20 text-orange-400' :
                  city.risk === 'Moderate' ? 'bg-amber-500/20 text-amber-400' :
                  'bg-green-500/20 text-green-400'
                }`}>
                  {city.risk}
                </span>
              </div>
              
              <div className="mb-4">
                <div className="text-3xl font-bold text-white mb-1">{city.pm25} <span className="text-sm font-normal text-slate-500">µg/m³</span></div>
                <div className="text-xs text-slate-400 line-clamp-1">Action: <span className="text-slate-300">{city.action}</span></div>
              </div>
              
              <div className="flex items-center justify-between pt-3 border-t border-white/10 text-xs text-slate-400">
                <div className="flex items-center gap-1">
                  <Wind className="w-3 h-3 text-cyan-400" /> {city.temp}°C
                </div>
                <div>Humidity: {city.humidity}%</div>
              </div>
            </GlassCard>
          ))}
        </div>
      </div>
    </div>
  );
}
