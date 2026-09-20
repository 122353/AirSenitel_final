import React, { useState } from 'react';
import GlassCard from '../ui/GlassCard';
import { ShieldCheck, Lock, UserCheck, KeyRound, Building2, ChevronRight, X } from 'lucide-react';

const PRECONFIGURED_ROLES = [
  {
    role: 'DPCC Enforcement Officer',
    agency: 'Delhi Pollution Control Committee',
    officer_id: 'DPCC-ENV-409',
    badge: 'Industrial Inspection Wing',
    color: 'border-orange-500/40 bg-orange-500/10 text-orange-400'
  },
  {
    role: 'CPCB Regional Analyst',
    agency: 'Central Pollution Control Board',
    officer_id: 'CPCB-HQ-118',
    badge: 'National Corridor Surveillance',
    color: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-400'
  },
  {
    role: 'MCD Flying Squad Chief',
    agency: 'Municipal Corporation of Delhi',
    officer_id: 'MCD-ZONAL-092',
    badge: 'C&D and Biomass Burning Task Force',
    color: 'border-amber-500/40 bg-amber-500/10 text-amber-400'
  },
  {
    role: 'CAQM Special Observer',
    agency: 'Commission for Air Quality Management',
    officer_id: 'CAQM-NCR-005',
    badge: 'Inter-State Emergency Task Force',
    color: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
  }
];

export default function AuthorityLoginModal({ isOpen, onClose, onLoginSuccess }) {
  const [officerId, setOfficerId] = useState('');
  const [password, setPassword] = useState('');
  const [selectedAgency, setSelectedAgency] = useState('Delhi Pollution Control Committee');

  if (!isOpen) return null;

  const handleQuickLogin = (roleItem) => {
    const user = {
      officer_id: roleItem.officer_id,
      name: roleItem.role,
      agency: roleItem.agency,
      badge: roleItem.badge,
      logged_in_at: new Date().toISOString()
    };
    sessionStorage.setItem('airsentinel_auth_user', JSON.stringify(user));
    onLoginSuccess(user);
    onClose();
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    const user = {
      officer_id: officerId || 'OFFICER-771',
      name: `${selectedAgency} Officer`,
      agency: selectedAgency,
      badge: 'Authorized Enforcement Reviewer',
      logged_in_at: new Date().toISOString()
    };
    sessionStorage.setItem('airsentinel_auth_user', JSON.stringify(user));
    onLoginSuccess(user);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="relative w-full max-w-lg">
        <GlassCard className="p-7 border border-white/20 shadow-2xl">
          {/* Header */}
          <div className="flex items-start justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/30">
                <ShieldCheck className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Central Authority Portal</h2>
                <p className="text-xs text-slate-400">Restricted government air enforcement console</p>
              </div>
            </div>
            <button 
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Fast Quick-Demo Logins */}
          <div className="mb-6">
            <span className="block text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-2">
              Select Authorized Officer Role (1-Click Access)
            </span>
            <div className="grid grid-cols-1 gap-2">
              {PRECONFIGURED_ROLES.map((item) => (
                <button
                  key={item.officer_id}
                  onClick={() => handleQuickLogin(item)}
                  type="button"
                  className={`flex items-center justify-between p-3 rounded-xl border text-left transition-all hover:scale-[1.01] ${item.color}`}
                >
                  <div className="space-y-0.5">
                    <div className="text-xs font-bold flex items-center gap-2 text-white">
                      <span>{item.role}</span>
                      <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-white/10 text-slate-300">
                        {item.officer_id}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400">{item.agency} • {item.badge}</div>
                  </div>
                  <ChevronRight className="w-4 h-4 opacity-70" />
                </button>
              ))}
            </div>
          </div>

          <div className="relative flex py-2 items-center mb-5">
            <div className="flex-grow border-t border-white/10"></div>
            <span className="flex-shrink mx-3 text-[11px] text-slate-500 uppercase tracking-widest font-mono">Or Custom Credential</span>
            <div className="flex-grow border-t border-white/10"></div>
          </div>

          {/* Form */}
          <form onSubmit={handleFormSubmit} className="space-y-3.5">
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 uppercase mb-1">
                Statutory Agency
              </label>
              <select
                value={selectedAgency}
                onChange={e => setSelectedAgency(e.target.value)}
                className="w-full bg-slate-900/70 border border-white/15 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
              >
                <option value="Delhi Pollution Control Committee">Delhi Pollution Control Committee (DPCC)</option>
                <option value="Central Pollution Control Board">Central Pollution Control Board (CPCB)</option>
                <option value="Municipal Corporation of Delhi">Municipal Corporation of Delhi (MCD)</option>
                <option value="Commission for Air Quality Management">Commission for Air Quality Management (CAQM)</option>
                <option value="Delhi Traffic Police">Delhi Traffic Police (Green Corridor Unit)</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-300 uppercase mb-1">
                  Badge / Officer ID
                </label>
                <input
                  type="text"
                  placeholder="e.g. DPCC-891"
                  value={officerId}
                  onChange={e => setOfficerId(e.target.value)}
                  className="w-full bg-slate-900/70 border border-white/15 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-300 uppercase mb-1">
                  Access Key
                </label>
                <input
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full bg-slate-900/70 border border-white/15 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 mt-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-cyan-500/25 transition-all flex items-center justify-center gap-2"
            >
              <UserCheck className="w-3.5 h-3.5" /> Authenticate & Access Authority Console
            </button>
          </form>
        </GlassCard>
      </div>
    </div>
  );
}
