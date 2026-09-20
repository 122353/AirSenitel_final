import { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Layers3, MapPin, Minus, Plus, RotateCcw, Satellite } from 'lucide-react';
import { useMonitoring, pollutantLabel, valueLabel, latestMeasurement, freshMeasurement } from './data';

// MapLibre 6 ships a separate module worker. Let Vite bundle its shared imports.
maplibregl.setWorkerUrl(mapWorkerUrl);

export default function StationMap({ full = false }) {
  const { stations, selectedStation, setStationId, pollutant, mode, error } = useMonitoring();
  const container = useRef(null);
  const mapRef = useRef(null);
  const markers = useRef([]);
  const [mapError, setMapError] = useState('');
  const [ready, setReady] = useState(false);
  const [styleReady, setStyleReady] = useState(false);
  const [pitched, setPitched] = useState(true);
  const [satellite, setSatellite] = useState('off');
  const [imageryDate, setImageryDate] = useState(() => new Date(Date.now() - 3 * 86400000).toISOString().slice(0, 10));
  const [imageryError, setImageryError] = useState('');
  useEffect(() => {
    let map;
    let resizeObserver;
    try {
      map = new maplibregl.Map({
        container: container.current, style: 'https://tiles.openfreemap.org/styles/dark',
        center: [78.9629, 22.5937], zoom: 3.4, pitch: 35, bearing: -8,
        attributionControl: true, cooperativeGestures: true,
      });
      mapRef.current = map;
      setReady(true);
      resizeObserver = new ResizeObserver(() => map.resize());
      resizeObserver.observe(container.current);
      map.on('load', () => {
        setMapError('');
        setStyleReady(true);
        const sources = map.getStyle().sources;
        const source = Object.keys(sources).find(key => sources[key].type === 'vector');
        if (source && !map.getLayer('airsentinel-buildings')) map.addLayer({
          id: 'airsentinel-buildings', type: 'fill-extrusion', source, 'source-layer': 'building', minzoom: 13,
          paint: { 'fill-extrusion-color': '#243c42', 'fill-extrusion-height': ['coalesce', ['get', 'render_height'], 8], 'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], 0], 'fill-extrusion-opacity': 0.7 },
        });
      });
      map.on('error', event => {
        if (event.sourceId === 'nasa-context') setImageryError('NASA imagery is unavailable for this layer or date. Try an earlier date or turn the overlay off.');
        else if (!map.isStyleLoaded()) setMapError('Map tiles are unavailable. The station list remains accessible.');
      });
    } catch { setMapError('Interactive mapping is unavailable on this device. Use the station list below.'); }
    return () => { resizeObserver?.disconnect(); markers.current.forEach(marker => marker.remove()); map?.remove(); mapRef.current = null; };
  }, []);
  useEffect(() => {
    if (!mapRef.current || !ready) return;
    markers.current.forEach(marker => marker.remove());
    markers.current = stations.filter(s => (s.location_precision === 'station_point' || s.is_mobile === false) && Number.isFinite(s.latitude) && Number.isFinite(s.longitude)).map(station => {
      const measurement = latestMeasurement(station, pollutant);
      const fresh = freshMeasurement(measurement, mode, error);
      const selected = String(station.id) === String(selectedStation?.id);
      const element = document.createElement('button');
      element.className = `station-marker ${fresh ? 'fresh' : ''} ${selected ? 'selected' : ''}`;
      element.type = 'button';
      element.setAttribute('aria-label', `${station.name}: ${pollutantLabel(pollutant)} ${valueLabel(measurement?.value)} ${measurement?.unit || ''}. ${fresh ? 'Fresh reading' : station.latest_status === 'not_requested' ? 'Latest readings not queried yet' : 'No fresh reading'}. Select station.`);
      element.title = element.getAttribute('aria-label');
      element.addEventListener('click', () => setStationId(station.id));
      return new maplibregl.Marker({ element }).setLngLat([station.longitude, station.latitude]).addTo(mapRef.current);
    });
  }, [stations, selectedStation?.id, pollutant, mode, error, ready]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady) return;
    if (map.getLayer('nasa-context-layer')) map.removeLayer('nasa-context-layer');
    if (map.getSource('nasa-context')) map.removeSource('nasa-context');
    setImageryError('');
    if (satellite === 'off') return;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(imageryDate) || imageryDate < '2000-02-24' || imageryDate > new Date().toISOString().slice(0, 10)) { setImageryError('Choose a valid past observation date.'); return; }
    const aerosol = satellite === 'aerosol';
    const layer = aerosol ? 'MODIS_Terra_Aerosol_Optical_Depth_3km' : 'MODIS_Terra_CorrectedReflectance_TrueColor';
    const matrix = aerosol ? 'GoogleMapsCompatible_Level6' : 'GoogleMapsCompatible_Level9';
    const extension = aerosol ? 'png' : 'jpeg';
    map.addSource('nasa-context', { type: 'raster', tiles: [`https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${layer}/default/${imageryDate}/${matrix}/{z}/{y}/{x}.${extension}`], tileSize: 256, maxzoom: aerosol ? 6 : 9, attribution: '<a href="https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-standard-products/nasa-global-imagery-browse-services-gibs" target="_blank" rel="noopener noreferrer">NASA GIBS · MODIS Terra</a>' });
    const firstSymbol = map.getStyle().layers.find(item => item.type === 'symbol')?.id;
    map.addLayer({ id: 'nasa-context-layer', type: 'raster', source: 'nasa-context', paint: { 'raster-opacity': aerosol ? 0.68 : 0.92 } }, firstSymbol);
  }, [satellite, imageryDate, styleReady]);
  const togglePitch = () => { const next = !pitched; setPitched(next); mapRef.current?.easeTo({ pitch: next ? 50 : 0, bearing: next ? -12 : 0, duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 800 }); };
  return <div className={`station-map ${full ? 'map-full' : ''}`}>
    <div className="map-canvas" ref={container} role="region" aria-label="Interactive map of monitoring station locations across India" />
    <div className="map-coordinate"><span className="status-dot" /> INDIA NETWORK <span>6–38.5° N · 68–98.5° E</span></div>
    {full ? <div className="satellite-controls"><div><Satellite size={14} /><span>NASA SATELLITE CONTEXT</span></div><label><span className="sr-only">Satellite layer</span><select value={satellite} onChange={e => setSatellite(e.target.value)}><option value="off">Overlay off</option><option value="truecolor">MODIS Terra · true color</option><option value="aerosol">MODIS Terra · aerosol optical depth</option></select></label>{satellite !== 'off' ? <><label><span>Observation date (UTC)</span><input aria-label="Satellite observation date" type="date" min="2000-02-24" max={new Date().toISOString().slice(0, 10)} value={imageryDate} onChange={e => setImageryDate(e.target.value)} /></label><p>{satellite === 'aerosol' ? 'Column aerosol context (~3 km product). Not street-level PM₂.₅ or source proof.' : 'Dated satellite imagery. Clouds and observation gaps can obscure the surface.'}</p><a href="https://worldview.earthdata.nasa.gov/" target="_blank" rel="noreferrer">Source: NASA GIBS / Worldview ↗</a></> : null}{imageryError ? <p className="satellite-error" role="alert">{imageryError}</p> : null}</div> : null}
    <div className="map-tools"><button onClick={togglePitch} className={pitched ? 'active' : ''} title="Toggle pitched map" aria-label="Toggle pitched map" aria-pressed={pitched}><Layers3 size={16} /></button><button onClick={() => mapRef.current?.zoomIn()} aria-label="Zoom in"><Plus size={16} /></button><button onClick={() => mapRef.current?.zoomOut()} aria-label="Zoom out"><Minus size={16} /></button><button onClick={() => mapRef.current?.easeTo({ center: [78.9629, 22.5937], zoom: 3.4, duration: 0 })} aria-label="Reset map to India"><RotateCcw size={15} /></button></div>
    {mapError ? <div className="map-fallback"><MapPin size={26} /><p>{mapError}</p></div> : null}
    <div className="map-legend"><span><i className="legend-dot green" />Fresh station reading</span><span><i className="legend-dot muted" />Delayed / not yet queried</span></div>
    {!stations.length && !mapError ? <div className="map-empty">Station locations appear when the data service responds.</div> : null}
  </div>;
}
