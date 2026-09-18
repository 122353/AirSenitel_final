import { useState, useEffect, useCallback } from 'react';

// Generates a random walk value
const generateValue = (prev, min, max, volatility) => {
  const change = (Math.random() - 0.5) * volatility;
  const next = prev + change;
  return Math.max(min, Math.min(max, next));
};

export function useLiveData() {
  const [data, setData] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);

  // Initialize with some historical data (last 100 points, 1 min apart)
  const initializeData = useCallback(() => {
    const initialData = [];
    let currentPm25 = 65;
    let currentPm10 = 120;
    let currentNo2 = 45;
    let currentO3 = 30;
    let currentSo2 = 15;
    let currentCo = 2;

    const now = Date.now();
    for (let i = 100; i >= 0; i--) {
      currentPm25 = generateValue(currentPm25, 10, 300, 10);
      currentPm10 = generateValue(currentPm10, 20, 500, 15);
      currentNo2 = generateValue(currentNo2, 10, 200, 5);
      currentO3 = generateValue(currentO3, 5, 150, 8);
      currentSo2 = generateValue(currentSo2, 1, 100, 3);
      currentCo = generateValue(currentCo, 0.5, 10, 0.5);

      initialData.push({
        timestamp: new Date(now - i * 60000).toISOString(),
        pm25: parseFloat(currentPm25.toFixed(1)),
        pm10: parseFloat(currentPm10.toFixed(1)),
        no2: parseFloat(currentNo2.toFixed(1)),
        o3: parseFloat(currentO3.toFixed(1)),
        so2: parseFloat(currentSo2.toFixed(1)),
        co: parseFloat(currentCo.toFixed(1)),
      });
    }
    return initialData;
  }, []);

  useEffect(() => {
    // Attempt actual SSE here (stubbed for demo fallback)
    // In a real app, this would be new EventSource('/api/v1/live-data')
    let sseSource = null;
    
    // Fallback to simulated data
    setData(initializeData());
    setIsConnected(true);
    
    const interval = setInterval(() => {
      setData((prevData) => {
        const last = prevData[prevData.length - 1];
        const newDataPoint = {
          timestamp: new Date().toISOString(),
          pm25: parseFloat(generateValue(last.pm25, 10, 300, 15).toFixed(1)),
          pm10: parseFloat(generateValue(last.pm10, 20, 500, 20).toFixed(1)),
          no2: parseFloat(generateValue(last.no2, 10, 200, 8).toFixed(1)),
          o3: parseFloat(generateValue(last.o3, 5, 150, 10).toFixed(1)),
          so2: parseFloat(generateValue(last.so2, 1, 100, 4).toFixed(1)),
          co: parseFloat(generateValue(last.co, 0.5, 10, 0.5).toFixed(1)),
        };
        // Keep last 100 points
        return [...prevData.slice(1), newDataPoint];
      });
    }, 3000);

    return () => {
      clearInterval(interval);
      if (sseSource) sseSource.close();
    };
  }, [initializeData]);

  return { data, isConnected, error };
}
