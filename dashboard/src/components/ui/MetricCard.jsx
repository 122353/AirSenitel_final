import React, { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export default function MetricCard({ title, value, subtitle, trend, icon: Icon, color = 'cyan' }) {
  const [count, setCount] = useState(0);
  
  const numericValue = typeof value === 'number' ? value : parseFloat(value.toString().replace(/,/g, ''));
  const isNumber = !isNaN(numericValue);

  useEffect(() => {
    if (!isNumber) return;
    
    let start = 0;
    const duration = 1500;
    const increment = numericValue / (duration / 16);
    
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
    if (trend > 0) return <TrendingUp className="w-3.5 h-3.5" />;
    if (trend < 0) return <TrendingDown className="w-3.5 h-3.5" />;
    return <Minus className="w-3.5 h-3.5" />;
  };

  const borderColors = {
    cyan: 'border-l-cyan-500',
    red: 'border-l-red-500',
    green: 'border-l-green-500',
    amber: 'border-l-amber-500',
    blue: 'border-l-blue-500',
    teal: 'border-l-[#0ea5e9]'
  };
  
  const iconColors = {
    cyan: 'text-cyan-400',
    red: 'text-red-400',
    green: 'text-green-400',
    amber: 'text-amber-400',
    blue: 'text-blue-400',
    teal: 'text-[#0ea5e9]'
  };

  const leftBorder = borderColors[color] || borderColors.teal;
  const iconColor = iconColors[color] || iconColors.teal;

  return (
    <div className={`bg-[#0c1729] border-y border-r border-[#1a3055] border-l-4 ${leftBorder} rounded-xl p-5 flex flex-col`}>
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-[#7aa2cc] font-medium text-sm">{title}</h3>
        {Icon && (
          <div className={`${iconColor}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
      
      <div className="flex items-end gap-3 mt-auto">
        <div className="text-3xl font-bold text-[#f0f6ff]">{displayValue}</div>
        {trend !== undefined && (
          <div className={`flex items-center gap-1 text-sm mb-1 ${trend > 0 ? 'text-[#ef4444]' : 'text-[#22c55e]'}`}>
            {getTrendIcon()}
            <span className="font-medium">{Math.abs(trend)}%</span>
          </div>
        )}
      </div>
      
      {subtitle && <div className="text-xs text-[#7aa2cc] mt-2">{subtitle}</div>}
    </div>
  );
}
