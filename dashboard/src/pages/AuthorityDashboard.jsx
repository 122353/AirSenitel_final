import React, { useState, useEffect } from 'react';
import MetricCard from '../components/ui/MetricCard';
import AlertBanner from '../components/ui/AlertBanner';
import LivePollutantChart from '../components/charts/LivePollutantChart';
import ForecastChart from '../components/charts/ForecastChart';
import AnomalyTimeline from '../components/charts/AnomalyTimeline';
import AuthorityLoginModal from '../components/auth/AuthorityLoginModal';
import CaseDispatchModal from '../components/cases/CaseDispatchModal';
import { useLiveData } from '../hooks/useLiveData';
import { Briefcase, AlertOctagon, Target, Clock, ShieldCheck, UserCheck, LogOut, ChevronRight, Building } from 'lucide-react';

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
  const [activeTab, setActiveTab] = useState('system'); // 'system' or 'citizen'

  useEffect(() => {
    const stored = sessionStorage.getItem('airsentinel_auth_user');
    if (stored) {
      try {
        setCurrentUser(JSON.parse(stored));
      } catch (e) {}
    } else {
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

    fetch('/api/v1/reports')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setCitizenReports(data);
        } else {
          const cached = JSON.parse(localStorage.getItem('airsentinel_citizen_reports') || '[]');
          setCitizenReports(cached);
        }
      })
      .catch(() => {
        const cached = JSON.parse(localStorage.getItem('airsentinel_citizen_reports') || '[]');
        setCitizenReports(cached);
      });
  }, []);

  const handleCaseClick = (c) => {
    setSelectedCase(c);
    setIsDispatchModalOpen(true);
  };

  const handleCitizenReportClick = (rep) => {
    const mapped = {
      id: rep.report_id,
      area: rep.location || rep.locality_id,
      category: 'Citizen Report',
      type: 'citizen_report',
      observation: rep.observation || rep.report_text,
      time: rep.timestamp_utc ? new Date(rep.timestamp_utc).toLocaleTimeString() : new Date().toLocaleTimeString(),
      observed_pm25: 180
    };
    setSelectedCase(mapped);
    setIsDispatchModalOpen(true);
  };

  const handleDispatchSuccess = (updatedCase) => {
    if (updatedCase.type === 'citizen_report') {
      // In a real app we'd update the report status
      setIsDispatchModalOpen(false);
    } else {
      setCases(prev => prev.map(item => item.id === updatedCase.id ? updatedCase : item));
      setIsDispatchModalOpen(false);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem('airsentinel_auth_user');
    setCurrentUser(null);
    setIsLoginModalOpen(true);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-[#0c1729] border-b border-[#1a3055] -mx-6 -mt-6 px-6 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded bg-[#0ea5e9]/10 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-[#0ea5e9]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-[#f0f6ff] uppercase tracking-wider">
                AirSentinel Authority Command
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e] animate-pulse" />
              <span className="text-[11px] text-[#22c55e] font-medium">Encrypted Live Session</span>
            </div>
            <p className="text-xs text-[#7aa2cc]">
              {currentUser ? `${currentUser.agency} • ${currentUser.name} (${currentUser.officer_id})` : 'Guest Mode (Read-only)'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {currentUser ? (
            <div className="flex items-center gap-2">
              <span className="hidden sm:inline-block text-xs px-2.5 py-1 rounded bg-[#0ea5e9]/10 text-[#0ea5e9] font-mono border border-[#0ea5e9]/30">
                {currentUser.badge}
              </span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 text-xs text-[#7aa2cc] hover:text-[#ef4444] px-3 py-1.5 rounded-lg border border-[#1a3055] hover:border-[#ef4444]/30 transition-all"
              >
                <LogOut className="w-3.5 h-3.5" /> Switch Role
              </button>
            </div>
          ) : (
            <button
              onClick={() => setIsLoginModalOpen(true)}
              className="flex items-center gap-2 text-xs font-bold bg-[#0ea5e9] text-[#060d1a] px-4 py-2 rounded-lg transition-all hover:opacity-90"
            >
              <UserCheck className="w-3.5 h-3.5" /> Officer Login
            </button>
          )}
        </div>
      </div>

      <header>
        <h1 className="text-2xl font-bold text-[#f0f6ff] mb-1">Central Authority Air Triage</h1>
        <p className="text-[#7aa2cc] text-sm">Delhi NCR Regional Air Quality Enforcement & AI Root-Cause Attribution</p>
      </header>

      {/* Smooth Marquee Alert Banner */}
      <div className="mb-6 overflow-hidden">
        <AlertBanner alerts={MOCK_ALERTS} onSelectAlert={() => {}} />
      </div>

      {/* KPI Metric Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="Active Enforcement Cases" value={cases.filter(c => c.status !== 'resolved').length} trend={12} icon={Briefcase} color="amber" />
        <MetricCard title="Predicted Spikes (Next 4h)" value={3} trend={-2} icon={AlertOctagon} color="red" />
        <MetricCard title="Physical Sensor Radius" value="1.5 km" subtitle="True dispersion limit enforced" icon={Target} color="green" />
        <MetricCard title="Intervention Lead Time" value="2.5h" subtitle="Faster than 24h rolling AQI" icon={Clock} color="teal" />
      </div>

      {/* Main Tabbed Area */}
      <div className="bg-[#0c1729] border border-[#1a3055] rounded-xl overflow-hidden">
        <div className="flex border-b border-[#1a3055]">
          <button 
            className={`flex-1 py-4 text-sm font-bold transition-colors ${activeTab === 'system' ? 'text-[#0ea5e9] border-b-2 border-[#0ea5e9]' : 'text-[#7aa2cc] hover:text-[#f0f6ff]'}`}
            onClick={() => setActiveTab('system')}
          >
            System Detected Cases
          </button>
          <button 
            className={`flex-1 py-4 text-sm font-bold transition-colors ${activeTab === 'citizen' ? 'text-[#0ea5e9] border-b-2 border-[#0ea5e9]' : 'text-[#7aa2cc] hover:text-[#f0f6ff]'}`}
            onClick={() => setActiveTab('citizen')}
          >
            Citizen Reports
          </button>
        </div>

        <div className="p-0">
          {activeTab === 'system' && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#1a3055] text-[#7aa2cc] uppercase tracking-wider bg-[#080f1e]">
                    <th className="px-4 py-3 font-semibold">Case ID</th>
                    <th className="px-4 py-3 font-semibold">Location</th>
                    <th className="px-4 py-3 font-semibold">AI Category</th>
                    <th className="px-4 py-3 font-semibold">PM2.5</th>
                    <th className="px-4 py-3 font-semibold">Assigned Authority</th>
                    <th className="px-4 py-3 font-semibold">Status</th>
                    <th className="px-4 py-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1a3055]">
                  {cases.map(c => (
                    <tr 
                      key={c.id} 
                      className="border-b border-[#1a3055] hover:bg-[#0ea5e9]/5 transition-colors group"
                    >
                      <td className="px-4 py-3.5 font-mono text-[#0ea5e9] font-bold">{c.id}</td>
                      <td className="px-4 py-3.5 font-semibold text-[#f0f6ff]">{c.area}</td>
                      <td className="px-4 py-3.5 text-[#7aa2cc]">{c.category}</td>
                      <td className="px-4 py-3.5 text-[#ef4444] font-mono">{c.observed_pm25} µg/m³</td>
                      <td className="px-4 py-3.5">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-medium border ${
                          c.assigned_authority === 'Unassigned' 
                            ? 'border-[#ef4444]/40 bg-[#ef4444]/10 text-[#ef4444]' 
                            : 'border-[#0ea5e9]/40 bg-[#0ea5e9]/10 text-[#0ea5e9]'
                        }`}>
                          {c.assigned_authority}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={`status-badge ${
                          c.status === 'open' ? 'status-badge-red' :
                          c.status === 'in-progress' ? 'status-badge-amber' :
                          c.status === 'dispatched' ? 'status-badge-blue' :
                          'status-badge-green'
                        }`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <button 
                          onClick={() => handleCaseClick(c)}
                          className="bg-[#0ea5e9]/10 border border-[#0ea5e9]/30 text-[#0ea5e9] hover:bg-[#0ea5e9] hover:text-[#060d1a] text-xs px-3 py-1.5 rounded-lg transition-all font-medium inline-flex items-center gap-1"
                        >
                          Assign Authority <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {cases.length === 0 && (
                    <tr>
                      <td colSpan="7" className="px-4 py-8 text-center text-[#7aa2cc]">No system detected cases.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'citizen' && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#1a3055] text-[#7aa2cc] uppercase tracking-wider bg-[#080f1e]">
                    <th className="px-4 py-3 font-semibold">Report ID</th>
                    <th className="px-4 py-3 font-semibold">Location</th>
                    <th className="px-4 py-3 font-semibold">Category</th>
                    <th className="px-4 py-3 font-semibold">Observation</th>
                    <th className="px-4 py-3 font-semibold">Time</th>
                    <th className="px-4 py-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1a3055]">
                  {citizenReports.map((rep, idx) => (
                    <tr 
                      key={rep.report_id || idx} 
                      className="border-b border-[#1a3055] hover:bg-[#0ea5e9]/5 transition-colors group"
                    >
                      <td className="px-4 py-3.5 font-mono text-[#0ea5e9] font-bold">{rep.report_id || `REP-${1000+idx}`}</td>
                      <td className="px-4 py-3.5 font-semibold text-[#f0f6ff]">{rep.location || rep.locality_id}</td>
                      <td className="px-4 py-3.5 text-[#7aa2cc]">Citizen Report</td>
                      <td className="px-4 py-3.5 text-[#7aa2cc] max-w-xs truncate">{rep.observation || rep.report_text}</td>
                      <td className="px-4 py-3.5 text-[#7aa2cc]">{rep.timestamp_utc ? new Date(rep.timestamp_utc).toLocaleTimeString() : new Date().toLocaleTimeString()}</td>
                      <td className="px-4 py-3.5 text-right">
                        <button 
                          onClick={() => handleCitizenReportClick(rep)}
                          className="bg-[#0ea5e9]/10 border border-[#0ea5e9]/30 text-[#0ea5e9] hover:bg-[#0ea5e9] hover:text-[#060d1a] text-xs px-3 py-1.5 rounded-lg transition-all font-medium inline-flex items-center gap-1"
                        >
                          Review & Assign <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {citizenReports.length === 0 && (
                    <tr>
                      <td colSpan="6" className="px-4 py-8 text-center text-[#7aa2cc]">No recent citizen reports.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[400px]">
        <div className="DashCard p-4 flex flex-col h-full">
          <LivePollutantChart data={liveData} title="Network-wide Telemetry (Delhi Pilot)" />
        </div>
        <div className="DashCard p-4 flex flex-col h-full">
          <ForecastChart forecasts={MOCK_FORECAST} />
        </div>
      </div>

      {/* Bottom: AnomalyTimeline */}
      <div className="mt-6">
        <AnomalyTimeline anomalies={MOCK_ANOMALIES} />
      </div>

      <AuthorityLoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onLoginSuccess={(officer) => setCurrentUser(officer)}
      />

      <CaseDispatchModal
        isOpen={isDispatchModalOpen}
        caseData={selectedCase}
        onClose={() => setIsDispatchModalOpen(false)}
        onDispatchSuccess={handleDispatchSuccess}
      />
    </div>
  );
}
