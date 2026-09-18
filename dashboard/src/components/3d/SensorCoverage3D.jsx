import React, { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html, Sphere, Cylinder } from '@react-three/drei';
import * as THREE from 'three';
import { EFFECTIVE_RANGES } from '../../utils/sensorRange';
import { POLLUTANT_COLORS } from '../../utils/pollutantThresholds';

// Delhi base coordinates roughly at center for relative mapping
const CENTER = { lat: 28.6139, lon: 77.2090 };

// Convert Lat/Lon to relative 3D space coordinates (approximate scaling)
const getRelativePos = (lat, lon, scale = 200) => {
  const x = (lon - CENTER.lon) * scale;
  const z = -(lat - CENTER.lat) * scale; // Negative because WebGL Z goes into screen
  return [x, 0, z];
};

const ParticleSystem = ({ position, severity }) => {
  const particlesRef = useRef();
  
  const particles = useMemo(() => {
    const temp = [];
    const count = severity === 'critical' ? 50 : severity === 'very_high' ? 30 : 10;
    for (let i = 0; i < count; i++) {
      temp.push({
        x: (Math.random() - 0.5) * 2,
        y: Math.random() * 5,
        z: (Math.random() - 0.5) * 2,
        speed: 0.02 + Math.random() * 0.05
      });
    }
    return temp;
  }, [severity]);

  useFrame(() => {
    if (particlesRef.current) {
      particlesRef.current.children.forEach((child, i) => {
        child.position.y += particles[i].speed;
        if (child.position.y > 10) child.position.y = 0;
      });
    }
  });

  if (severity === 'low' || severity === 'moderate') return null;

  const color = severity === 'critical' ? '#ef4444' : '#f97316';

  return (
    <group position={position} ref={particlesRef}>
      {particles.map((p, i) => (
        <mesh key={i} position={[p.x, p.y, p.z]}>
          <sphereGeometry args={[0.05, 8, 8]} />
          <meshBasicMaterial color={color} transparent opacity={0.6} />
        </mesh>
      ))}
    </group>
  );
};

const SensorNode = ({ sensor, activePollutant, showRange, onClick }) => {
  const [hovered, setHovered] = useState(false);
  const pos = getRelativePos(sensor.lat, sensor.lon);
  
  // Height based on PM2.5 (normalized)
  const height = Math.max(0.5, (sensor.pm25 || 50) / 20);
  const color = sensor.severity === 'critical' ? '#ef4444' : 
                sensor.severity === 'very_high' ? '#f97316' : 
                sensor.severity === 'high' ? '#eab308' : 
                '#22c55e';

  // Range dome color and radius
  const domeColor = POLLUTANT_COLORS?.[activePollutant] || '#3b82f6';
  const rangeRadius = ((EFFECTIVE_RANGES?.[activePollutant] || 2000) / 1000) * 1.5; // Scale radius

  return (
    <group position={pos} onClick={(e) => { e.stopPropagation(); onClick(sensor); }} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)}>
      {/* Pillar */}
      <Cylinder args={[0.2, 0.2, height, 16]} position={[0, height / 2, 0]}>
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} />
      </Cylinder>
      
      {/* Base Node */}
      <Sphere args={[0.4, 32, 32]} position={[0, 0, 0]}>
        <meshStandardMaterial color="#ffffff" emissive="#ffffff" emissiveIntensity={0.8} />
      </Sphere>
      
      {/* Effective Range Dome */}
      {showRange && (
        <Sphere args={[rangeRadius, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2]} position={[0, 0, 0]}>
          <meshBasicMaterial color={domeColor} transparent opacity={0.15} wireframe={hovered} side={THREE.DoubleSide} />
        </Sphere>
      )}

      {/* Particles for high pollution */}
      <ParticleSystem position={[0, height, 0]} severity={sensor.severity} />

      {/* Tooltip on hover */}
      {hovered && (
        <Html position={[0, height + 1, 0]} center zIndexRange={[100, 0]}>
          <div className="bg-slate-900/90 backdrop-blur text-white px-3 py-2 rounded-lg shadow-xl border border-white/20 whitespace-nowrap pointer-events-none transform -translate-y-full">
            <div className="font-bold">{sensor.name}</div>
            <div className="text-sm text-slate-300">PM2.5: <span style={{ color }}>{sensor.pm25} µg/m³</span></div>
          </div>
        </Html>
      )}
    </group>
  );
};

const TerrainGrid = () => (
  <gridHelper args={[100, 100, '#1e293b', '#0f172a']} position={[0, -0.1, 0]}>
    <meshBasicMaterial transparent opacity={0.3} />
  </gridHelper>
);

export default function SensorCoverage3D({ sensors, activePollutant = 'pm25', showRange = true, onSensorClick }) {
  return (
    <div className="w-full h-full absolute inset-0 cursor-move">
      <Canvas camera={{ position: [0, 20, 25], fov: 45 }}>
        <color attach="background" args={['#020617']} />
        <fog attach="fog" args={['#020617', 20, 60]} />
        
        <ambientLight intensity={0.2} />
        <directionalLight position={[10, 20, 10]} intensity={1.5} color="#ffffff" />
        <pointLight position={[0, 5, 0]} intensity={2} color="#06b6d4" distance={50} />

        <TerrainGrid />
        
        {sensors.map(sensor => (
          <SensorNode 
            key={sensor.id} 
            sensor={sensor} 
            activePollutant={activePollutant} 
            showRange={showRange} 
            onClick={onSensorClick} 
          />
        ))}

        <OrbitControls 
          enablePan={true} 
          enableZoom={true} 
          maxPolarAngle={Math.PI / 2 - 0.05} // Prevent going under ground
          minDistance={5}
          maxDistance={50}
          autoRotate={true}
          autoRotateSpeed={0.5}
        />
      </Canvas>
    </div>
  );
}
