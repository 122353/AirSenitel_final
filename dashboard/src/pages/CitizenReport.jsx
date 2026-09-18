import React, { useState } from 'react';
import GlassCard from '../components/ui/GlassCard';
import { Camera, Mic, MapPin, Send, CheckCircle2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function CitizenReport() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    location: '',
    observation: '',
    language: 'hi',
  });
  
  const handleSubmit = (e) => {
    e.preventDefault();
    setStep(2); // Loading
    setTimeout(() => {
      setStep(3); // Success
    }, 2000);
  };

  return (
    <div className="max-w-3xl mx-auto py-8">
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-white mb-2">Report Pollution</h1>
        <p className="text-slate-400">Your ground-level reports help train our AI models</p>
      </header>

      <AnimatePresence mode="wait">
        {step === 1 && (
          <motion.div
            key="form"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <GlassCard className="p-8">
              <form onSubmit={handleSubmit} className="space-y-6">
                
                {/* Media Upload area */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border-2 border-dashed border-white/20 rounded-xl p-6 flex flex-col items-center justify-center text-slate-400 hover:border-cyan-400/50 hover:text-cyan-400 transition-colors cursor-pointer bg-white/5">
                    <Camera className="w-8 h-8 mb-2" />
                    <span className="text-sm font-medium">Upload Photo</span>
                    <span className="text-xs mt-1 opacity-70">Visual evidence of smoke/dust</span>
                  </div>
                  
                  <div className="border-2 border-dashed border-white/20 rounded-xl p-6 flex flex-col items-center justify-center text-slate-400 hover:border-blue-400/50 hover:text-blue-400 transition-colors cursor-pointer bg-white/5">
                    <Mic className="w-8 h-8 mb-2" />
                    <span className="text-sm font-medium">Record Voice Note</span>
                    <span className="text-xs mt-1 opacity-70">Local language supported</span>
                  </div>
                </div>

                {/* Form fields */}
                <div className="space-y-4">
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-slate-300 mb-1 flex items-center gap-2">
                        <MapPin className="w-4 h-4" /> Locality / Area
                      </label>
                      <input 
                        type="text" 
                        required
                        className="w-full bg-slate-900/50 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyan-500 transition-colors"
                        placeholder="E.g., Anand Vihar, Near ISBT"
                        value={formData.location}
                        onChange={e => setFormData({...formData, location: e.target.value})}
                      />
                    </div>
                    <div className="w-1/3">
                      <label className="block text-sm font-medium text-slate-300 mb-1">Language</label>
                      <select 
                        className="w-full bg-slate-900/50 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyan-500 transition-colors"
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
                    <label className="block text-sm font-medium text-slate-300 mb-1">Observation Details</label>
                    <textarea 
                      required
                      className="w-full bg-slate-900/50 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition-colors h-24 resize-none"
                      placeholder="Describe what you see or smell..."
                      value={formData.observation}
                      onChange={e => setFormData({...formData, observation: e.target.value})}
                    />
                  </div>
                </div>

                {/* Privacy notice */}
                <div className="flex items-start gap-3 bg-blue-500/10 border border-blue-500/20 p-4 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-blue-200">
                    Your report will be anonymized and fed directly into the AirSentinel predictive model. 
                    Local authorities may use this data to dispatch enforcement teams.
                  </p>
                </div>

                <button 
                  type="submit"
                  className="w-full py-3.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-medium rounded-xl shadow-[0_0_20px_rgba(6,182,212,0.3)] transition-all flex items-center justify-center gap-2"
                >
                  <Send className="w-5 h-5" /> Submit Report securely
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
            className="flex flex-col items-center justify-center py-20"
          >
            <div className="w-16 h-16 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin mb-4" />
            <h2 className="text-xl text-white font-medium mb-2">Analyzing Report...</h2>
            <p className="text-slate-400 text-sm">NLP extracting key entities and matching with sensor telemetry</p>
          </motion.div>
        )}

        {step === 3 && (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center justify-center py-16 text-center"
          >
            <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(34,197,94,0.3)]">
              <CheckCircle2 className="w-10 h-10 text-green-400" />
            </div>
            <h2 className="text-3xl font-bold text-white mb-3">Report Verified & Ingested</h2>
            <p className="text-slate-400 max-w-md mx-auto mb-8">
              Thank you. Your observation has been correlated with sensor <span className="text-cyan-400">DPCC-ANV</span> telemetry. The predictive model confidence has increased by 4.2%.
            </p>
            <button 
              onClick={() => { setStep(1); setFormData({ location: '', observation: '', language: 'hi' }); }}
              className="px-6 py-2 border border-white/20 rounded-lg text-slate-300 hover:bg-white/5 transition-colors"
            >
              Submit Another Report
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
