import React from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Box } from '@react-three/drei';

const CityColumn = ({ city, index, total }) => {
  // Layout in a line or grid
  const x = (index - total / 2) * 2;
  const height = Math.max(0.5, city.pm25 / 20); // Scale height
  
  const color = city.risk === 'Critical' ? '#ef4444' : 
                city.risk === 'High' ? '#f97316' : 
                city.risk === 'Moderate' ? '#eab308' : '#22c55e';

  return (
    <group position={[x, 0, 0]}>
      {/* Base */}
      <Box args={[1, 0.2, 1]} position={[0, 0.1, 0]}>
        <meshStandardMaterial color="#334155" />
      </Box>
      
      {/* Data Column */}
      <Box args={[0.6, height, 0.6]} position={[0, height / 2 + 0.2, 0]}>
        <meshStandardMaterial color={color} transparent opacity={0.8} />
      </Box>
    </group>
  );
};

export default function PollutantColumns({ cities = [] }) {
  if (!cities.length) return null;

  return (
    <div className="w-full h-full absolute inset-0">
      <Canvas camera={{ position: [0, 10, 15], fov: 50 }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[5, 10, 5]} intensity={1} />
        
        <group position={[0, -2, 0]}>
          <gridHelper args={[50, 50, '#1e293b', '#0f172a']} />
          {cities.map((city, idx) => (
            <CityColumn key={city.name} city={city} index={idx} total={cities.length} />
          ))}
        </group>
        
        <OrbitControls enablePan={true} enableZoom={true} autoRotate autoRotateSpeed={0.5} />
      </Canvas>
    </div>
  );
}
