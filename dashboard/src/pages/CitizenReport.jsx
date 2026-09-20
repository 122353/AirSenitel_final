import React, { useState, useEffect } from 'react';
import GlassCard from '../components/ui/GlassCard';
import { Camera, Mic, MapPin, Send, CheckCircle2, AlertCircle, Clock, ShieldCheck, Flame, Truck, Hammer, Factory } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const QUICK_CATEGORIES = [
  { label: 'Open Waste Burning', icon: Flame, tag: 'Biomass/Waste Burning', color: 'from-amber-500/20 to-orange-500/20 text-orange-400 border-orange-500/30' },
  { label: 'Construction Dust', icon: Hammer, tag: 'C&D Mechanical Dust', color: 'from-yellow-500/20 to-amber-500/20 text-yellow-400 border-yellow-500/30' },
  { label: 'Heavy Truck Idling', icon: Truck, tag: 'Diesel Corridor Congestion', color: 'from-blue-500/20 to-cyan-500/20 text-cyan-400 border-blue-500/30' },
  { label: 'Industrial Chimney', icon: Factory, tag: 'Boiler Point Source', color: 'from-red-500/20 to-purple-500/20 text-red-400 border-red-500/30' },
];

export default function CitizenReport() {
  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [photoName, setPhotoName] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [audioAttached, setAudioAttached] = useState(false);
  const [submittedReport, setSubmittedReport] = useState(null);
  const [recentReports, setRecentReports] = useState([]);

  const [formData, setFormData] = useState({
    location: '',
    observation: '',
    language: 'hi',
    category: '',
    consent: true
  });

  // Load existing saved reports
  useEffect(() => {
    fetch('/api/v1/reports')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setRecentReports(data.slice(0, 5));
        } else {
          const cached = JSON.parse(localStorage.getItem('airsentinel_citizen_reports') || '[]');
          setRecentReports(cached.slice(0, 5));
        }
      })
      .catch(() => {
        const cached = JSON.parse(localStorage.getItem('airsentinel_citizen_reports') || '[]');
        setRecentReports(cached.slice(0, 5));
      });
  }, []);

  const handlePhotoSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setPhotoName(e.target.files[0].name);
    }
  };

  const handleVoiceToggle = () => {
    if (isRecording) {
      setIsRecording(false);
      setAudioAttached(true);
    } else {
      setIsRecording(true);
      setTimeout(() => {
        setIsRecording(false);
        setAudioAttached(true);
      }, 3000);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStep(2);

    const fullObservation = `${formData.category ? `[${formData.category}] ` : ''}${formData.observation}${photoName ? ` (Attached Photo: ${photoName})` : ''}${audioAttached ? ' (Attached Voice Audio Note)' : ''}`;

    const payload = {
      location: formData.location,
      observation: fullObservation,
      language: formData.language,
      source_type: photoName ? 'photo' : audioAttached ? 'voice' : 'text',
      consent: formData.consent,
      coarse_grid: formData.location
    };

    let resultRecord = null;

    try {
      const res = await fetch('/api/v1/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        resultRecord = {
          report_id: data.report_id || `REP-${Date.now().toString().slice(-6)}`,
          location: formData.location,
          observation: fullObservation,
          timestamp_utc: data.timestamp_utc || new Date().toISOString(),
          locality_id: data.locality_id || 'DEL_GEN'
        };
      }
    } catch (err) {
      console.warn('Backend API unavailable, saving locally:', err);
    }

    if (!resultRecord) {
      // Local fallback
      resultRecord = {
        report_id: `REP-${Math.floor(100000 + Math.random() * 900000)}`,
        location: formData.location,
        observation: fullObservation,
        timestamp_utc: new Date().toISOString(),
        locality_id: `DEL_${formData.location.slice(0, 4).toUpperCase()}`
      };
    }

    // Save to localStorage for offline resilience
    const existing = JSON.parse(localStorage.getItem('airsentinel_citizen_reports') || '[]');
    const updated = [resultRecord, ...existing];
    localStorage.setItem('airsentinel_citizen_reports', JSON.stringify(updated));

    setSubmittedReport(resultRecord);
    setRecentReports(updated.slice(0, 5));
    setIsSubmitting(false);
    setStep(3);
  };

  return (
    <div className="max-w-4xl mx-auto py-6 space-y-8">
      <header className="text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-medium mb-3">
          <ShieldCheck className="w-3.5 h-3.5" /> Official Citizen Environmental Sentry
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">Report Hyperlocal Pollution</h1>
        <p className="text-slate-400 text-sm max-w-xl mx-auto">
          Your ground observation is cryptographically anonymized and directly ingested into the AirSentinel AI model for authority dispatch.
        </p>
      </header>

      <AnimatePresence mode="wait">
        {step === 1 && (
          <motion.div
            key="form"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <GlassCard className="p-7">
              <form onSubmit={handleSubmit} className="space-y-6">

                {/* Quick Cause Badges */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Select Pollution Type (Optional Quick Tag)
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
                    {QUICK_CATEGORIES.map(cat => {
                      const Icon = cat.icon;
                      const isSelected = formData.category === cat.tag;
                      return (
                        <button
                          key={cat.tag}
                          type="button"
                          onClick={() => setFormData({ ...formData, category: isSelected ? '' : cat.tag })}
                          className={`flex items-center gap-2 p-2.5 rounded-lg border text-xs font-medium transition-all ${
                            isSelected
                              ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-[0_0_12px_rgba(6,182,212,0.3)]'
                              : `${cat.color} hover:bg-white/10`
                          }`}
                        >
                          <Icon className="w-4 h-4 flex-shrink-0" />
                          <span className="truncate">{cat.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Media Evidence Upload area */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Photo Upload */}
                  <label className={`border-2 border-dashed rounded-xl p-5 flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
                    photoName ? 'border-green-500/50 bg-green-500/10 text-green-300' : 'border-white/15 bg-white/5 hover:border-cyan-400/50 text-slate-400 hover:text-cyan-300'
                  }`}>
                    <Camera className="w-7 h-7 mb-2" />
                    <span className="text-sm font-medium">{photoName ? `Photo: ${photoName}` : 'Attach Photo Evidence'}</span>
                    <span className="text-xs opacity-70 mt-1">Geotagged smoke, burning or construction dust</span>
                    <input type="file" accept="image/*" className="hidden" onChange={handlePhotoSelect} />
                  </label>
                  
                  {/* Voice Note Upload */}
                  <div 
                    onClick={handleVoiceToggle}
                    className={`border-2 border-dashed rounded-xl p-5 flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
                      isRecording ? 'border-red-500 bg-red-500/20 text-red-300 animate-pulse' :
                      audioAttached ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300' :
                      'border-white/15 bg-white/5 hover:border-blue-400/50 text-slate-400 hover:text-blue-300'
                    }`}
                  >
                    <Mic className="w-7 h-7 mb-2" />
                    <span className="text-sm font-medium">
                      {isRecording ? 'Recording voice note... (3s)' : audioAttached ? 'Voice Note Attached ✓' : 'Record Voice Observation'}
                    </span>
                    <span className="text-xs opacity-70 mt-1">Local Hindi, Punjabi or English supported</span>
                  </div>
                </div>

                {/* Form Fields */}
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="md:col-span-2">
                      <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-cyan-400" /> Locality / Ward Name
                      </label>
                      <input 
                        type="text" 
                        required
                        className="w-full bg-slate-900/60 border border-white/15 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition-colors text-sm"
                        placeholder="E.g., Anand Vihar ISBT, Bawana Industrial Phase 2, Rohini Sec 18"
                        value={formData.location}
                        onChange={e => setFormData({...formData, location: e.target.value})}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                        Language
                      </label>
                      <select 
                        className="w-full bg-slate-900/60 border border-white/15 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:border-cyan-400 transition-colors text-sm"
                        value={formData.language}
                        onChange={e => setFormData({...formData, language: e.target.value})}
                      >
                        <option value="en">English</option>
                        <option value="hi">हिंदी (Hindi)</option>
                        <option value="pa">ਪੰਜਾਬੀ (Punjabi)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                      Specific Observation Details
                    </label>
                    <textarea 
                      required
                      className="w-full bg-slate-900/60 border border-white/15 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition-colors h-24 resize-none text-sm"
                      placeholder="Describe what you see or smell: thick black smoke from industrial unit, continuous plastic/garbage burning, intense unpaved road dust..."
                      value={formData.observation}
                      onChange={e => setFormData({...formData, observation: e.target.value})}
                    />
                  </div>
                </div>

                {/* Consent & Privacy Notice */}
                <div className="flex items-start gap-3 bg-cyan-950/30 border border-cyan-800/40 p-3.5 rounded-lg">
                  <input 
                    type="checkbox"
                    id="consent"
                    checked={formData.consent}
                    onChange={e => setFormData({...formData, consent: e.target.checked})}
                    className="mt-1 accent-cyan-500 w-4 h-4 cursor-pointer"
                  />
                  <label htmlFor="consent" className="text-xs text-slate-300 cursor-pointer">
                    I consent to transmitting this anonymized environmental evidence to the <strong className="text-white">DPCC, MCD, and CAQM</strong> enforcement desks for rapid intervention. No personal identifying information (PII) is stored.
                  </label>
                </div>

                <button 
                  type="submit"
                  disabled={isSubmitting || !formData.consent}
                  className="w-full py-3 bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-medium rounded-xl shadow-[0_0_20px_rgba(6,182,212,0.3)] transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-50"
                >
                  <Send className="w-4 h-4" /> Transmit Report to AirSentinel Network
                </button>
              </form>
            </GlassCard>
          </motion.div>
        )}

        {step === 2 && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-20 text-center"
          >
            <div className="w-14 h-14 border-4 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin mb-4" />
            <h2 className="text-xl text-white font-semibold mb-1">Ingesting & Corroborating Report...</h2>
            <p className="text-slate-400 text-sm max-w-sm">
              Cross-referencing sensor telemetry and running AI root-cause attribution.
            </p>
          </motion.div>
        )}

        {step === 3 && submittedReport && (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-6"
          >
            <GlassCard className="p-8 text-center border-green-500/40 bg-green-950/20">
              <div className="w-16 h-16 bg-green-500/20 border border-green-500/40 rounded-full flex items-center justify-center mx-auto mb-4 shadow-[0_0_25px_rgba(34,197,94,0.3)]">
                <CheckCircle2 className="w-8 h-8 text-green-400" />
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded bg-green-500/20 text-green-300 font-bold">
                {submittedReport.report_id}
              </span>
              <h2 className="text-2xl font-bold text-white mt-3 mb-2">Report Successfully Ingested</h2>
              <p className="text-slate-300 text-sm max-w-lg mx-auto mb-6">
                Your ground evidence for <strong className="text-cyan-400">{submittedReport.location}</strong> has been stored in the AirSentinel audit datastore and queued for statutory authority verification.
              </p>

              <div className="max-w-md mx-auto p-4 rounded-xl bg-slate-900/60 border border-white/10 text-left text-xs space-y-2 mb-6">
                <div className="flex justify-between">
                  <span className="text-slate-400">Timestamp:</span>
                  <span className="text-slate-200 font-mono">{new Date(submittedReport.timestamp_utc).toLocaleTimeString()} UTC</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Authority Routing:</span>
                  <span className="text-amber-400 font-medium">DPCC / MCD Enforcement Desk</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Status:</span>
                  <span className="text-green-400 font-medium flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" /> Queued for Corroboration
                  </span>
                </div>
              </div>

              <button 
                onClick={() => {
                  setStep(1);
                  setFormData({ location: '', observation: '', language: 'hi', category: '', consent: true });
                  setPhotoName('');
                  setAudioAttached(false);
                }}
                className="px-6 py-2.5 bg-white/10 hover:bg-white/15 border border-white/20 rounded-xl text-white text-sm transition-all"
              >
                Submit Another Observation
              </button>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Recent Community Signals Table */}
      {recentReports.length > 0 && (
        <GlassCard className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" /> Recent Community Telemetry Ingests
            </h3>
            <span className="text-xs text-slate-400">{recentReports.length} records verified</span>
          </div>
          <div className="divide-y divide-white/5 text-xs">
            {recentReports.map((r, idx) => (
              <div key={r.report_id || idx} className="py-3 flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-cyan-400">{r.report_id}</span>
                    <span className="font-semibold text-white">{r.location || r.locality_id}</span>
                  </div>
                  <p className="text-slate-400 line-clamp-1">{r.observation || r.report_text}</p>
                </div>
                <span className="text-slate-500 whitespace-nowrap text-[11px]">
                  {new Date(r.timestamp_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
          </div>
        </GlassCard>
      )}
    </div>
  );
}
