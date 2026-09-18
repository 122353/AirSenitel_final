export const EFFECTIVE_RANGES = {
  pm25: 1500, // meters
  pm10: 2000,
  no2: 2000,
  o3: 3000,
  so2: 2000,
  co: 1500
};

export function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371e3; // metres
  const φ1 = lat1 * Math.PI/180; // φ, λ in radians
  const φ2 = lat2 * Math.PI/180;
  const Δφ = (lat2-lat1) * Math.PI/180;
  const Δλ = (lon2-lon1) * Math.PI/180;

  const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
            Math.cos(φ1) * Math.cos(φ2) *
            Math.sin(Δλ/2) * Math.sin(Δλ/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

  return R * c; // in metres
}

export function getSensorWeight(distance, pollutant) {
  const maxRange = EFFECTIVE_RANGES[pollutant] || 2000;
  if (distance > maxRange) return 0;
  // Inverse distance weighting, dropping off to 0 at max range
  return Math.max(0, 1 - (distance / maxRange));
}

export function isInRange(distance, pollutant) {
  const maxRange = EFFECTIVE_RANGES[pollutant] || 2000;
  return distance <= maxRange;
}
