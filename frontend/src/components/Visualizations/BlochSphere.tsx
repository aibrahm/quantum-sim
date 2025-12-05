import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Line, Text, Sphere } from '@react-three/drei';
import * as THREE from 'three';
import { useCircuitStore } from '../../stores/circuitStore';

interface BlochStateProps {
  x: number;
  y: number;
  z: number;
}

function BlochState({ x, y, z }: BlochStateProps) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.position.lerp(new THREE.Vector3(x, z, y), 0.1);
    }
  });

  const arrowPoints = useMemo(() => {
    return [new THREE.Vector3(0, 0, 0), new THREE.Vector3(x, z, y)];
  }, [x, y, z]);

  return (
    <group>
      <Line
        points={arrowPoints}
        color="#fff"
        lineWidth={2}
      />
      <mesh ref={meshRef} position={[x, z, y]}>
        <sphereGeometry args={[0.06, 8, 8]} />
        <meshBasicMaterial color="#fff" />
      </mesh>
    </group>
  );
}

function BlochSphereGeometry() {
  const { blochVectors, selectedQubit } = useCircuitStore();

  const displayQubit = selectedQubit ?? 0;
  const vector = blochVectors[displayQubit] || { x: 0, y: 0, z: 1 };

  return (
    <group>
      {/* Transparent sphere */}
      <Sphere args={[1, 16, 16]}>
        <meshBasicMaterial
          color="#111"
          transparent
          opacity={0.3}
          side={THREE.DoubleSide}
          wireframe
        />
      </Sphere>

      {/* Wireframe circles */}
      <group>
        {/* Equator */}
        <Line
          points={Array.from({ length: 65 }, (_, i) => {
            const theta = (i / 64) * 2 * Math.PI;
            return new THREE.Vector3(Math.cos(theta), 0, Math.sin(theta));
          })}
          color="#444"
          lineWidth={1}
        />

        {/* Vertical circle XZ */}
        <Line
          points={Array.from({ length: 65 }, (_, i) => {
            const theta = (i / 64) * 2 * Math.PI;
            return new THREE.Vector3(Math.cos(theta), Math.sin(theta), 0);
          })}
          color="#444"
          lineWidth={1}
        />

        {/* Vertical circle YZ */}
        <Line
          points={Array.from({ length: 65 }, (_, i) => {
            const theta = (i / 64) * 2 * Math.PI;
            return new THREE.Vector3(0, Math.sin(theta), Math.cos(theta));
          })}
          color="#444"
          lineWidth={1}
        />
      </group>

      {/* Axes */}
      <group>
        {/* X axis */}
        <Line
          points={[new THREE.Vector3(-1.2, 0, 0), new THREE.Vector3(1.2, 0, 0)]}
          color="#666"
          lineWidth={1}
        />
        <Text
          position={[1.4, 0, 0]}
          fontSize={0.12}
          color="#666"
        >
          X
        </Text>

        {/* Y axis */}
        <Line
          points={[new THREE.Vector3(0, 0, -1.2), new THREE.Vector3(0, 0, 1.2)]}
          color="#666"
          lineWidth={1}
        />
        <Text
          position={[0, 0, 1.4]}
          fontSize={0.12}
          color="#666"
        >
          Y
        </Text>

        {/* Z axis */}
        <Line
          points={[new THREE.Vector3(0, -1.2, 0), new THREE.Vector3(0, 1.2, 0)]}
          color="#666"
          lineWidth={1}
        />
        <Text
          position={[0, 1.4, 0]}
          fontSize={0.12}
          color="#fff"
        >
          |0⟩
        </Text>
        <Text
          position={[0, -1.4, 0]}
          fontSize={0.12}
          color="#fff"
        >
          |1⟩
        </Text>
      </group>

      {/* State vector */}
      <BlochState x={vector.x} y={vector.y} z={vector.z} />

      {/* Reference points */}
      <group>
        <mesh position={[0, 1, 0]}>
          <sphereGeometry args={[0.03, 6, 6]} />
          <meshBasicMaterial color="#444" />
        </mesh>
        <mesh position={[0, -1, 0]}>
          <sphereGeometry args={[0.03, 6, 6]} />
          <meshBasicMaterial color="#444" />
        </mesh>
        <mesh position={[1, 0, 0]}>
          <sphereGeometry args={[0.03, 6, 6]} />
          <meshBasicMaterial color="#444" />
        </mesh>
        <mesh position={[-1, 0, 0]}>
          <sphereGeometry args={[0.03, 6, 6]} />
          <meshBasicMaterial color="#444" />
        </mesh>
      </group>
    </group>
  );
}

export function BlochSphere() {
  const { nQubits, selectedQubit, setSelectedQubit, blochVectors } = useCircuitStore();
  const displayQubit = selectedQubit ?? 0;
  const vector = blochVectors[displayQubit] || { x: 0, y: 0, z: 1 };

  return (
    <div className="space-y-3 text-xs">
      {/* Qubit selector */}
      {nQubits > 1 && (
        <div className="flex gap-1">
          {Array.from({ length: nQubits }, (_, i) => (
            <button
              key={i}
              onClick={() => setSelectedQubit(i)}
              className={`px-2 py-1 border font-bold ${
                displayQubit === i
                  ? 'border-white bg-white text-black'
                  : 'border-gray-600 hover:border-white'
              }`}
            >
              Q{i}
            </button>
          ))}
        </div>
      )}

      {/* 3D Bloch sphere */}
      <div className="aspect-square border border-gray-700 bg-black">
        <Canvas camera={{ position: [2.5, 2, 2.5], fov: 45 }}>
          <BlochSphereGeometry />
          <OrbitControls
            enableZoom={true}
            enablePan={false}
            minDistance={2}
            maxDistance={6}
          />
        </Canvas>
      </div>

      {/* Coordinates */}
      <div className="grid grid-cols-3 gap-1">
        <div className="border border-gray-700 p-2 text-center">
          <div className="text-gray-600">X</div>
          <div className="font-bold">{vector.x.toFixed(3)}</div>
        </div>
        <div className="border border-gray-700 p-2 text-center">
          <div className="text-gray-600">Y</div>
          <div className="font-bold">{vector.y.toFixed(3)}</div>
        </div>
        <div className="border border-gray-700 p-2 text-center">
          <div className="text-gray-600">Z</div>
          <div className="font-bold">{vector.z.toFixed(3)}</div>
        </div>
      </div>
    </div>
  );
}
