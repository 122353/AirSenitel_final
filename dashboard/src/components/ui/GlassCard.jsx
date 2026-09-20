import React from 'react';

export default function GlassCard({ children, className = '' }) {
  return (
    <div className={`bg-[#0c1729] border border-[#1a3055] rounded-xl ${className}`}>
      {children}
    </div>
  );
}
