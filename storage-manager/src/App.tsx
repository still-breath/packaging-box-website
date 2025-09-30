// src/App.tsx
import React, { useState, useEffect } from 'react';

import Header from './components/Header';
import DataCalculationPage from './pages/DataCalculation';
import VisualizationPage from './pages/VisualizationPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import { Box, Group, Container, CalculationResult, ApiResponse } from './types/types';
import { presets, getDefaultGroups } from './data';
import { loginUser, registerUser, postCalculation } from './api';

import './App.css';

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [page, setPage] = useState<'data' | 'visualization'>('data');
  const [authPage, setAuthPage] = useState<'login' | 'register'>('login');

  // Data state
  const [containerData, setContainerData] = useState<Container>(presets['20ft'].container);
  const [boxes, setBoxes] = useState<Box[]>(presets['20ft'].boxes);
  const [groups, setGroups] = useState<Group[]>(getDefaultGroups());
  const [constraints, setConstraints] = useState({
    enforceLoadCapacity: true,
    enforceStacking: false,
    enforcePriority: false,
    enforceLIFO: false,
  });

  // UI State
  const [calculationResult, setCalculationResult] = useState<CalculationResult | null>(null);
  const [usedAlgorithm, setUsedAlgorithm] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken);
    }
  }, []);

  const handleLogin = async (credentials: { username: string; password: string }) => {
    try {
      setIsLoading(true);
      const receivedToken = await loginUser(credentials);
      localStorage.setItem('authToken', receivedToken);
      setToken(receivedToken);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Login failed');
      throw err; // Re-throw to be caught in the component
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (credentials: { username: string; email: string; password: string }) => {
    try {
      await registerUser(credentials);
      // On successful registration, switch to login page with a success message
      setAuthPage('login');
      alert('Registration successful! Please log in.');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
      throw err; // Re-throw to be caught in the component
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    setToken(null);
    setPage('data'); // Reset to default page
  };

  const handlePresetChange = (presetName: '10ft' | '20ft' | '40ft') => {
    const preset = presets[presetName];
    setContainerData(preset.container);
    setBoxes(preset.boxes);
    setGroups(getDefaultGroups());
  };

  const handleVisualize = async (algorithm: string, container: Container, currentBoxes: Box[], currentGroups: Group[], currentConstraints: any) => {
    if (!token) {
      setError('You must be logged in to perform a calculation.');
      return;
    }

    setIsLoading(true);
    setError(null);

    const requestBody = { 
        container, 
        items: currentBoxes, 
        groups: currentGroups, 
        algorithm,
        constraints: currentConstraints
    };

    try {
        const resultData: ApiResponse = await postCalculation(requestBody, token);
        
        if ('error' in resultData && resultData.error) {
             throw new Error(`Calculation error from backend: ${resultData.error}`);
        }

        setCalculationResult(resultData as CalculationResult);
        setContainerData(container);
        setUsedAlgorithm(algorithm);
        setPage('visualization');

    } catch (e: any) {
        console.error("Failed to call API:", e);
        setError(`Failed to get data from backend: ${e.message}`);
    } finally {
        setIsLoading(false);
    }
  };

  // Render logic
  if (!token) {
    if (authPage === 'login') {
      return <LoginPage onLogin={handleLogin} onSwitchToRegister={() => setAuthPage('register')} />;
    }
    return <RegisterPage onRegister={handleRegister} onSwitchToLogin={() => setAuthPage('login')} isLoading={isLoading} />
  }

  return (
    <div 
      className="app-container"
      style={page === 'visualization' ? { height: '100vh' } : {}}
    >
      <Header page={page} setPage={setPage} onLogout={handleLogout} />
      
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
              <p>No data to visualize. Please return to the Data & Calculation page.</p>
          </div>
      )}

      {isLoading && (
        <div className="loading-overlay">
            <div className="spinner"></div>
            <p style={{marginTop: '1rem'}}>Calculating...</p>
        </div>
      )}

      {error && (
        <div className="loading-overlay">
          <div className="error-modal">
              <h3>Operation Failed</h3>
              <p>{error}</p>
              <button onClick={() => setError(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
