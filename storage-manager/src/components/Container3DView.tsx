// src/components/Container3DView.tsx
import React from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Box, Edges, Grid } from '@react-three/drei';
import * as THREE from 'three';
import { PlacedBox, Container } from '../types/types';

interface Container3DViewProps {
  items: PlacedBox[];
  containerDimensions: Container;
  settings: any;
  visibleItems: { [id: string]: boolean };
}

const Container3DView = ({ items, containerDimensions, settings, visibleItems }: Container3DViewProps) => {
    const scale = 0.01; 

    const scaledContainer = {
        width: containerDimensions.length * scale,
        height: containerDimensions.height * scale,
        depth: containerDimensions.width * scale,
    };

    const itemsToRender = items.filter(item => visibleItems[item.id]);

    return (
        <Canvas camera={{ position: [scaledContainer.width * 1.5, scaledContainer.height * 1.5, scaledContainer.depth * 1.5], fov: 50 }}>
            {settings.addLights && <>
                <ambientLight intensity={0.7} />
                <directionalLight position={[10, 10, 5]} intensity={1} />
                <directionalLight position={[-10, -10, -5]} intensity={0.5} />
            </>}
            
            {settings.showContainer && (
                 <Box args={[scaledContainer.width, scaledContainer.height, scaledContainer.depth]}>
                    <meshStandardMaterial color="gray" transparent opacity={0.1} />
                    {settings.showContainerEdges && <Edges color="white" />}
                </Box>
            )}

            {settings.showGoods && itemsToRender.map(item => {
                // Dimensi box disesuaikan dengan mapping sumbu
                const scaledItem = { 
                    width: item.length * scale,  // X-axis
                    height: item.height * scale, // Y-axis
                    depth: item.width * scale,   // Z-axis
                };

                // PERBAIKAN: Logika perhitungan posisi yang disederhanakan dan diperbaiki
                // 1. Hitung posisi tengah box relatif terhadap sudut kontainer (0,0,0)
                const boxCenterX = item.x + (item.length / 2);
                const boxCenterY = item.z + (item.height / 2); // Backend Z adalah tinggi -> Three.js Y
                const boxCenterZ = item.y + (item.width / 2);  // Backend Y adalah lebar -> Three.js Z

                // 2. Geser posisi box agar relatif terhadap pusat kontainer (0,0,0)
                const position: [number, number, number] = [
                    (boxCenterX - containerDimensions.length / 2) * scale, // Posisi X
                    (boxCenterY - containerDimensions.height / 2) * scale, // Posisi Y (Tinggi)
                    (boxCenterZ - containerDimensions.width / 2) * scale,  // Posisi Z (Lebar)
                ];

                return (
                    <Box key={item.id} args={[scaledItem.width, scaledItem.height, scaledItem.depth]} position={position}>
                        <meshStandardMaterial color={item.color || '#cccccc'} transparent opacity={0.8} />
                         {settings.showGoodEdges && <Edges color="black" />}
                    </Box>
                );
            })}
            
            {settings.showBaseGrid && <Grid infiniteGrid position={[0, -scaledContainer.height / 2, 0]} />}
            
            <OrbitControls />
        </Canvas>
    );
};

export default Container3DView;
