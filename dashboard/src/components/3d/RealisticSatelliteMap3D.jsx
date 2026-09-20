import React, { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html, Sphere, Cylinder, Text } from '@react-three/drei';
import * as THREE from 'three';
import { EFFECTIVE_RANGES, POLLUTANT_COLORS } from '../../utils/sensorRange';

// Geographic reference center for Delhi NCR (Connaught Place)
const DELHI_CENTER = { lat: 28.6139, lon: 77.2090 };

// Convert Lat/Lon to relative 3D coordinate space with realistic scale
export const geoTo3D = (lat, lon, scale = 180) => {
  const x = (lon - DELHI_CENTER.lon) * scale;
  const z = -(lat - DELHI_CENTER.lat) * scale;
  return [x, 0, z];
};

// Generate high-resolution procedural satellite texture with river, ridge & road grid
const useSatelliteTexture = () => {
  return useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 1024;
    const ctx = canvas.getContext('2d');

    // Base satellite terrain: deep urban slate/olive mix
    const bgGrad = ctx.createLinearGradient(0, 0, 1024, 1024);
    bgGrad.addColorStop(0, '#131b24');
    bgGrad.addColorStop(0.5, '#18242e');
    bgGrad.addColorStop(1, '#0e171e');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, 1024, 1024);

    // Urban settlement density textures
    ctx.fillStyle = '#22303c';
    for (let i = 0; i < 400; i++) {
      const rx = Math.random() * 1024;
      const ry = Math.random() * 1024;
      const rw = 15 + Math.random() * 40;
      const rh = 15 + Math.random() * 40;
      ctx.fillRect(rx, ry, rw, rh);
    }

    // Delhi Ridge Forest Cover (greenish-dark patches in central and southern sections)
    ctx.fillStyle = '#1b382b';
    ctx.beginPath();
    ctx.ellipse(480, 560, 140, 60, Math.PI / 4, 0, Math.PI * 2); // Central ridge
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(540, 780, 120, 80, -Math.PI / 6, 0, Math.PI * 2); // Southern ridge / Asola
    ctx.fill();

    // Yamuna River curve flowing from North-East to South-East
    ctx.strokeStyle = '#1e3a5f';
    ctx.lineWidth = 14;
    ctx.beginPath();
    ctx.moveTo(680, 0);
    ctx.bezierCurveTo(620, 300, 640, 500, 690, 700);
    ctx.bezierCurveTo(720, 820, 750, 940, 770, 1024);
    ctx.stroke();

    // Secondary river banks shimmer
    ctx.strokeStyle = '#2d5a88';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(680, 0);
    ctx.bezierCurveTo(620, 300, 640, 500, 690, 700);
    ctx.bezierCurveTo(720, 820, 750, 940, 770, 1024);
    ctx.stroke();

    // Ring Road & Highway network
    ctx.strokeStyle = '#3d4d5c';
    ctx.lineWidth = 3;

    // Outer Ring Road loop
    ctx.beginPath();
    ctx.ellipse(512, 512, 340, 320, 0, 0, Math.PI * 2);
    ctx.stroke();

    // Inner Ring Road loop
    ctx.strokeStyle = '#4a5e72';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.ellipse(512, 512, 200, 190, 0, 0, Math.PI * 2);
    ctx.stroke();

    // Radial Arterials (GT Road, Rohtak Road, NH48, Mathura Road)
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(512, 512); ctx.lineTo(150, 180); // Rohtak road NW
    ctx.moveTo(512, 512); ctx.lineTo(880, 220); // GT Road NE
    ctx.moveTo(512, 512); ctx.lineTo(240, 880); // NH48 SW to Gurgaon
    ctx.moveTo(512, 512); ctx.lineTo(820, 850); // Mathura road SE
    ctx.stroke();

    // Subtle coordinate grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
    ctx.lineWidth = 1;
    for (let x = 0; x <= 1024; x += 128) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, 1024); ctx.stroke();
    }
    for (let y = 0; y <= 1024; y += 128) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(1024, y); ctx.stroke();
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.ClampToEdgeWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    return texture;
  }, []);
};

// Rising 3D Hotspot Particle Stream
const HotspotParticleStream = ({ position, color }) => {
  const pointsRef = useRef();
  const particleCount = 45;

  const [positions, velocities] = useMemo(() => {
    const pos = new Float32Array(particleCount * 3);
    const vel = [];
    for (let i = 0; i < particleCount; i++) {
      pos[i * 3] = position[0] + (Math.random() - 0.5) * 1.2;
      pos[i * 3 + 1] = position[1] + Math.random() * 4.0;
      pos[i * 3 + 2] = position[2] + (Math.random() - 0.5) * 1.2;
      vel.push({
        vy: 0.03 + Math.random() * 0.04,
        vx: (Math.random() - 0.5) * 0.015,
        vz: (Math.random() - 0.5) * 0.015,
        maxHeight: position[1] + 6.0 + Math.random() * 4.0
      });
    }
    return [pos, vel];
  }, [position]);

  useFrame(() => {
    if (!pointsRef.current) return;
    const posAttr = pointsRef.current.geometry.attributes.position;
    for (let i = 0; i < particleCount; i++) {
      let y = posAttr.getY(i) + velocities[i].vy;
      let x = posAttr.getX(i) + velocities[i].vx;
      let z = posAttr.getZ(i) + velocities[i].vz;

      if (y > velocities[i].maxHeight) {
        y = position[1] + 0.2;
        x = position[0] + (Math.random() - 0.5) * 1.0;
        z = position[2] + (Math.random() - 0.5) * 1.0;
      }
      posAttr.setXYZ(i, x, y, z);
    }
    posAttr.needsUpdate = true;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={particleCount}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.22}
        color={color}
        transparent
        opacity={0.7}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
};

// Individual Monitoring Station Tower & Effective Radius Dome
const StationMarker3D = ({ sensor, activePollutant, showRange, isSelected, onClick }) => {
  const position = useMemo(() => geoTo3D(sensor.lat, sensor.lon), [sensor.lat, sensor.lon]);
  const pollutantColor = POLLUTANT_COLORS[activePollutant] || '#ef4444';
  
  // Physical effective radius scaled to 3D space: 1500m -> ~3.2 units, 3000m -> ~6.4 units
  const radiusScale = (EFFECTIVE_RANGES[activePollutant] || 1500) / 470;
  
  // Height proportional to PM2.5 or pollutant value
  const val = sensor.pm25 || 120;
  const pillarHeight = Math.min(12, Math.max(1.8, val / 25));

  const isHighAnomaly = val >= 250;

  return (
    <group position={position}>
      {/* Translucent Physical Effective Prediction Dome */}
      {showRange && (
        <Sphere args={[radiusScale, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2]}>
          <meshStandardMaterial
            color={pollutantColor}
            transparent
            opacity={isSelected ? 0.35 : 0.16}
            roughness={0.2}
            metalness={0.1}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </Sphere>
      )}

      {/* Ground Footprint Ring */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.05, 0]}>
        <ringGeometry args={[radiusScale * 0.96, radiusScale, 32]} />
        <meshBasicMaterial color={pollutantColor} transparent opacity={0.6} side={THREE.DoubleSide} />
      </mesh>

      {/* Sensor Station Base Beacon */}
      <Cylinder 
        args={[0.3, 0.45, 0.4, 16]} 
        position={[0, 0.2, 0]}
        onClick={(e) => { e.stopPropagation(); onClick(sensor); }}
      >
        <meshStandardMaterial color="#0f172a" metalness={0.8} roughness={0.2} />
      </Cylinder>

      {/* Vertical Concentration Pillar */}
      <Cylinder 
        args={[0.15, 0.22, pillarHeight, 16]} 
        position={[0, pillarHeight / 2 + 0.2, 0]}
        onClick={(e) => { e.stopPropagation(); onClick(sensor); }}
      >
        <meshStandardMaterial 
          color={pollutantColor} 
          emissive={pollutantColor} 
          emissiveIntensity={isSelected ? 0.8 : 0.4} 
          roughness={0.3}
        />
      </Cylinder>

      {/* Top Beacon Orb */}
      <Sphere 
        args={[0.32, 16, 16]} 
        position={[0, pillarHeight + 0.35, 0]}
        onClick={(e) => { e.stopPropagation(); onClick(sensor); }}
      >
        <meshStandardMaterial 
          color="#ffffff" 
          emissive={pollutantColor} 
          emissiveIntensity={1.0}
        />
      </Sphere>

      {/* Active Hotspot Plume */}
      {isHighAnomaly && (
        <HotspotParticleStream position={[0, pillarHeight + 0.2, 0]} color={pollutantColor} />
      )}

      {/* Station Title Label */}
      <Html position={[0, pillarHeight + 0.9, 0]} center distanceFactor={22}>
        <div 
          onClick={() => onClick(sensor)}
          className={`px-2 py-1 rounded-md text-[10px] font-bold whitespace-nowrap cursor-pointer transition-all ${
            isSelected 
              ? 'bg-cyan-500 text-slate-950 shadow-[0_0_15px_rgba(6,182,212,0.8)] scale-110' 
              : 'bg-slate-950/80 text-white border border-white/20 hover:border-cyan-400'
          }`}
        >
          {sensor.name} • {val} µg/m³
        </div>
      </Html>
    </group>
  );
};

export default function RealisticSatelliteMap3D({ 
  sensors = [], 
  activePollutant = 'pm25', 
  showRange = true, 
  selectedSensor = null, 
  onSensorClick 
}) {
  const satelliteTexture = useSatelliteTexture();
  const controlsRef = useRef();

  return (
    <div className="w-full h-full relative cursor-grab active:cursor-grabbing">
      <Canvas
        camera={{ position: [0, 24, 28], fov: 45 }}
        gl={{ antialias: true, alpha: false }}
        onCreated={({ gl, scene }) => {
          gl.setClearColor(new THREE.Color('#090d14'));
          scene.fog = new THREE.FogExp2('#090d14', 0.015);
        }}
      >
        <ambientLight intensity={0.7} />
        <directionalLight position={[20, 40, 20]} intensity={1.2} castShadow />
        <pointLight position={[0, 15, 0]} intensity={0.8} color="#06b6d4" distance={50} />

        {/* Photorealistic Satellite Ground Plane of Delhi NCR */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
          <planeGeometry args={[70, 70, 64, 64]} />
          <meshStandardMaterial
            map={satelliteTexture}
            roughness={0.8}
            metalness={0.15}
          />
        </mesh>

        {/* Ambient Geographic Grid Outline */}
        <gridHelper args={[70, 35, '#06b6d4', '#1e293b']} position={[0, 0.02, 0]} />

        {/* Render all monitoring stations */}
        {sensors.map((sensor) => (
          <StationMarker3D
            key={sensor.id || sensor.name}
            sensor={sensor}
            activePollutant={activePollutant}
            showRange={showRange}
            isSelected={selectedSensor?.id === sensor.id || selectedSensor?.name === sensor.name}
            onClick={onSensorClick}
          />
        ))}

        <OrbitControls
          ref={controlsRef}
          enableDamping
          dampingFactor={0.06}
          maxPolarAngle={Math.PI / 2.05} // Prevent camera clipping below ground
          minDistance={10}
          maxDistance={65}
        />
      </Canvas>
    </div>
  );
}
