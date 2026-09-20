import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, Brain, Building, AlertCircle, FileText } from 'lucide-react';

export default function CaseDispatchModal({ isOpen, caseData, onClose, onDispatchSuccess }) {
  const [diagnosis, setDiagnosis] = useState(null);
  const [loadingDiag, setLoadingDiag] = useState(false);
  const [agency, setAgency] = useState('DPCC');
  const [unit, setUnit] = useState('Industrial Inspection Wing');
  const [actionType, setActionType] = useState('Field Inspection');
  const [priority, setPriority] = useState('High');
  const [notes, setNotes] = useState('');

  const agencyUnits = {
    'DPCC': ['Industrial Inspection Wing', 'Waste Management Cell', 'Air Lab Team'],
    'MCD': ['Anti-Smog Gun Fleet', 'C&D Waste Enforcement', 'Sanitation Ward Officer'],
    'Traffic Police': ['Corridor Management', 'Heavy Vehicle Check Unit'],
    'CAQM': ['Regional Flying Squad', 'Policy Directive Desk'],
    'SDM': ['Local Executive Magistrate', 'Emergency Response']
  };

  useEffect(() => {
    if (isOpen && caseData) {
      setAgency('DPCC');
      setUnit('Industrial Inspection Wing');
      setNotes('');
      setPriority(caseData.severity === 'critical' ? 'Emergency' : 'High');

      // Fetch AI Diagnosis for system cases
      if (caseData.type !== 'citizen_report') {
        setLoadingDiag(true);
        fetch('/api/v1/diagnostics/spikes')
          .then(res => res.json())
          .then(data => {
            const result = data.find(d => d.case_id === caseData.id) || data[0];
            setDiagnosis(result);
          })
          .catch(() => {})
          .finally(() => setLoadingDiag(false));
      } else {
        setDiagnosis(null);
      }
    }
  }, [isOpen, caseData]);

  if (!isOpen || !caseData) return null;

  const isCitizen = caseData.type === 'citizen_report';

  const handleDispatch = () => {
    if (onDispatchSuccess) {
      onDispatchSuccess({
        ...caseData,
        assigned_authority: agency,
        status: 'dispatched'
      });
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-40 flex justify-end">
        <motion.div 
          initial={{ opacity: 0 }} 
          animate={{ opacity: 1 }} 
          exit={{ opacity: 0 }} 
          onClick={onClose}
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40" 
        />
        
        <motion.div 
          initial={{ x: '100%' }} 
          animate={{ x: 0 }} 
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="relative z-50 w-[520px] bg-[#080f1e] border-l border-[#1a3055] shadow-2xl h-full flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-[#1a3055] bg-[#0c1729]">
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-[#f0f6ff]">{caseData.id}</h2>
              <span className={`status-badge ${caseData.severity === 'critical' ? 'status-badge-red' : 'status-badge-amber'}`}>
                {caseData.severity || 'high'}
              </span>
            </div>
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/10 text-[#7aa2cc] transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
            {/* Case Info */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-[#7aa2cc] block text-xs mb-1">Area</span>
                <span className="text-[#f0f6ff] font-medium">{caseData.area}</span>
              </div>
              <div>
                <span className="text-[#7aa2cc] block text-xs mb-1">Category</span>
                <span className="text-[#f0f6ff] font-medium">{caseData.category}</span>
              </div>
              <div>
                <span className="text-[#7aa2cc] block text-xs mb-1">Time Reported</span>
                <span className="text-[#f0f6ff] font-medium">{caseData.time}</span>
              </div>
              <div>
                <span className="text-[#7aa2cc] block text-xs mb-1">Observed PM2.5</span>
                <span className="text-[#ef4444] font-bold font-mono">{caseData.observed_pm25} µg/m³</span>
              </div>
            </div>

            {/* Citizen Report Info Box */}
            {isCitizen && caseData.observation && (
              <div className="bg-[#0c1729] border border-[#1a3055] rounded-xl p-4">
                <h3 className="flex items-center gap-2 text-sm font-bold text-[#0ea5e9] mb-2">
                  <FileText className="w-4 h-4" /> Citizen Observation
                </h3>
                <p className="text-[#f0f6ff] text-sm">{caseData.observation}</p>
              </div>
            )}

            {/* AI Diagnosis Section */}
            {!isCitizen && (
              <div className="space-y-4">
                <h3 className="flex items-center gap-2 text-sm font-bold text-[#f0f6ff] uppercase tracking-wide">
                  <Brain className="w-4 h-4 text-[#0ea5e9]" /> Ensembling Engine Diagnosis
                </h3>
                
                {loadingDiag ? (
                  <div className="animate-pulse bg-[#0c1729] h-32 rounded-xl border border-[#1a3055]"></div>
                ) : diagnosis ? (
                  <>
                    <div className="bg-[#0ea5e9]/10 border border-[#0ea5e9]/30 rounded-xl p-4">
                      <span className="text-xs text-[#0ea5e9] uppercase font-bold tracking-wider mb-1 block">Primary Cause</span>
                      <p className="text-[#f0f6ff] font-medium">{diagnosis.primary_cause}</p>
                    </div>

                    <div className="bg-[#0c1729] border border-[#1a3055] rounded-xl p-4 space-y-3">
                      <span className="text-xs text-[#7aa2cc] uppercase font-bold tracking-wider block mb-2">Signal Attributions (SHAP)</span>
                      {diagnosis.shap_signals?.map((sig, i) => (
                        <div key={i} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-[#f0f6ff]">{sig.name}</span>
                            <span className="text-[#7aa2cc]">{sig.voted_for} ({Math.round(sig.signal_confidence * 100)}%)</span>
                          </div>
                          <div className="h-2 w-full bg-[#080f1e] rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-[#0ea5e9] rounded-full" 
                              style={{ width: `${sig.signal_confidence * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-[#0c1729] border border-[#1a3055] rounded-xl p-3">
                        <span className="text-[10px] text-[#7aa2cc] uppercase block mb-1">Recommended Action</span>
                        <span className="text-sm text-[#f0f6ff]">{diagnosis.recommended_action}</span>
                      </div>
                      <div className="bg-[#0c1729] border border-[#1a3055] rounded-xl p-3">
                        <span className="text-[10px] text-[#7aa2cc] uppercase block mb-1">GRAP Trigger</span>
                        <span className="text-sm text-[#f0f6ff]">{diagnosis.grap_trigger}</span>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="p-4 bg-[#0c1729] border border-[#1a3055] rounded-xl text-center text-[#7aa2cc] text-sm">
                    Diagnosis not available.
                  </div>
                )}
              </div>
            )}

            {/* Authority Assignment Section */}
            <div className="space-y-4 pt-4 border-t border-[#1a3055]">
              <h3 className="flex items-center gap-2 text-sm font-bold text-[#f0f6ff] uppercase tracking-wide">
                <Building className="w-4 h-4 text-[#f59e0b]" /> Authority Assignment
              </h3>
              
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-[#7aa2cc] mb-1">Target Statutory Agency</label>
                  <select 
                    value={agency} 
                    onChange={e => {
                      setAgency(e.target.value);
                      setUnit(agencyUnits[e.target.value][0]);
                    }}
                    className="w-full bg-[#0c1729] border border-[#1a3055] text-[#f0f6ff] text-sm rounded-lg p-2.5 focus:outline-none focus:border-[#0ea5e9]"
                  >
                    {Object.keys(agencyUnits).map(a => <option key={a} value={a}>{a}</option>)}
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-[#7aa2cc] mb-1">Enforcement Unit</label>
                  <select 
                    value={unit} 
                    onChange={e => setUnit(e.target.value)}
                    className="w-full bg-[#0c1729] border border-[#1a3055] text-[#f0f6ff] text-sm rounded-lg p-2.5 focus:outline-none focus:border-[#0ea5e9]"
                  >
                    {agencyUnits[agency].map(u => <option key={u} value={u}>{u}</option>)}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-[#7aa2cc] mb-1">Action Type</label>
                    <select 
                      value={actionType}
                      onChange={e => setActionType(e.target.value)}
                      className="w-full bg-[#0c1729] border border-[#1a3055] text-[#f0f6ff] text-sm rounded-lg p-2.5 focus:outline-none focus:border-[#0ea5e9]"
                    >
                      <option>Field Inspection</option>
                      <option>Deploy Sprinklers</option>
                      <option>Issue Notice</option>
                      <option>Seal Premises</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-[#7aa2cc] mb-1">Priority</label>
                    <select 
                      value={priority}
                      onChange={e => setPriority(e.target.value)}
                      className="w-full bg-[#0c1729] border border-[#1a3055] text-[#f0f6ff] text-sm rounded-lg p-2.5 focus:outline-none focus:border-[#0ea5e9]"
                    >
                      <option>Emergency</option>
                      <option>High</option>
                      <option>Medium</option>
                      <option>Low</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs text-[#7aa2cc] mb-1">Officer Field Notes</label>
                  <textarea 
                    value={notes}
                    onChange={e => setNotes(e.target.value)}
                    rows={3}
                    placeholder="Enter dispatch instructions or context..."
                    className="w-full bg-[#0c1729] border border-[#1a3055] text-[#f0f6ff] text-sm rounded-lg p-2.5 focus:outline-none focus:border-[#0ea5e9] resize-none"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="p-5 border-t border-[#1a3055] bg-[#0c1729]">
            <button 
              onClick={handleDispatch}
              className="w-full flex items-center justify-center gap-2 bg-[#0ea5e9] text-[#060d1a] font-bold py-3 rounded-lg hover:opacity-90 transition-opacity"
            >
              <Send className="w-5 h-5" /> Confirm & Dispatch Order
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
