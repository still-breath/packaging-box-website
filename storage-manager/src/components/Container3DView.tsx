// src/components/Container3DView.tsx
import React from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Box, Edges, Grid, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';
import { PlacedBox, Container } from '../types/types';

interface Container3DViewProps {
  items: PlacedBox[];
  containerDimensions: Container;
  settings: any;
  visibleItems: { [id: string]: boolean };
    animationIndex?: number;
    animationProgress?: number; // 0..1
}

// Clean Wooden Crate Component
const WoodenCrate = ({ position, size, color, showEdges, opacity = 1 }: any) => {
    const [width, height, depth] = size;
    const woodColor = '#D2B48C';
    const labelColor = color || '#FF1493';
    const useTransparent = opacity < 1;

    return (
        <group position={position}>
            <Box args={[width, height, depth]} castShadow receiveShadow>
                <meshLambertMaterial 
                    color={woodColor}
                    {...(useTransparent ? { transparent: true, opacity } : {})}
                />
            </Box>

            {Array.from({ length: 4 }).map((_, i) => (
                <Box
                    key={`front-slat-${i}`}
                    args={[width * 0.95, height * 0.18, 0.005]}
                    position={[
                        0,
                        -height/2 + height * 0.12 + i * (height * 0.22),
                        depth/2 + 0.0025
                    ]}
                    castShadow
                >
                    <meshLambertMaterial 
                        color={new THREE.Color(woodColor).multiplyScalar(0.95)}
                        {...(useTransparent ? { transparent: true, opacity } : {})}
                    />
                </Box>
            ))}

            {Array.from({ length: 4 }).map((_, i) => (
                <Box
                    key={`back-slat-${i}`}
                    args={[width * 0.95, height * 0.18, 0.005]}
                    position={[
                        0,
                        -height/2 + height * 0.12 + i * (height * 0.22),
                        -depth/2 - 0.0025
                    ]}
                    castShadow
                >
                    <meshLambertMaterial 
                        color={new THREE.Color(woodColor).multiplyScalar(0.95)}
                    />
                </Box>
            ))}

            {Array.from({ length: 4 }).map((_, i) => (
                <Box
                    key={`left-slat-${i}`}
                    args={[0.005, height * 0.18, depth * 0.95]}
                    position={[
                        -width/2 - 0.0025,
                        -height/2 + height * 0.12 + i * (height * 0.22),
                        0
                    ]}
                    castShadow
                >
                    <meshLambertMaterial 
                        color={new THREE.Color(woodColor).multiplyScalar(0.95)}
                    />
                </Box>
            ))}

            {Array.from({ length: 4 }).map((_, i) => (
                <Box
                    key={`right-slat-${i}`}
                    args={[0.005, height * 0.18, depth * 0.95]}
                    position={[
                        width/2 + 0.0025,
                        -height/2 + height * 0.12 + i * (height * 0.22),
                        0
                    ]}
                    castShadow
                >
                    <meshLambertMaterial 
                        color={new THREE.Color(woodColor).multiplyScalar(0.95)}
                    />
                </Box>
            ))}

            <Box
                args={[width * 0.3, height * 0.2, 0.002]}
                position={[width * 0.25, height * 0.2, depth/2 + 0.01]}
                castShadow
            >
                <meshLambertMaterial color={labelColor} {...(useTransparent ? { transparent: true, opacity } : {})} />
            </Box>

            <Box
                args={[0.002, height * 0.2, depth * 0.3]}
                position={[width/2 + 0.01, height * 0.2, 0]}
                castShadow
            >
                <meshLambertMaterial color={labelColor} {...(useTransparent ? { transparent: true, opacity } : {})} />
            </Box>

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
                    args={[0.015, 0.015, 0.015]}
                    position={cornerPos as [number, number, number]}
                    castShadow
                >
                    <meshStandardMaterial 
                        color="#696969"
                        metalness={0.7}
                        roughness={0.4}
                        {...(useTransparent ? { transparent: true, opacity } : {})}
                    />
                </Box>
            ))}

            {showEdges && (
                <Edges 
                    color="#8B4513" 
                    lineWidth={1}
                    threshold={10}
                />
            )}
        </group>
    );
};

const Container3DView = ({ items, containerDimensions, settings, visibleItems, animationIndex = Number.MAX_SAFE_INTEGER, animationProgress = 1 }: Container3DViewProps) => {
    const scale = 0.01; 

    const scaledContainer = {
        width: containerDimensions.length * scale,
        height: containerDimensions.height * scale,
        depth: containerDimensions.width * scale,
    };

    // We'll render items up to animationIndex. The item at animationIndex will be shown with animationProgress.
    const itemsToRender = items.map((item, idx) => ({ item, idx })).filter(({ item }) => visibleItems[item.id]);

    return (
        <Canvas 
            camera={{ 
                position: [scaledContainer.width * 2.2, scaledContainer.height * 1.8, scaledContainer.depth * 2.2], 
                fov: 45 
            }}
            shadows
            gl={{ antialias: true, alpha: true, shadowMapType: THREE.PCFSoftShadowMap }}
            style={{ background: 'linear-gradient(135deg, #2c3e50 0%, #34495e 50%, #2c3e50 100%)' }}
        >
            {settings.addLights && <>
                <ambientLight intensity={0.6} color="#ffffff" />
                <directionalLight 
                    position={[20, 30, 15]} 
                    intensity={1.8} 
                    color="#ffffff"
                    castShadow
                    shadow-mapSize-width={4096}
                    shadow-mapSize-height={4096}
                    shadow-camera-far={100}
                    shadow-camera-left={-25}
                    shadow-camera-right={25}
                    shadow-camera-top={25}
                    shadow-camera-bottom={-25}
                    shadow-bias={-0.0001}
                />
                <directionalLight 
                    position={[-15, 20, -10]} 
                    intensity={0.8} 
                    color="#f8f8ff"
                />
                <pointLight 
                    position={[0, scaledContainer.height * 2, 0]} 
                    intensity={0.5} 
                    color="#ffffff"
                />
            </>}
            
            {settings.showContainer && (
                <group>
                    <Box 
                        args={[scaledContainer.width, scaledContainer.height, scaledContainer.depth]}
                        receiveShadow
                    >
                        <meshStandardMaterial 
                            color="#f5f5f5"
                            transparent 
                            opacity={0.15}
                            roughness={0.1}
                            metalness={0.0}
                        />
                        {settings.showContainerEdges && (
                            <Edges 
                                color="#666666" 
                                lineWidth={2}
                                threshold={15}
                            />
                        )}
                    </Box>
                </group>
            )}

            {settings.showGoods && itemsToRender.map(({ item, idx }) => {
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

                const isBefore = idx < animationIndex;
                const isCurrent = idx === animationIndex;
                if (!isBefore && !isCurrent) return null;

                const animScale = isCurrent ? (0.2 + 0.8 * animationProgress) : 1;
                const opacity = 1; // keep boxes opaque (no transparency)

                return (
                    <group key={item.id} position={position} scale={[animScale, animScale, animScale]}>
                        <WoodenCrate
                            position={[0,0,0]}
                            size={[scaledItem.width, scaledItem.height, scaledItem.depth]}
                            color={item.color}
                            showEdges={settings.showGoodEdges}
                            opacity={opacity}
                        />
                    </group>
                );
            })}
            
            {settings.showBaseGrid && (
                <Grid 
                    infiniteGrid 
                    position={[0, -scaledContainer.height / 2 - 0.01, 0]}
                    args={[50, 50]}
                    cellSize={0.5}
                    cellThickness={0.8}
                    cellColor="#999999"
                    sectionSize={5}
                    sectionThickness={1.2}
                    sectionColor="#777777"
                    fadeDistance={25}
                    fadeStrength={1}
                />
            )}

            <ContactShadows 
                position={[0, -scaledContainer.height / 2, 0]}
                opacity={0.4}
                scale={scaledContainer.width * 2.5}
                blur={2.5}
                far={scaledContainer.height}
                color="#333333"
            />
            
            <OrbitControls 
                enablePan={true}
                enableZoom={true}
                enableRotate={true}
                minDistance={scaledContainer.width * 0.8}
                maxDistance={scaledContainer.width * 4}
                autoRotate={false}
                dampingFactor={0.05}
                enableDamping={true}
                maxPolarAngle={Math.PI * 0.75}
                minPolarAngle={Math.PI * 0.1}
            />
        </Canvas>
    );
};

export default Container3DView;