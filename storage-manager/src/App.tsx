// src/App.tsx
import React, { useState } from 'react';

import Header from './components/Header';
import DataCalculationPage from './pages/DataCalculation';
import VisualizationPage from './pages/VisualizationPage';
import { Box, Group, Container, CalculationResult, ApiResponse } from './types/types';
import { presets, getDefaultGroups } from './data';

import './App.css';

export default function App() {
  const [page, setPage] = useState<'data' | 'visualization'>('data');
  const [containerData, setContainerData] = useState<Container>(presets['20ft'].container);
  const [boxes, setBoxes] = useState<Box[]>(presets['20ft'].boxes);
  const [groups, setGroups] = useState<Group[]>(getDefaultGroups());
  
  const [constraints, setConstraints] = useState({
    enforceLoadCapacity: true,
    enforceStacking: false,
    enforcePriority: false,
    enforceLIFO: false,
  });

  const [calculationResult, setCalculationResult] = useState<CalculationResult | null>(null);
  const [usedAlgorithm, setUsedAlgorithm] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handlePresetChange = (presetName: '10ft' | '20ft' | '40ft') => {
    const preset = presets[presetName];
    setContainerData(preset.container);
    setBoxes(preset.boxes);
    setGroups(getDefaultGroups());
  };

  const handleVisualize = async (algorithm: string, container: Container, currentBoxes: Box[], currentGroups: Group[], currentConstraints: any) => {
    setIsLoading(true);
    setError(null);

    const processedBoxes = currentBoxes.map(box => {
        const newBox: any = { ...box };
        if (typeof newBox.allowed_rotations === 'string' && newBox.allowed_rotations.trim() !== '') {
            newBox.allowed_rotations = newBox.allowed_rotations
                .split(',')
                .map((s: string) => parseInt(s.trim(), 10))
                .filter((n: number) => !isNaN(n));
        } else {
            delete newBox.allowed_rotations;
        }
        return newBox;
    });

    const requestBody = { 
        container, 
        items: processedBoxes, 
        groups: currentGroups, 
        algorithm,
        constraints: currentConstraints
    };
    
    const apiUrl = 'http://localhost:8000/calculate/python';

    try {
        await new Promise(resolve => setTimeout(resolve, 500));
        const response = await fetch(apiUrl, { 
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody)
        });

        const resultData: ApiResponse = await response.json();

        if (!response.ok) {
            const errorMessage = (resultData as { error: string }).error || 'Unknown server error';
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorMessage}`);
        }
        
        if ('error' in resultData && resultData.error) {
             throw new Error(`Calculation error from backend: ${resultData.error}`);
        }

        setCalculationResult(resultData as CalculationResult);
        setContainerData(container);
        setUsedAlgorithm(algorithm);
        setPage('visualization');

    } catch (e: any) {
        console.error("Gagal memanggil API:", e);
        setError(`Gagal mengambil data dari backend: ${e.message}`);
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div 
      className="app-container"
      style={page === 'visualization' ? { height: '100vh' } : {}}
    >
      <Header page={page} setPage={setPage} />
      
      {page === 'data' && (
        <DataCalculationPage 
          container={containerData}
          boxes={boxes}
          groups={groups}
          constraints={constraints}
          setContainer={setContainerData}
          setBoxes={setBoxes}
          setGroups={setGroups}
          setConstraints={setConstraints}
          onPresetChange={handlePresetChange}
          onVisualize={handleVisualize}
        />
      )}
      
      {page === 'visualization' && calculationResult && (
        <VisualizationPage 
          result={calculationResult}
          container={containerData}
          algorithm={usedAlgorithm}
          initialGroups={groups}
        />
      )}
      
      {page === 'visualization' && !calculationResult && (
          <div className="placeholder-container" style={{color: 'white'}}>
              <p>Tidak ada data untuk divisualisasikan. Silakan kembali ke halaman Data & Calculation.</p>
          </div>
      )}

      {isLoading && (
        <div className="loading-overlay">
            <div className="spinner"></div>
            <p style={{marginTop: '1rem'}}>Calculating...</p>
        </div>
      )}

      {error && (
        <div className="error-modal">
            <h3>Calculation Failed</h3>
            <p>{error}</p>
            <button onClick={() => setError(null)}>Close</button>
        </div>
      )}
    </div>
  );
}
