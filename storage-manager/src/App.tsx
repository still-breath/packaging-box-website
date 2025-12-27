// src/App.tsx
import React, { useState, useEffect } from 'react';

import Header from './components/Header';
import DataCalculationPage from './pages/DataCalculation';
import VisualizationPage from './pages/VisualizationPage';
import HistoryPage from './pages/History';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import { Box, Group, Container, CalculationResult, ApiResponse } from './types/types';
import { presets, getDefaultGroups } from './data';
import { loginUser, registerUser, postCalculation, getItemGroups } from './api';

import './App.css';

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [page, setPage] = useState<'data' | 'visualization' | 'history'>('data');
  const [authPage, setAuthPage] = useState<'login' | 'register'>('login');

  // Data state
  // Start with empty workspace (no preset selected). User can pick a preset
  const [containerData, setContainerData] = useState<Container>({ length: 0, width: 0, height: 0, maxWeight: 0 });
  const [boxes, setBoxes] = useState<Box[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [constraints, setConstraints] = useState({
    enforceLoadCapacity: true,
    enforceStacking: false,
    enforcePriority: false,
    enforceLIFO: false,
  });

  // UI State
  const [calculationResult, setCalculationResult] = useState<CalculationResult | null>(null);
  const [usedAlgorithm, setUsedAlgorithm] = useState<string>('');
    const [activityName, setActivityName] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [calculationLog, setCalculationLog] = useState<string[] | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);

  // View a saved calculation from History: fetch details and set visualization state
  const handleViewSaved = async (calculationId: number | string) => {
    if (!token) {
      setError('You must be logged in to view history');
      return;
    }
    try {
      setIsLoading(true);
      // lazy import api function to avoid top-level circular issues
      const { getCalculationById } = await import('./api');
      const data: any = await getCalculationById(calculationId, token);
      // build CalculationResult shape
      const result = data.result || {};
      const placed = (result.placed_items || []).map((p: any) => ({
        id: p.id || '',
        x: p.x || 0,
        y: p.y || 0,
        z: p.z || 0,
        length: p.length || 0,
        width: p.width || 0,
        height: p.height || 0,
        weight: p.weight || 0,
        color: p.color || '#CCCCCC'
      }));

      setCalculationResult({ fillRate: result.fill_rate || 0, totalWeight: result.total_weight || 0, placedItems: placed, unplacedItems: [] });

      if (data.container) {
        setContainerData({ width: data.container.width || 0, height: data.container.height || 0, length: data.container.length || 0, maxWeight: data.container.max_weight || 0 });
      }
      if (data.groups) {
        setGroups((data.groups || []).map((g: any, idx: number) => ({ id: String(g.group_id_string || idx), name: g.name || 'Group', color: g.color || '#CCCCCC' })));
      }
      setUsedAlgorithm((data.calculation && data.calculation.algorithm) || 'SAVED_CALCULATION');
      setActivityName((data.calculation && data.calculation.activity_name) || '');
      setPage('visualization');
    } catch (e: any) {
      console.error('Failed to load saved calculation', e);
      setError(e.message || 'Failed to load saved calculation');
    } finally {
      setIsLoading(false);
    }
  };

  // append a log line keeping at most 5 recent entries
  const appendLog = (line: string) => {
    setCalculationLog(prev => {
      const arr = prev ? [...prev] : [];
      arr.push(line);
      if (arr.length > 5) arr.splice(0, arr.length - 5);
      return arr;
    });
  };

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
      // Load groups after login
      try {
        const groupsFromApi = await getItemGroups(receivedToken);
        if (groupsFromApi && groupsFromApi.length) {
          setGroups(groupsFromApi.map(g => ({ id: String(g.id), name: g.name, color: g.color })));
        }
      } catch (err) {
        console.warn('Failed to load groups after login', err);
      }
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
      setAuthPage('login');
      alert('Registration successful! Please log in.');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
      throw err;
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    setToken(null);
    setPage('data'); // Reset to default page
  };

  const handlePresetChange = (presetName: '' | '10ft' | '20ft' | '40ft') => {
    if (!presetName) {
      // clear to empty editable state
      setContainerData({ length: 0, width: 0, height: 0, maxWeight: 0 });
      setBoxes([]);
      setGroups([]);
      return;
    }
    const preset = presets[presetName];
    setContainerData(preset.container);
    setBoxes(preset.boxes);
    setGroups(getDefaultGroups());
  };

  const handleVisualize = async (algorithm: string, container: Container, currentBoxes: Box[], currentGroups: Group[], currentConstraints: any, activityName?: string) => {
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
      constraints: currentConstraints,
      activity_name: activityName || ''
    };

    try {
      // store activity name for visualization/export
      setActivityName(activityName || '');
      // For Python GA we use streaming endpoint to show logs in realtime
      if (algorithm === 'PYTHON_GA' || algorithm === 'PYTHON_CLPTAC') {
        // Start job via Go backend (authenticated) which in turn starts Python GA job
        const startResp = await fetch('http://localhost:8080/api/calculate/golang', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify(requestBody)
        });
        if (!startResp.ok) {
          const errText = await startResp.text();
          throw new Error(`Failed to start GA job: ${errText}`);
        }
        const startData = await startResp.json();
        const jobId = startData.job_id;
        setCurrentJobId(jobId);

        // Prepare log modal with connecting messages so modal isn't empty
        setCalculationLog([`Connecting to job ${jobId}...`, 'Waiting for algorithm to finish...']);

        // Open EventSource to receive logs and final result proxied by Go
        const es = new EventSource(`http://localhost:8080/api/calculate/golang/stream/${jobId}`);
        setEventSource(es);
        console.log('Opening EventSource for job:', jobId);
        es.onopen = () => console.log('EventSource opened');
        es.onmessage = (ev) => {
          console.log('Received SSE message:', ev.data);
          appendLog(ev.data);
        };
            es.addEventListener('done', async (ev: any) => {
          console.log('Received done event:', ev.data);
          try {
            const data = JSON.parse(ev.data);
            if (data && data.error) {
              // Append error to log so user sees why calculation failed
              setCalculationLog(prev => (prev ? [...prev, `ERROR: ${data.error}`] : [`ERROR: ${data.error}`]));
              setError(data.error);
            } else {
              setCalculationResult(data as CalculationResult);
              setContainerData(container);
              setUsedAlgorithm(algorithm);
                  setPage('visualization');
                  // Auto-close the log modal shortly after the result is visualized
                  try { setTimeout(() => setCalculationLog(null), 1200); } catch (e) { /* ignore */ }
            }
          } catch (err) {
            console.error('Failed to parse final result', err);
            setError('Failed to parse final result from calculation');
          } finally {
            es.close();
            setEventSource(null);
            setIsLoading(false);
            setCurrentJobId(null);
          }
        });
        // Listen for named 'error' events emitted by the SSE stream (these can carry error details)
        es.addEventListener('error', (ev: any) => {
          console.log('Received error event on SSE', ev);
          // EventSource error events often don't include data; append a generic message
          const msg = ev?.data ? (typeof ev.data === 'string' ? ev.data : JSON.stringify(ev.data)) : 'Calculation streaming error (SSE)';
          appendLog(`ERROR: ${msg}`);
          setError(msg);
          // don't immediately close here; allow 'done' or server to close stream
        });

        // Show log modal immediately
        setPage('visualization');
        return;
      }

      // Fallback: use existing backend proxy for other algorithms
      const resultData: ApiResponse = await postCalculation(requestBody, token);
        
      if ('error' in resultData && resultData.error) {
         throw new Error(`Calculation error from backend: ${resultData.error}`);
      }

      setCalculationResult(resultData as CalculationResult);
      setContainerData(container);
      setUsedAlgorithm(algorithm);
      if ('logs' in resultData) setCalculationLog((resultData as any).logs || null);
      setPage('visualization');
      // If a log modal is open for some reason, close it shortly after showing visualization
      try { setTimeout(() => setCalculationLog(null), 800); } catch (e) { /* ignore */ }

    } catch (e: any) {
      console.error("Failed to call API:", e);
      setError(`Failed to get data from backend: ${e.message}`);
    } finally {
      // For PYTHON_GA the EventSource handler will clear isLoading when done.
      if (algorithm !== 'PYTHON_GA') setIsLoading(false);
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
      
      {page === 'history' && (
        <HistoryPage onView={handleViewSaved} token={token} />
      )}
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
          activityName={activityName}
        />
      )}
      
      {page === 'visualization' && !calculationResult && (
          <div className="placeholder-container" style={{color: 'white'}}>
              <p>No data to visualize. Please return to the Data & Calculation page.</p>
          </div>
      )}

      {/* Unified overlay: shows spinner, log modal, or error in the same centered box */}
      {(isLoading || calculationLog || error) && (
        <div className="loading-overlay">
          <div className="centered-box">
            {calculationLog ? (
              <div className="log-modal">
                <h3>Calculation Log</h3>
                <div className="log-content">
                  <pre>{calculationLog.join('\n')}</pre>
                </div>
                <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', alignItems: 'center' }}>
                  {currentJobId && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <div className="spinner" style={{ width: 28, height: 28, borderWidth: 4 }}></div>
                      <div>Calculating...</div>
                    </div>
                  )}
                  <div>
                    <button onClick={() => {
                      // closing log should not leave the EventSource open if job finished
                      setCalculationLog(null);
                    }}>Close</button>
                  </div>
                  {currentJobId && (
                    <button onClick={async () => {
                      try {
                        // close local EventSource first so UI updates immediately
                        try { eventSource?.close(); } catch (e) { /* ignore */ }
                        setEventSource(null);

                        const resp = await fetch(`http://localhost:8080/api/calculate/golang/cancel`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                          body: JSON.stringify({ job_id: currentJobId })
                        });
                        if (!resp.ok) {
                          const t = await resp.text();
                          appendLog(`ERROR: Failed to cancel job: ${t}`);
                          setError('Failed to cancel job');
                        } else {
                          appendLog('Cancellation requested');
                        }
                      } catch (e) {
                        appendLog('ERROR: Cancel request failed');
                      } finally {
                        setCurrentJobId(null);
                        setIsLoading(false);
                      }
                    }}>Cancel</button>
                  )}
                </div>
              </div>
            ) : error ? (
              <div className="error-modal">
                <h3>Operation Failed</h3>
                <p>{error}</p>
                <button onClick={() => setError(null)}>Close</button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div className="spinner" style={{ width: 48, height: 48, borderWidth: 6 }}></div>
                <p style={{marginTop: '1rem'}}>Calculating...</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
