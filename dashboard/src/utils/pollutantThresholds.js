export const WHO_THRESHOLDS = {
  pm25: [15, 35, 75, 150],
  pm10: [45, 100, 200, 300],
  no2: [25, 50, 100, 200],
  o3: [60, 100, 160, 240],
  so2: [40, 80, 380, 800],
  co: [4, 10, 30, 60] // mg/m3
};

export const NAAQS_THRESHOLDS = {
  pm25: [30, 60, 90, 120],
  pm10: [50, 100, 250, 430],
  no2: [40, 80, 180, 280],
  o3: [50, 100, 168, 208],
  so2: [40, 80, 380, 800],
  co: [2, 4, 10, 17]
};

export const POLLUTANT_COLORS = {
  pm25: '#ef4444', // Red
  pm10: '#f97316', // Orange
  no2: '#8b5cf6', // Violet
  o3: '#22c55e', // Green
  so2: '#eab308', // Yellow
  co: '#06b6d4'   // Cyan
};

export const SEVERITY_COLORS = {
  low: '#22c55e',
  moderate: '#eab308',
  high: '#f97316',
  very_high: '#ef4444',
  critical: '#dc2626'
};

export function getSeverityLevel(pollutant, value) {
  const thresholds = WHO_THRESHOLDS[pollutant] || WHO_THRESHOLDS.pm25;
  if (value <= thresholds[0]) return 'low';
  if (value <= thresholds[1]) return 'moderate';
  if (value <= thresholds[2]) return 'high';
  if (value <= thresholds[3]) return 'very_high';
  return 'critical';
}

export function getHealthGuidance(pollutant, value) {
  const level = getSeverityLevel(pollutant, value);
  switch (level) {
    case 'low': return 'Air quality is satisfactory. No health risk.';
    case 'moderate': return 'Acceptable quality. Sensitive individuals should consider limiting prolonged outdoor exertion.';
    case 'high': return 'Members of sensitive groups may experience health effects. The general public is not likely to be affected.';
    case 'very_high': return 'Everyone may begin to experience health effects; members of sensitive groups may experience more serious health effects.';
    case 'critical': return 'Health warning of emergency conditions. The entire population is more likely to be affected.';
    default: return 'Unknown status.';
  }
}
