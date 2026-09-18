import React, { useEffect, useState } from 'react';
import GlassCard from './GlassCard';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export default function MetricCard({ title, value, subtitle, trend, icon: Icon, color = 'cyan' }) {
  const [count, setCount] = useState(0);
  
  // Extract number from value if it's a string like "1,234"
  const numericValue = typeof value === 'number' ? value : parseFloat(value.toString().replace(/,/g, ''));
  const isNumber = !isNaN(numericValue);

  useEffect(() => {
    if (!isNumber) return;
    
    let start = 0;
    const duration = 1500; // ms
    const increment = numericValue / (duration / 16); // 60fps
    
    const timer = setInterval(() => {
      start += increment;
      if (start >= numericValue) {
        setCount(numericValue);
        clearInterval(timer);
      } else {
        setCount(start);
      }
    }, 16);
    
    return () => clearInterval(timer);
  }, [numericValue, isNumber]);

  const displayValue = isNumber 
    ? (Number.isInteger(numericValue) ? Math.floor(count) : count.toFixed(1)) 
    : value;

  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend > 0) return <TrendingUp className="w-4 h-4 text-red-400" />;
    if (trend < 0) return <TrendingDown className="w-4 h-4 text-green-400" />;
    return <Minus className="w-4 h-4 text-slate-400" />;
  };

  const colorStyles = {
    cyan: 'text-cyan-400 bg-cyan-400/10',
    red: 'text-red-400 bg-red-400/10',
    green: 'text-green-400 bg-green-400/10',
    amber: 'text-amber-400 bg-amber-400/10',
    blue: 'text-blue-400 bg-blue-400/10',
  };

  return (
    <GlassCard hover className="p-5 flex flex-col relative overflow-hidden">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-slate-400 font-medium text-sm">{title}</h3>
        {Icon && (
          <div className={`p-2 rounded-lg ${colorStyles[color]}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
      
      <div className="flex items-end gap-3 mt-auto">
        <div className="text-3xl font-bold text-slate-100">{displayValue}</div>
        {trend !== undefined && (
          <div className={`flex items-center gap-1 text-sm mb-1 ${trend > 0 ? 'text-red-400' : 'text-green-400'}`}>
            {getTrendIcon()}
            <span>{Math.abs(trend)}%</span>
          </div>
        )}
      </div>
      
      {subtitle && <div className="text-xs text-slate-500 mt-2">{subtitle}</div>}
      
      {/* Decorative gradient blur in background */}
      <div className={`absolute -bottom-6 -right-6 w-24 h-24 rounded-full blur-2xl opacity-20 bg-${color}-500`} />
    </GlassCard>
  );
}
