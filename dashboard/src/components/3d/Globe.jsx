import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere, Html } from '@react-three/drei';
import * as THREE from 'three';

const BRICS_NATIONS = [
  { name: 'India', lat: 20.59, lon: 78.96, color: '#f97316' },
  { name: 'China', lat: 35.86, lon: 104.19, color: '#ef4444' },
  { name: 'Brazil', lat: -14.23, lon: -51.92, color: '#22c55e' },
  { name: 'Russia', lat: 61.52, lon: 105.31, color: '#3b82f6' },
  { name: 'South Africa', lat: -30.55, lon: 22.93, color: '#eab308' }
];

// Convert Lat/Lon to 3D Sphere coordinates
const getSpherePos = (lat, lon, radius = 5) => {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);

  const x = -(radius * Math.sin(phi) * Math.cos(theta));
  const z = (radius * Math.sin(phi) * Math.sin(theta));
  const y = (radius * Math.cos(phi));

  return [x, y, z];
};

const Node = ({ nation }) => {
  const pos = getSpherePos(nation.lat, nation.lon, 5.1);
  return (
    <group position={pos}>
      <Sphere args={[0.2, 16, 16]}>
        <meshStandardMaterial color={nation.color} emissive={nation.color} emissiveIntensity={2} />
      </Sphere>
      {/* Pulse effect */}
      <Sphere args={[0.3, 16, 16]}>
        <meshBasicMaterial color={nation.color} transparent opacity={0.3} />
      </Sphere>
      <Html position={[0, 0.4, 0]} center>
        <div className="bg-slate-900/80 backdrop-blur-sm border border-white/10 px-2 py-1 rounded text-xs text-white font-medium whitespace-nowrap">
          {nation.name}
        </div>
      </Html>
    </group>
  );
};

const Arc = ({ start, end }) => {
  const startPos = new THREE.Vector3(...getSpherePos(start.lat, start.lon, 5.1));
  const endPos = new THREE.Vector3(...getSpherePos(end.lat, end.lon, 5.1));
  
  // Create a quadratic bezier curve for the arc
  const midPoint = new THREE.Vector3().addVectors(startPos, endPos).multiplyScalar(0.5);
  midPoint.normalize().multiplyScalar(5.1 + startPos.distanceTo(endPos) * 0.2); // Arch height based on distance
  
  const curve = new THREE.QuadraticBezierCurve3(startPos, midPoint, endPos);
  const points = curve.getPoints(50);
  const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);

  return (
    <line geometry={lineGeometry}>
      <lineBasicMaterial color="#06b6d4" transparent opacity={0.4} />
    </line>
  );
};

const Earth = () => {
  const earthRef = useRef();
  
  useFrame(() => {
    if (earthRef.current) {
      earthRef.current.rotation.y += 0.002;
    }
  });

  // Generate arcs connecting India to others (Federated Hub)
  const arcs = [];
  const india = BRICS_NATIONS.find(n => n.name === 'India');
  BRICS_NATIONS.forEach(nation => {
    if (nation.name !== 'India') {
      arcs.push(<Arc key={nation.name} start={india} end={nation} />);
    }
  });

  return (
    <group ref={earthRef}>
      {/* Wireframe Globe */}
      <Sphere args={[5, 32, 32]}>
        <meshBasicMaterial color="#1e293b" wireframe transparent opacity={0.3} />
      </Sphere>
      
      {/* Nodes */}
      {BRICS_NATIONS.map(nation => <Node key={nation.name} nation={nation} />)}
      
      {/* Connections */}
      {arcs}
    </group>
  );
};

export default function Globe() {
  return (
    <div className="w-full h-full absolute inset-0 cursor-move">
      <Canvas camera={{ position: [0, 0, 15], fov: 45 }}>
        <color attach="background" args={['transparent']} />
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1} color="#ffffff" />
        
        <Earth />
        
        <OrbitControls enablePan={false} enableZoom={true} minDistance={8} maxDistance={20} />
      </Canvas>
    </div>
  );
}
