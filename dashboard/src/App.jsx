import React, { useState, useEffect } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import Sidebar from './components/ui/Sidebar';
import AuthorityDashboard from './pages/AuthorityDashboard';
import LiveDetection from './pages/LiveDetection';
import SensorMap3D from './pages/SensorMap3D';
import NationalOverview from './pages/NationalOverview';
import BRICSFederation from './pages/BRICSFederation';
import CitizenReport from './pages/CitizenReport';

function App() {
  const [theme, setTheme] = useState('dark');
  const location = useLocation();

  useEffect(() => {
    if (theme === 'dark') {
      document.body.classList.add('dark', 'bg-slate-950', 'text-slate-50');
      document.body.classList.remove('bg-slate-50', 'text-slate-900');
    } else {
      document.body.classList.remove('dark', 'bg-slate-950', 'text-slate-50');
      document.body.classList.add('bg-slate-50', 'text-slate-900');
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(t => t === 'dark' ? 'light' : 'dark');
  };

  return (
    <div className={`flex h-screen overflow-hidden ${theme === 'dark' ? 'bg-animated-gradient' : 'bg-slate-100'}`}>
      <Sidebar theme={theme} toggleTheme={toggleTheme} />
      
      <main className="flex-1 relative overflow-y-auto overflow-x-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="min-h-full p-6"
          >
            <Routes location={location}>
              <Route path="/" element={<AuthorityDashboard />} />
              <Route path="/live" element={<LiveDetection />} />
              <Route path="/sensors" element={<SensorMap3D theme={theme} />} />
              <Route path="/national" element={<NationalOverview theme={theme} />} />
              <Route path="/brics" element={<BRICSFederation theme={theme} />} />
              <Route path="/report" element={<CitizenReport theme={theme} />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

export default App;
