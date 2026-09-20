import { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Layers3, Minus, Plus, RotateCcw } from 'lucide-react';
import { pollutantLabel, valueLabel } from './data';

maplibregl.setWorkerUrl(mapWorkerUrl);

export default function IndiaCoverageMap({ cities = [], selected, pollutant, onSelect }) {
  const container = useRef(null);
  const mapRef = useRef(null);
  const markers = useRef([]);
  const [ready, setReady] = useState(false);
  const [mapError, setMapError] = useState('');
  const [pitched, setPitched] = useState(true);

  useEffect(() => {
    let map;
    let resizeObserver;
    try {
      map = new maplibregl.Map({
        container: container.current,
        style: 'https://tiles.openfreemap.org/styles/dark',
        center: [79.2, 22.8], zoom: 3.4, pitch: 28, bearing: -5,
        attributionControl: true, cooperativeGestures: true,
      });
      mapRef.current = map;
      resizeObserver = new ResizeObserver(() => map.resize());
      resizeObserver.observe(container.current);
      map.on('load', () => { setReady(true); setMapError(''); });
      map.on('error', () => { if (!map.isStyleLoaded()) setMapError('Map tiles are unavailable. The national watchlist remains available below.'); });
    } catch {
      setMapError('Interactive mapping is unavailable on this device.');
    }
    return () => { resizeObserver?.disconnect(); markers.current.forEach(marker => marker.remove()); map?.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    if (!ready || !mapRef.current) return;
    markers.current.forEach(marker => marker.remove());
    const mapped = [...cities];
    if (selected && !mapped.some(city => Math.abs(city.latitude - selected.latitude) < 0.0001 && Math.abs(city.longitude - selected.longitude) < 0.0001)) {
      mapped.push({ ...selected, name: selected.label, selectedSearch: true });
    }
    markers.current = mapped.filter(city => Number.isFinite(city.latitude) && Number.isFinite(city.longitude)).map(city => {
      const warning = city.risk === 'model_spike_watch';
      const isSelected = selected && Math.abs(city.latitude - selected.latitude) < 0.0001 && Math.abs(city.longitude - selected.longitude) < 0.0001;
      const element = document.createElement('button');
      element.type = 'button';
      element.className = `india-marker ${warning ? 'warning' : ''} ${isSelected ? 'selected' : ''} ${city.selectedSearch ? 'searched' : ''}`;
      const value = city.model?.value;
      element.setAttribute('aria-label', `${city.name}: ${pollutantLabel(pollutant)} ${valueLabel(value)} ${city.model?.unit || ''}. ${warning ? 'Model spike watch.' : 'No model spike signal.'}`);
      element.title = element.getAttribute('aria-label');
      element.addEventListener('click', () => onSelect?.({ label: `${city.name}${city.state ? `, ${city.state}` : ''}`, latitude: city.latitude, longitude: city.longitude }));
      return new maplibregl.Marker({ element }).setLngLat([city.longitude, city.latitude]).addTo(mapRef.current);
    });
  }, [cities, selected, pollutant, onSelect, ready]);

  useEffect(() => {
    if (!mapRef.current || !selected?.focus || !Number.isFinite(selected.latitude) || !Number.isFinite(selected.longitude)) return;
    mapRef.current.easeTo({ center: [selected.longitude, selected.latitude], zoom: Math.max(mapRef.current.getZoom(), 7), duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 700 });
  }, [selected]);

  const togglePitch = () => {
    const next = !pitched;
    setPitched(next);
    mapRef.current?.easeTo({ pitch: next ? 42 : 0, bearing: next ? -7 : 0, duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 700 });
  };

  return <div className="station-map india-map">
    <div className="map-canvas" ref={container} role="region" aria-label="Interactive map of the VayuNirikshak India model watchlist" />
    <div className="map-coordinate"><span className="status-dot" /> INDIA <span>National screening · select a city</span></div>
    <div className="map-tools"><button onClick={togglePitch} className={pitched ? 'active' : ''} aria-label="Toggle pitched map"><Layers3 size={16} /></button><button onClick={() => mapRef.current?.zoomIn()} aria-label="Zoom in"><Plus size={16} /></button><button onClick={() => mapRef.current?.zoomOut()} aria-label="Zoom out"><Minus size={16} /></button><button onClick={() => mapRef.current?.easeTo({ center: [79.2, 22.8], zoom: 3.4, pitch: 28, bearing: -5, duration: 0 })} aria-label="Reset map to India"><RotateCcw size={15} /></button></div>
    <div className="map-legend"><span><i className="legend-dot green" />Model estimate</span><span><i className="legend-dot amber" />Forecast rise to verify</span><span><i className="india-selected-dot" />Selected place</span></div>
    {mapError ? <div className="map-fallback"><p>{mapError}</p></div> : null}
  </div>;
}
