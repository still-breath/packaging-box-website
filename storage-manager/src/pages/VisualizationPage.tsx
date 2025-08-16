// src/pages/VisualizationPage.tsx
import React, { useState, useMemo, useEffect } from 'react';
import { CalculationResult, Group, Container, PlacedBox } from '../types/types'; 
import Container3DView from '../components/Container3DView';

// Komponen PieChart dan CustomToggle tidak berubah
const PieChart = ({ percentage }: { percentage: number }) => {
    const radius = 50;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percentage / 100) * circumference;

    return (
        <div className="pie-chart-container">
            <svg className="pie-chart-svg" viewBox="0 0 120 120">
                <circle className="pie-chart-track" strokeWidth="10" stroke="currentColor" fill="transparent" r={radius} cx="60" cy="60" />
                <circle className="pie-chart-fill" strokeWidth="10" stroke="currentColor" fill="transparent" r={radius} cx="60" cy="60"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    transform="rotate(-90 60 60)" />
            </svg>
            <div className="pie-chart-text"><span className="pie-chart-percentage">{percentage.toFixed(1)}%</span></div>
        </div>
    );
};

const CustomToggle = ({ label, checked, onChange }: { label: string, checked: boolean, onChange: (e: React.ChangeEvent<HTMLInputElement>) => void }) => (
    <div className="custom-toggle">
        <span>{label}</span>
        <label className="toggle-label">
            <input type="checkbox" checked={checked} onChange={onChange} className="toggle-input" />
            <div className="toggle-switch"></div>
        </label>
    </div>
);


interface VisualizationPageProps {
  result?: CalculationResult;
  container?: Container;
  algorithm?: string;
  initialGroups?: Group[];
}

const defaultContainer: Container = { width: 0, height: 0, length: 0, maxWeight: 0 };
const defaultResult: CalculationResult = { placedItems: [], unplacedItems: [], totalWeight: 0, fillRate: 0 };

const VisualizationPage = ({
    result = defaultResult,
    container = defaultContainer,
    algorithm = 'UNKNOWN ALGORITHM',
    initialGroups = []
}: VisualizationPageProps) => {
    const [settings, setSettings] = useState({
        showContainer: true, showContainerEdges: true, showGoods: true, showGoodEdges: true,
        showEmptySpace: false, addLights: true, showBaseGrid: true,
    });

    const [visibleItems, setVisibleItems] = useState<{ [id: string]: boolean }>({});

    useEffect(() => {
        if (result.placedItems) {
            const initialVisibility = result.placedItems.reduce((acc, item) => {
                acc[item.id] = true;
                return acc;
            }, {} as { [id: string]: boolean });
            setVisibleItems(initialVisibility);
        }
    }, [result.placedItems]); // Dependensi array memastikan ini berjalan saat placedItems berubah.

    const colorToGroupMap = useMemo(() => initialGroups.reduce((acc, group) => {
        if (group?.color) {
            acc[group.color.toUpperCase()] = group.name;
        }
        return acc;
    }, {} as { [color: string]: string }), [initialGroups]);
    
    if (!result.placedItems || result.placedItems.length === 0) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <p>Waiting for calculation result or the result is empty...</p>
            </div>
        );
    }
    
    // Fungsi dan kalkulasi lainnya didefinisikan setelah guard clause
    const toggleItemVisibility = (itemId: string) => {
        setVisibleItems(prev => ({ ...prev, [itemId]: !prev[itemId] }));
    };

    const groupCounters: { [groupName: string]: number } = {};
    const displayItems = result.placedItems.map(item => {
        const colorKey = item?.color?.toUpperCase() || '#CCCCCC';
        const groupName = colorToGroupMap[colorKey] || 'Unknown Group';
        groupCounters[groupName] = (groupCounters[groupName] || 0) + 1;
        const displayName = `${groupName} - ${groupCounters[groupName]}`;
        return { ...item, displayName };
    });

    const formatAlgorithmName = (name: string) => name.replace(/_/g, ' ').toUpperCase();
    
    const containerVolume = container.width > 0 ? (container.width * container.height * container.length) / 1e6 : 0;

    return (
        <div className="page-container">
            {/* Sidebar Kiri */}
            <div className="sidebar">
                <div className="card">
                    <h3 className="card-title">{formatAlgorithmName(algorithm)}</h3>
                    <p style={{fontSize: '0.75rem', color: '#6b7280'}}>Calculated at {new Date(Date.now()).toLocaleString('id-ID')}</p>
                    <div style={{marginTop: '0.5rem', fontSize: '0.875rem'}}>
                        <p>CONTAINER ({result.placedItems.length} BOXES)</p>
                        <p style={{fontSize: '0.75rem'}}>
                            W: {(container.width / 100).toFixed(2)}m | 
                            H: {(container.height / 100).toFixed(2)}m | 
                            L: {(container.length / 100).toFixed(2)}m | 
                            V: {containerVolume.toFixed(2)} m³
                        </p>
                        <p style={{fontSize: '0.75rem'}}>Weight: {result.totalWeight.toFixed(2)} kg / {container.maxWeight} kg</p>
                    </div>
                    <PieChart percentage={result.fillRate} />
                     <div className="legend-container">
                        <div className="legend-item"><span className="legend-color-box" style={{backgroundColor: '#f87171'}}></span>Fill Rate</div>
                        <div className="legend-item"><span className="legend-color-box" style={{backgroundColor: '#d1fae5'}}></span>Free Space</div>
                    </div>
                </div>
                <div className="card" style={{flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: 0, gap: '1rem'}}>
                    <div className="list-block">
                        <h3 className="card-title" style={{marginBottom: 0}}>GROUPS ({initialGroups.length})</h3>
                        <div className="goods-list-container">
                            <ul className="goods-list">
                                {initialGroups.map(g => (
                                     <li key={g.id} className="legend-item">
                                         <span className="legend-color-box" style={{backgroundColor: g.color}}></span>{g.name}
                                     </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                    <div className="list-block">
                        <h3 className="card-title" style={{marginBottom: 0}}>LOADED BOXES ({result.placedItems.length})</h3>
                        <div className="goods-list-container">
                            <ul className="goods-list">
                                {displayItems.map((item) => (
                                     <li key={item.id} className="goods-list-item">
                                         <span>● {item.displayName}</span>
                                         <button onClick={() => toggleItemVisibility(item.id)} className="visibility-toggle-button">
                                            {visibleItems[item.id] ? (
                                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                                            ) : (
                                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                                            )}
                                         </button>
                                     </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            {/* Canvas Utama */}
            <div className="viz-canvas-container">
                <Container3DView 
                    items={result.placedItems} 
                    containerDimensions={container}
                    settings={settings}
                    visibleItems={visibleItems}
                />
            </div>

            {/* Sidebar Kanan */}
            <div className="viz-sidebar-right">
                <h3 className="card-title" style={{color: 'white'}}>SCENE SETTINGS</h3>
                <div className="sidebar-section">
                    <p className="sidebar-section-title">CONTAINER</p>
                    <div className="toggle-container">
                        <CustomToggle label="Show container" checked={settings.showContainer} onChange={(e) => setSettings(s => ({...s, showContainer: e.target.checked}))} />
                        <CustomToggle label="Show container edges" checked={settings.showContainerEdges} onChange={(e) => setSettings(s => ({...s, showContainerEdges: e.target.checked}))} />
                    </div>
                </div>
                 <div className="sidebar-section">
                    <p className="sidebar-section-title">GOODS</p>
                    <div className="toggle-container">
                         <CustomToggle label="Show goods" checked={settings.showGoods} onChange={(e) => setSettings(s => ({...s, showGoods: e.target.checked}))} />
                         <CustomToggle label="Show good edges" checked={settings.showGoodEdges} onChange={(e) => setSettings(s => ({...s, showGoodEdges: e.target.checked}))} />
                    </div>
                </div>
                <div className="sidebar-section">
                    <p className="sidebar-section-title">EMPTY SPACE</p>
                    <div className="toggle-container">
                         <CustomToggle label="Show empty space" checked={settings.showEmptySpace} onChange={(e) => setSettings(s => ({...s, showEmptySpace: e.target.checked}))} />
                    </div>
                </div>
                <div className="sidebar-section">
                    <p className="sidebar-section-title">SCENE</p>
                    <div className="toggle-container">
                         <CustomToggle label="Add lights" checked={settings.addLights} onChange={(e) => setSettings(s => ({...s, addLights: e.target.checked}))} />
                         <CustomToggle label="Show base grid" checked={settings.showBaseGrid} onChange={(e) => setSettings(s => ({...s, showBaseGrid: e.target.checked}))} />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default VisualizationPage;