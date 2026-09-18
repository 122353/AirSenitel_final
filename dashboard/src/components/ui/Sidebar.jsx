import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Activity, Map, Globe2, Network, MessageSquarePlus, Menu, ChevronLeft, Sun, Moon, Wind } from 'lucide-react';
import { motion } from 'framer-motion';

const navItems = [
  { path: '/', label: 'Authority Dashboard', icon: LayoutDashboard },
  { path: '/live', label: 'Live Detection', icon: Activity },
  { path: '/sensors', label: '3D Sensor Map', icon: Map },
  { path: '/national', label: 'National Overview', icon: Globe2 },
  { path: '/brics', label: 'BRICS Network', icon: Network },
  { path: '/report', label: 'Report Pollution', icon: MessageSquarePlus },
];

export default function Sidebar({ theme, toggleTheme }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <motion.aside 
      initial={false}
      animate={{ width: collapsed ? 80 : 260 }}
      className={`relative z-50 h-full flex flex-col border-r ${theme === 'dark' ? 'border-white/10 bg-slate-900/40 backdrop-blur-xl' : 'border-slate-200 bg-white/70 backdrop-blur-xl'}`}
    >
      <div className="flex items-center justify-between p-4 mb-4 border-b border-white/10">
        {!collapsed && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2">
            <div className="relative">
              <Wind className="w-8 h-8 text-cyan-400" />
              <div className="absolute top-0 right-0 w-2 h-2 bg-green-500 rounded-full animate-pulse-ring" />
            </div>
            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-500">
              AirSentinel
            </span>
          </motion.div>
        )}
        <button 
          onClick={() => setCollapsed(!collapsed)}
          className="p-2 rounded-lg hover:bg-white/10 transition-colors mx-auto"
        >
          {collapsed ? <Menu className="w-6 h-6 text-slate-300" /> : <ChevronLeft className="w-6 h-6 text-slate-300" />}
        </button>
      </div>

      <nav className="flex-1 px-3 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `
              flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-300
              ${isActive 
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 text-cyan-300 shadow-[0_0_15px_rgba(6,182,212,0.3)]' 
                : 'hover:bg-white/5 text-slate-400 hover:text-slate-200'
              }
            `}
            title={collapsed ? item.label : undefined}
          >
            <item.icon className="w-5 h-5 flex-shrink-0" />
            {!collapsed && (
              <span className="font-medium truncate">{item.label}</span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 mt-auto border-t border-white/10">
        <button
          onClick={toggleTheme}
          className={`w-full flex items-center ${collapsed ? 'justify-center' : 'justify-between'} p-3 rounded-xl hover:bg-white/10 transition-colors`}
        >
          {!collapsed && <span className="text-sm font-medium text-slate-300">Theme</span>}
          {theme === 'dark' ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5 text-slate-700" />}
        </button>
        
        {!collapsed && (
          <div className="mt-4 flex items-center gap-2 px-3">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse-ring" />
            <span className="text-xs text-slate-400">System Connected</span>
          </div>
        )}
      </div>
    </motion.aside>
  );
}
