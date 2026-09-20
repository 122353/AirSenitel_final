import React, { useEffect, useRef, useState } from 'react';
import { EFFECTIVE_RANGES, POLLUTANT_COLORS } from '../../utils/sensorRange';
import { KeyRound, ShieldAlert, Sparkles } from 'lucide-react';

export default function GoogleMaps3DWrapper({ sensors = [], activePollutant = 'pm25', showRange = true, onSensorClick }) {
  const mapContainerRef = useRef(null);
  const [hasKey, setHasKey] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [mapError, setMapError] = useState(null);

  const activeApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || apiKeyInput;

  useEffect(() => {
    if (!activeApiKey) return;

    // Load Google Maps Script with Satellite/3D tilt
    const scriptId = 'google-maps-js-sdk';
    let script = document.getElementById(scriptId);

    const initMap = () => {
      if (!window.google || !mapContainerRef.current) return;
      try {
        const map = new window.google.maps.Map(mapContainerRef.current, {
          center: { lat: 28.6139, lng: 77.2090 }, // Delhi Center
          zoom: 12,
          tilt: 45,
          heading: 0,
          mapTypeId: 'hybrid', // Real satellite imagery + road overlay
          disableDefaultUI: false,
          mapTypeControl: true,
          styles: [
            { elementType: 'geometry', stylers: [{ saturation: -10 }] }
          ]
        });

        // Add sensor circles with physical effective radius
        sensors.forEach(sensor => {
          const color = POLLUTANT_COLORS[activePollutant] || '#ef4444';
          const radiusMeters = EFFECTIVE_RANGES[activePollutant] || 1500;

          if (showRange) {
            new window.google.maps.Circle({
              strokeColor: color,
              strokeOpacity: 0.8,
              strokeWeight: 2,
              fillColor: color,
              fillOpacity: 0.22,
              map: map,
              center: { lat: sensor.lat, lng: sensor.lon },
              radius: radiusMeters,
            });
          }

          // Marker
          const marker = new window.google.maps.Marker({
            position: { lat: sensor.lat, lng: sensor.lon },
            map: map,
            title: `${sensor.name} (${sensor.pm25 || 100} µg/m³)`,
            animation: window.google.maps.Animation.DROP
          });

          marker.addListener('click', () => {
            onSensorClick && onSensorClick(sensor);
          });
        });

        setHasKey(true);
      } catch (err) {
        setMapError(err.message);
      }
    };

    if (!script) {
      script = document.createElement('script');
      script.id = scriptId;
      script.src = `https://maps.googleapis.com/maps/api/js?key=${activeApiKey}&v=beta`;
      script.async = true;
      script.onload = initMap;
      script.onerror = () => setMapError('Failed to load Google Maps script. Check your API key.');
      document.head.appendChild(script);
    } else {
      initMap();
    }
  }, [activeApiKey, sensors, activePollutant, showRange]);

  if (!activeApiKey) {
    return (
      <div className="w-full h-full flex items-center justify-center p-6 bg-slate-950/90 text-center">
        <div className="max-w-md p-6 rounded-2xl bg-slate-900 border border-white/10 space-y-4">
          <div className="w-12 h-12 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center mx-auto text-cyan-400">
            <KeyRound className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white">Google Maps 3D Satellite Mode</h3>
          <p className="text-xs text-slate-400">
            Enter a Google Maps Platform API Key (or Google Maps Demo Key) to stream real-time Google Photorealistic 3D Hybrid Satellite tiles.
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Paste AIzaSy... key"
              value={apiKeyInput}
              onChange={e => setApiKeyInput(e.target.value)}
              className="flex-1 bg-slate-950 border border-white/20 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
            />
            <button
              onClick={() => setApiKeyInput(apiKeyInput.trim())}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-semibold transition-all"
            >
              Load 3D Map
            </button>
          </div>
          <p className="text-[11px] text-slate-500">
            Alternatively, toggle <strong className="text-cyan-400">"Photorealistic 3D Satellite"</strong> in the top-left menu to explore the built-in 3D model with zero key required.
          </p>
        </div>
      </div>
    );
  }

  if (mapError) {
    return (
      <div className="w-full h-full flex items-center justify-center p-6 bg-slate-950 text-center">
        <div className="p-6 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs space-y-2 max-w-sm">
          <ShieldAlert className="w-6 h-6 mx-auto text-red-400" />
          <p className="font-semibold">{mapError}</p>
          <p className="text-slate-400">Switching back to built-in 3D Satellite Terrain view is recommended.</p>
        </div>
      </div>
    );
  }

  return <div ref={mapContainerRef} className="w-full h-full" />;
}
