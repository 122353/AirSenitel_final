import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Activity, Map, Globe2, Network, MessageSquarePlus, Menu, ChevronLeft, Sun, Moon, Wind } from 'lucide-react';

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
    <aside 
      className={`relative z-50 h-full flex flex-col bg-[#080f1e] border-r border-[#1a3055] transition-all duration-300 ${collapsed ? 'w-[80px]' : 'w-[260px]'}`}
    >
      <div className="flex items-center justify-between p-4 mb-4 border-b border-[#1a3055]">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="relative">
              <Wind className="w-8 h-8 text-[#0ea5e9]" />
              <div className="absolute top-0 right-0 w-2 h-2 bg-[#22c55e] rounded-full animate-pulse-ring" />
            </div>
            <span className="text-xl font-bold text-white">
              VayuNirikshak
            </span>
          </div>
        )}
        <button 
          onClick={() => setCollapsed(!collapsed)}
          className={`p-2 rounded-lg hover:bg-white/5 transition-colors ${collapsed ? 'mx-auto' : ''}`}
        >
          {collapsed ? <Menu className="w-6 h-6 text-[#7aa2cc]" /> : <ChevronLeft className="w-6 h-6 text-[#7aa2cc]" />}
        </button>
      </div>

      <nav className="flex-1 px-3 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `
              flex items-center gap-3 px-3 py-3 rounded-lg transition-colors
              ${isActive 
                ? 'bg-[#0ea5e9]/10 border-l-4 border-[#0ea5e9] text-[#0ea5e9]' 
                : 'hover:bg-white/5 text-[#7aa2cc] hover:text-white border-l-4 border-transparent'
              }
            `}
            title={collapsed ? item.label : undefined}
          >
            <item.icon className={`w-5 h-5 flex-shrink-0 ${collapsed ? 'mx-auto' : ''}`} />
            {!collapsed && (
              <span className="font-medium truncate">{item.label}</span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 mt-auto border-t border-[#1a3055]">
        <button
          onClick={toggleTheme}
          className={`w-full flex items-center ${collapsed ? 'justify-center' : 'justify-between'} p-3 rounded-lg hover:bg-white/5 transition-colors`}
        >
          {!collapsed && <span className="text-sm font-medium text-[#7aa2cc]">Theme</span>}
          {theme === 'dark' ? <Sun className="w-5 h-5 text-[#f59e0b]" /> : <Moon className="w-5 h-5 text-[#7aa2cc]" />}
        </button>
        
        {!collapsed && (
          <div className="mt-4 flex items-center gap-2 px-3">
            <div className="w-2 h-2 rounded-full bg-[#22c55e] animate-pulse-ring" />
            <span className="text-xs text-[#7aa2cc]">System Connected</span>
          </div>
        )}
      </div>
    </aside>
  );
}
