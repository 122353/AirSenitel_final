import React from 'react';

export default function GlassCard({ children, className = '', hover = false, glow = '' }) {
  const hoverClass = hover ? 'hover:scale-[1.02] hover:-translate-y-1 transition-all duration-300' : '';
  const glowClass = glow ? `glow-${glow}` : '';
  
  return (
    <div className={`glass-card rounded-2xl ${hoverClass} ${glowClass} ${className}`}>
      {children}
    </div>
  );
}
