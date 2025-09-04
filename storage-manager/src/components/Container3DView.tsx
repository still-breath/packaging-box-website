// src/components/Container3DView.tsx
import React, { useMemo } from 'react';
import { Canvas, useLoader } from '@react-three/fiber';
import { OrbitControls, Box, Edges, Grid, Environment, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';
import { PlacedBox, Container } from '../types/types';

interface Container3DViewProps {
  items: PlacedBox[];
  containerDimensions: Container;
  settings: any;
  visibleItems: { [id: string]: boolean };
}

// Wooden Box Component
const WoodenBox = ({ position, size, color, showEdges }: any) => {
    const [width, height, depth] = size;
    
    // Create wood texture procedurally
    const woodTexture = useMemo(() => {
        const canvas = document.createElement('canvas');
        canvas.width = 512;
        canvas.height = 512;
        const context = canvas.getContext('2d')!;
        
        // Base wood color
        const baseColor = new THREE.Color(color || '#8B4513');
        context.fillStyle = `rgb(${Math.floor(baseColor.r * 255)}, ${Math.floor(baseColor.g * 255)}, ${Math.floor(baseColor.b * 255)})`;
        context.fillRect(0, 0, 512, 512);
        
        // Add wood grain
        for (let i = 0; i < 100; i++) {
            const darkerColor = baseColor.clone().multiplyScalar(0.7 + Math.random() * 0.2);
            context.strokeStyle = `rgb(${Math.floor(darkerColor.r * 255)}, ${Math.floor(darkerColor.g * 255)}, ${Math.floor(darkerColor.b * 255)})`;
            context.lineWidth = Math.random() * 3 + 1;
            context.beginPath();
            context.moveTo(0, Math.random() * 512);
            context.lineTo(512, Math.random() * 512);
            context.stroke();
        }
        
        const texture = new THREE.CanvasTexture(canvas);
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        texture.repeat.set(2, 2);
        return texture;
    }, [color]);

    const plankWidth = 0.15; // Width of each wooden plank
    const numPlanks = Math.ceil(width / plankWidth);
    const actualPlankWidth = width / numPlanks;

    return (
        <group position={position}>
            {/* Main box structure */}
            <Box args={[width, height, depth]} castShadow receiveShadow>
                <meshLambertMaterial 
                    map={woodTexture}
                    color={color || '#8B4513'}
                />
            </Box>

            {/* Wooden planks on front face */}
            {Array.from({ length: numPlanks }).map((_, i) => (
                <Box
                    key={`front-plank-${i}`}
                    args={[actualPlankWidth * 0.98, height + 0.01, 0.01]}
                    position={[
                        -width/2 + actualPlankWidth/2 + i * actualPlankWidth,
                        0,
                        depth/2 + 0.005
                    ]}
                    castShadow
                >
                    <meshLambertMaterial 
                        color={new THREE.Color(color || '#8B4513').multiplyScalar(0.9)}
                    />
                </Box>
            ))}

            {/* Wooden planks on back face */}
            {Array.from({ length: numPlanks }).map((_, i) => (
                <Box
                    key={`back-plank-${i}`}
                    args={[actualPlankWidth * 0.98, height + 0.01, 0.01]}
                    position={[
                        -width/2 + actualPlankWidth/2 + i * actualPlankWidth,
                        0,
                        -depth/2 - 0.005
                    ]}
                    castShadow
                >
                    <meshLambertMaterial 
                        color={new THREE.Color(color || '#8B4513').multiplyScalar(0.9)}
                    />
                </Box>
            ))}

            {/* Metal corner brackets */}
            {[
                [-width/2, height/2, depth/2],
                [width/2, height/2, depth/2],
                [-width/2, -height/2, depth/2],
                [width/2, -height/2, depth/2],
                [-width/2, height/2, -depth/2],
                [width/2, height/2, -depth/2],
                [-width/2, -height/2, -depth/2],
                [width/2, -height/2, -depth/2],
            ].map((cornerPos, idx) => (
                <Box
                    key={`bracket-${idx}`}
                    args={[0.02, 0.02, 0.02]}
                    position={cornerPos as [number, number, number]}
                    castShadow
                >
                    <meshStandardMaterial 
                        color="#404040"
                        metalness={0.8}
                        roughness={0.3}
                    />
                </Box>
            ))}

            {/* Wooden frame edges */}
            {showEdges && (
                <group>
                    {/* Top frame */}
                    <Box
                        args={[width + 0.02, 0.02, 0.02]}
                        position={[0, height/2 + 0.01, depth/2 + 0.01]}
                        castShadow
                    >
                        <meshLambertMaterial color={new THREE.Color(color || '#8B4513').multiplyScalar(0.6)} />
                    </Box>
                    <Box
                        args={[width + 0.02, 0.02, 0.02]}
                        position={[0, height/2 + 0.01, -depth/2 - 0.01]}
                        castShadow
                    >
                        <meshLambertMaterial color={new THREE.Color(color || '#8B4513').multiplyScalar(0.6)} />
                    </Box>

                    {/* Bottom frame */}
                    <Box
                        args={[width + 0.02, 0.02, 0.02]}
                        position={[0, -height/2 - 0.01, depth/2 + 0.01]}
                        castShadow
                    >
                        <meshLambertMaterial color={new THREE.Color(color || '#8B4513').multiplyScalar(0.6)} />
                    </Box>
                    <Box
                        args={[width + 0.02, 0.02, 0.02]}
                        position={[0, -height/2 - 0.01, -depth/2 - 0.01]}
                        castShadow
                    >
                        <meshLambertMaterial color={new THREE.Color(color || '#8B4513').multiplyScalar(0.6)} />
                    </Box>

                    {/* Vertical frame edges */}
                    <Box
                        args={[0.02, height + 0.04, 0.02]}
                        position={[-width/2 - 0.01, 0, depth/2 + 0.01]}
                        castShadow
                    >
                        <meshLambertMaterial color={new THREE.Color(color || '#8B4513').multiplyScalar(0.6)} />
                    </Box>
                    <Box
                        args={[0.02, height + 0.04, 0.02]}
                        position={[width/2 + 0.01, 0, depth/2 + 0.01]}
                        castShadow
                    >
                        <meshLambertMaterial color={new THREE.Color(color || '#8B4513').multiplyScalar(0.6)} />
                    </Box>
                </group>
            )}
        </group>
    );
};

const Container3DView = ({ items, containerDimensions, settings, visibleItems }: Container3DViewProps) => {
    const scale = 0.01; 

    const scaledContainer = {
        width: containerDimensions.length * scale,
        height: containerDimensions.height * scale,
        depth: containerDimensions.width * scale,
    };

    const itemsToRender = items.filter(item => visibleItems[item.id]);

    return (
        <Canvas 
            camera={{ 
                position: [scaledContainer.width * 2, scaledContainer.height * 2.5, scaledContainer.depth * 2], 
                fov: 50 
            }}
            shadows
            gl={{ antialias: true, alpha: true, shadowMapType: THREE.PCFSoftShadowMap }}
            style={{ background: 'linear-gradient(135deg, #2c3e50 0%, #34495e 100%)' }}
        >
            {/* Warehouse-style lighting */}
            {settings.addLights && <>
                <ambientLight intensity={0.3} color="#f4f1de" />
                <directionalLight 
                    position={[30, 40, 20]} 
                    intensity={2} 
                    color="#ffffff"
                    castShadow
                    shadow-mapSize-width={4096}
                    shadow-mapSize-height={4096}
                    shadow-camera-far={200}
                    shadow-camera-left={-30}
                    shadow-camera-right={30}
                    shadow-camera-top={30}
                    shadow-camera-bottom={-30}
                    shadow-bias={-0.0001}
                />
                <directionalLight 
                    position={[-20, 30, -15]} 
                    intensity={1} 
                    color="#ffd89b"
                    castShadow
                />
                <spotLight
                    position={[0, scaledContainer.height * 3, 0]}
                    angle={0.4}
                    penumbra={0.8}
                    intensity={1.5}
                    color="#fff8dc"
                    castShadow
                    shadow-mapSize-width={2048}
                    shadow-mapSize-height={2048}
                />
            </>}
            
            {/* Container with industrial look */}
            {settings.showContainer && (
                <group>
                    <Box 
                        args={[scaledContainer.width, scaledContainer.height, scaledContainer.depth]}
                        receiveShadow
                    >
                        <meshStandardMaterial 
                            color="#34495e"
                            transparent 
                            opacity={0.2}
                            roughness={0.8}
                            metalness={0.1}
                        />
                        {settings.showContainerEdges && (
                            <Edges 
                                color="#e74c3c" 
                                lineWidth={3}
                                threshold={15}
                            />
                        )}
                    </Box>
                </group>
            )}

            {/* Wooden boxes */}
            {settings.showGoods && itemsToRender.map((item) => {
                const scaledItem = { 
                    width: item.length * scale,
                    height: item.height * scale,
                    depth: item.width * scale,
                };

                const boxCenterX = item.x + (item.length / 2);
                const boxCenterY = item.z + (item.height / 2);
                const boxCenterZ = item.y + (item.width / 2);

                const position: [number, number, number] = [
                    (boxCenterX - containerDimensions.length / 2) * scale,
                    (boxCenterY - containerDimensions.height / 2) * scale,
                    (boxCenterZ - containerDimensions.width / 2) * scale,
                ];

                return (
                    <WoodenBox
                        key={item.id}
                        position={position}
                        size={[scaledItem.width, scaledItem.height, scaledItem.depth]}
                        color={item.color}
                        showEdges={settings.showGoodEdges}
                    />
                );
            })}
            
            {/* Industrial floor grid */}
            {settings.showBaseGrid && (
                <Grid 
                    infiniteGrid 
                    position={[0, -scaledContainer.height / 2 - 0.01, 0]}
                    args={[100, 100]}
                    cellSize={1}
                    cellThickness={1}
                    cellColor="#7f8c8d"
                    sectionSize={10}
                    sectionThickness={2}
                    sectionColor="#95a5a6"
                    fadeDistance={50}
                    fadeStrength={1}
                />
            )}

            {/* Enhanced shadows */}
            <ContactShadows 
                position={[0, -scaledContainer.height / 2, 0]}
                opacity={0.5}
                scale={scaledContainer.width * 3}
                blur={3}
                far={scaledContainer.height * 2}
                color="#2c3e50"
            />

            {/* Industrial environment */}
            <Environment preset="warehouse" background={false} />
            
            <OrbitControls 
                enablePan={true}
                enableZoom={true}
                enableRotate={true}
                minDistance={scaledContainer.width * 0.8}
                maxDistance={scaledContainer.width * 5}
                autoRotate={false}
                dampingFactor={0.08}
                enableDamping={true}
                maxPolarAngle={Math.PI * 0.8}
                minPolarAngle={Math.PI * 0.1}
            />
        </Canvas>
    );
};

export default Container3DView;