import React, { useState, useEffect } from 'react';
import MetricCard from '../components/ui/MetricCard';
import AlertBanner from '../components/ui/AlertBanner';
import LivePollutantChart from '../components/charts/LivePollutantChart';
import ForecastChart from '../components/charts/ForecastChart';
import AnomalyTimeline from '../components/charts/AnomalyTimeline';
import GlassCard from '../components/ui/GlassCard';
import AuthorityLoginModal from '../components/auth/AuthorityLoginModal';
import CaseDispatchModal from '../components/cases/CaseDispatchModal';
import { useLiveData } from '../hooks/useLiveData';
import { Briefcase, AlertOctagon, Target, Clock, ShieldCheck, UserCheck, LogOut, ChevronRight, CheckCircle, MessageSquare, Send, Building } from 'lucide-react';

const MOCK_ALERTS = [
  { id: 1, severity: 'critical', area: 'Anand Vihar', message: 'PM2.5 spike exceeded 380 µg/m³. DPCC mist cannons deployed.', timestamp: Date.now() },
  { id: 2, severity: 'warning', area: 'Punjabi Bagh', message: 'Predicted NO2 accumulation along Rohtak corridor in 2 hours.', timestamp: Date.now() - 1000 * 60 * 15 },
  { id: 3, severity: 'critical', area: 'Bawana Sector 3', message: 'Industrial boiler SO2 anomaly detected. Assigned to DPCC.', timestamp: Date.now() - 1000 * 60 * 30 },
  { id: 4, severity: 'info', area: 'Dwarka Sector 10', message: 'Citizen report corroborates road dust near metro station.', timestamp: Date.now() - 1000 * 60 * 45 }
];

const MOCK_FORECAST = Array.from({ length: 12 }).map((_, i) => ({
  timestamp: new Date(Date.now() - (11 - i) * 3600000).toISOString(),
  observed: i < 8 ? 60 + Math.random() * 40 + Math.sin(i) * 20 : null,
  predicted: 65 + Math.random() * 30 + Math.sin(i) * 20,
  interval_low: 50 + Math.sin(i) * 15,
  interval_high: 95 + Math.sin(i) * 25
}));

const INITIAL_CASES = [
  { 
    id: 'CAS-8892', 
    area: 'Okhla Phase II', 
    category: 'Industrial Point Source', 
    severity: 'critical', 
    status: 'open', 
    assigned_authority: 'Unassigned',
    time: '10 mins ago',
    observed_pm25: 340
  },
  { 
    id: 'CAS-8891', 
    area: 'Bawana Sector 3', 
    category: 'Biomass / Waste Burning', 
    severity: 'high', 
    status: 'in-progress', 
    assigned_authority: 'Municipal Corporation of Delhi (MCD)',
    time: '1 hour ago',
    observed_pm25: 265
  },
  { 
    id: 'CAS-8888', 
    area: 'Ashok Vihar', 
    category: 'C&D Mechanical Dust', 
    severity: 'moderate', 
    status: 'dispatched', 
    assigned_authority: 'MCD Anti-Smog Unit',
    time: '3 hours ago',
    observed_pm25: 190
  },
  {
    id: 'CAS-8885',
    area: 'Anand Vihar ISBT',
    category: 'Vehicular Corridor Congestion',
    severity: 'critical',
    status: 'under inspection',
    assigned_authority: 'Delhi Traffic Police',
    time: '4 hours ago',
    observed_pm25: 395
  }
];

const MOCK_ANOMALIES = [
  { id: 1, type: 'Unexplained PM2.5 Spike', severity: 'critical', area: 'Okhla Industrial Estate', timestamp: Date.now() - 1000 * 60 * 10, description: 'Rapid increase from 120 to 350 µg/m³ in 15 mins. High PM2.5/PM10 ratio confirms combustion.', action: 'Dispatched DPCC enforcement team' },
  { id: 2, type: 'NO2 Pattern Anomaly', severity: 'warning', area: 'ITO Junction', timestamp: Date.now() - 1000 * 60 * 45, description: 'Sustained NO2 elevation (88 µg/m³) matching diesel truck idling.', action: 'Diverted traffic to Ring Road' }
];

export default function AuthorityDashboard() {
  const { data: liveData } = useLiveData();
  const [currentUser, setCurrentUser] = useState(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [selectedCase, setSelectedCase] = useState(null);
  const [isDispatchModalOpen, setIsDispatchModalOpen] = useState(false);
  const [cases, setCases] = useState(INITIAL_CASES);
  const [citizenReports, setCitizenReports] = useState([]);

  // Check stored login session on mount
  useEffect(() => {
    const stored = sessionStorage.getItem('airsentinel_auth_user');
    if (stored) {
      try {
        setCurrentUser(JSON.parse(stored));
      } catch (e) {}
    } else {
      // Default to DPCC demo officer for immediate usability
      const defaultOfficer = {
        officer_id: 'DPCC-ENV-409',
        name: 'DPCC Enforcement Officer',
        agency: 'Delhi Pollution Control Committee',
        badge: 'Industrial Inspection Wing',
        logged_in_at: new Date().toISOString()
      };
      setCurrentUser(defaultOfficer);
      sessionStorage.setItem('airsentinel_auth_user', JSON.stringify(defaultOfficer));
    }

    // Load cases from backend if available
    fetch('/api/v1/cases')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          const mapped = data.slice(0, 8).map(c => ({
            id: c.case_id || `CAS-${Math.floor(1000 + Math.random() * 9000)}`,
            area: c.area_name || 'Delhi Locality',
            category: c.case_category || 'Industrial Spike',
            severity: (c.anomaly_score && c.anomaly_score > 2) ? 'critical' : 'high',
            status: c.review_state || 'open',
            assigned_authority: c.assigned_authority || 'Unassigned',
            time: 'Active',
            observed_pm25: c.observed_pm25 || 220
          }));
          setCases(mapped);
        }
      })
      .catch(() => {});

    // Load recent citizen reports
    fetch('/api/v1/reports')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setCitizenReports(data.slice(0, 4));
        } else {
          const cached = JSON.parse(localStorage.getItem('airsentinel_citizen_reports') || '[]');
          setCitizenReports(cached.slice(0, 4));
        }
      })
      .catch(() => {
        const cached = JSON.parse(localStorage.getItem('airsentinel_citizen_reports') || '[]');
        setCitizenReports(cached.slice(0, 4));
      });
  }, []);

  const handleCaseClick = (c) => {
    setSelectedCase(c);
    setIsDispatchModalOpen(true);
  };

  const handleDispatchSuccess = (updatedCase) => {
    setCases(prev => prev.map(item => item.id === updatedCase.id ? updatedCase : item));
  };

  const handleLogout = () => {
    sessionStorage.removeItem('airsentinel_auth_user');
    setCurrentUser(null);
    setIsLoginModalOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Top Officer Authentication Badge Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-slate-900/70 border border-white/10 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-md shadow-cyan-500/20">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                AirSentinel Authority Command
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              <span className="text-[11px] text-green-400 font-medium">Encrypted Live Session</span>
            </div>
            <p className="text-xs text-slate-400">
              {currentUser ? `${currentUser.agency} • ${currentUser.name} (${currentUser.officer_id})` : 'Guest Mode (Read-only)'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {currentUser ? (
            <div className="flex items-center gap-2">
              <span className="hidden sm:inline-block text-xs px-2.5 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 font-mono">
                {currentUser.badge}
              </span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-red-400 px-3 py-1.5 rounded-lg border border-white/10 hover:border-red-500/30 transition-all"
              >
                <LogOut className="w-3.5 h-3.5" /> Switch Role
              </button>
            </div>
          ) : (
            <button
              onClick={() => setIsLoginModalOpen(true)}
              className="flex items-center gap-2 text-xs font-bold text-white bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2 rounded-lg shadow-md shadow-cyan-500/20 transition-all"
            >
              <UserCheck className="w-3.5 h-3.5" /> Officer Login
            </button>
          )}
        </div>
      </div>

      <header>
        <h1 className="text-3xl font-bold text-white mb-1">Central Authority Air Triage</h1>
        <p className="text-slate-400 text-sm">Delhi NCR Regional Air Quality Enforcement & AI Root-Cause Attribution</p>
      </header>

      {/* Smooth Marquee Alert Banner */}
      <div className="-mx-6 mb-6">
        <AlertBanner alerts={MOCK_ALERTS} onSelectAlert={() => setIsDispatchModalOpen(true)} />
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="Active Enforcement Cases" value={cases.filter(c => c.status !== 'resolved').length} trend={12} icon={Briefcase} color="amber" />
        <MetricCard title="Predicted Spikes (Next 4h)" value={3} trend={-2} icon={AlertOctagon} color="red" />
        <MetricCard title="Physical Sensor Radius" value="1.5 km" subtitle="True dispersion limit enforced" icon={Target} color="green" />
        <MetricCard title="Intervention Lead Time" value="2.5h" subtitle="Faster than 24h rolling AQI" icon={Clock} color="cyan" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[400px]">
        <LivePollutantChart data={liveData} title="Network-wide Telemetry (Delhi Pilot)" />
        <ForecastChart forecasts={MOCK_FORECAST} />
      </div>

      {/* Bottom Row: Live Case Queue & Anomaly Timeline */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          <GlassCard className="p-6">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
              <div>
                <h3 className="font-bold text-lg text-white flex items-center gap-2">
                  <Building className="w-5 h-5 text-cyan-400" /> Active Government Case Queue
                </h3>
                <p className="text-xs text-slate-400">Click any row to view AI root cause diagnosis and assign government authorities</p>
              </div>
              <span className="text-xs px-2.5 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 font-mono">
                {cases.length} Tracked Hotspots
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/10 text-slate-400 uppercase tracking-wider">
                    <th className="pb-3 font-semibold">Case ID</th>
                    <th className="pb-3 font-semibold">Hotspot Area</th>
                    <th className="pb-3 font-semibold">Probable Category</th>
                    <th className="pb-3 font-semibold">Assigned Authority</th>
                    <th className="pb-3 font-semibold">Status</th>
                    <th className="pb-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {cases.map(c => (
                    <tr 
                      key={c.id} 
                      onClick={() => handleCaseClick(c)}
                      className="hover:bg-white/5 transition-colors group cursor-pointer"
                    >
                      <td className="py-3.5 font-mono text-cyan-400 font-bold">{c.id}</td>
                      <td className="py-3.5 font-semibold text-white">{c.area}</td>
                      <td className="py-3.5 text-slate-300">{c.category}</td>
                      <td className="py-3.5">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-medium border ${
                          c.assigned_authority === 'Unassigned' 
                            ? 'border-red-500/40 bg-red-500/10 text-red-400' 
                            : 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300'
                        }`}>
                          {c.assigned_authority}
                        </span>
                      </td>
                      <td className="py-3.5">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                          c.status === 'open' ? 'bg-red-500/20 text-red-400' :
                          c.status === 'in-progress' ? 'bg-amber-500/20 text-amber-400' :
                          c.status === 'dispatched' ? 'bg-blue-500/20 text-blue-400' :
                          'bg-green-500/20 text-green-400'
                        }`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="py-3.5 text-right">
                        <button className="text-xs px-2.5 py-1 rounded bg-white/10 group-hover:bg-cyan-500 group-hover:text-slate-950 transition-all font-semibold inline-flex items-center gap-1">
                          Assign <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>

          {/* Incoming Citizen Telemetry Corroboration Feed */}
          {citizenReports.length > 0 && (
            <GlassCard className="p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-cyan-400" />
                  <h4 className="text-sm font-bold text-white">Live Citizen Ground Corroboration Feed</h4>
                </div>
                <span className="text-xs text-slate-400">{citizenReports.length} incoming observations</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {citizenReports.map((rep, i) => (
                  <div key={rep.report_id || i} className="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-cyan-300">{rep.location || rep.locality_id}</span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(rep.timestamp_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-slate-300 text-[11px] line-clamp-2">{rep.observation || rep.report_text}</p>
                    <div className="pt-1 flex items-center gap-2 text-[10px] text-amber-400 font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" /> Awaiting Authority Verification
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}
        </div>

        {/* Anomaly Timeline Column */}
        <div className="xl:col-span-1">
          <AnomalyTimeline anomalies={MOCK_ANOMALIES} />
        </div>
      </div>

      {/* Authority Login Modal */}
      <AuthorityLoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onLoginSuccess={(officer) => setCurrentUser(officer)}
      />

      {/* Case Government Assignment Dispatch Modal */}
      <CaseDispatchModal
        isOpen={isDispatchModalOpen}
        caseData={selectedCase}
        onClose={() => setIsDispatchModalOpen(false)}
        onDispatchSuccess={handleDispatchSuccess}
      />
    </div>
  );
}
