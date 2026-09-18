import { useState, useEffect } from 'react';
import { getSeverityLevel } from '../utils/pollutantThresholds';

const DELHI_SENSORS = [
  { id: 'DPCC-NAJ', name: 'Najafgarh DPCC', lat: 28.6092, lon: 76.9798, type: 'pilot' },
  { id: 'DPCC-ROH', name: 'Rohini DPCC', lat: 28.7495, lon: 77.0565, type: 'pilot' },
  { id: 'DPCC-RKP', name: 'R K Puram DPCC', lat: 28.5630, lon: 77.1870, type: 'pilot' },
  { id: 'IGI-APT', name: 'IGI Airport', lat: 28.5600, lon: 77.0940, type: 'pilot' },
  { id: 'CIV-LNS', name: 'Civil Lines', lat: 28.6787, lon: 77.2262, type: 'pilot' },
  { id: 'DPCC-ANV', name: 'Anand Vihar DPCC', lat: 28.6468, lon: 77.3160, type: 'pilot' },
  { id: 'CPCB-NSI', name: 'NSIT Dwarka CPCB', lat: 28.6090, lon: 77.0320, type: 'pilot' },
  { id: 'IMD-PUS', name: 'Pusa IMD', lat: 28.6396, lon: 77.1460, type: 'pilot' }
];

export function useSensorNetwork() {
  const [sensors, setSensors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Simulated API call
    const fetchSensors = async () => {
      try {
        setLoading(true);
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 600));
        
        // Enhance with simulated current readings
        const activeSensors = DELHI_SENSORS.map(sensor => {
          const pm25 = Math.floor(Math.random() * 200) + 20; // 20 to 220
          const pm10 = pm25 * 1.8 + Math.floor(Math.random() * 50);
          const no2 = Math.floor(Math.random() * 100) + 10;
          const o3 = Math.floor(Math.random() * 120) + 10;
          const so2 = Math.floor(Math.random() * 60) + 5;
          const co = (Math.random() * 4 + 0.5).toFixed(1);
          
          return {
            ...sensor,
            pm25,
            pm10,
            no2,
            o3,
            so2,
            co,
            severity: getSeverityLevel('pm25', pm25),
            status: Math.random() > 0.05 ? 'active' : 'maintenance',
            lastUpdated: new Date().toISOString()
          };
        });
        
        setSensors(activeSensors);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchSensors();
    
    // Periodically update sensor readings
    const interval = setInterval(fetchSensors, 30000);
    return () => clearInterval(interval);
  }, []);

  return { sensors, loading, error };
}
