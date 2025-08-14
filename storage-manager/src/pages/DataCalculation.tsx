// src/pages/DataCalculation.tsx
import React from 'react';
import { Box, Group, Container } from '../types/types';

// Helper component untuk toggle switch
const CustomToggle = ({ label, checked, onChange }: { label: string, checked: boolean, onChange: (e: React.ChangeEvent<HTMLInputElement>) => void }) => (
    <div className="custom-toggle">
        <span>{label}</span>
        <label className="toggle-label">
            <input type="checkbox" checked={checked} onChange={onChange} className="toggle-input" />
            <div className="toggle-switch"></div>
        </label>
    </div>
);

interface DataCalculationPageProps {
  container: Container;
  boxes: Box[];
  groups: Group[];
  constraints: any;
  setContainer: React.Dispatch<React.SetStateAction<Container>>;
  setBoxes: React.Dispatch<React.SetStateAction<Box[]>>;
  setGroups: React.Dispatch<React.SetStateAction<Group[]>>;
  setConstraints: React.Dispatch<React.SetStateAction<any>>;
  onPresetChange: (presetName: '10ft' | '20ft' | '40ft') => void;
  onVisualize: (algorithm: string, container: Container, boxes: Box[], groups: Group[], constraints: any) => void;
}

const DataCalculationPage = ({ 
    container, boxes, groups, constraints,
    setContainer, setBoxes, setGroups, setConstraints,
    onPresetChange, onVisualize 
}: DataCalculationPageProps) => {

  const handleContainerChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setContainer(prev => ({ ...prev, [name]: Number(value) }));
  };

  const handleConstraintChange = (key: string, value: boolean) => {
    setConstraints((prev: any) => ({ ...prev, [key]: value }));
  };

  const addBox = () => {
    const newBox: Box = { 
      id: `${Date.now()}`, quantity: 1, length: 0, width: 0, height: 0, 
      weight: 0, group: '', priority: 5, destination_group: 1, max_stack_weight: 9999
    };
    setBoxes(prevBoxes => [...prevBoxes, newBox]);
  };

  const removeBox = (idToRemove: string) => {
    setBoxes(prevBoxes => prevBoxes.filter(box => box.id !== idToRemove));
  };

  const handleBoxChange = (id: string, field: keyof Box, value: string | number) => {
      setBoxes(prevBoxes => prevBoxes.map(box => 
          box.id === id ? { ...box, [field]: value as any } : box
      ));
  };

  const addGroup = () => {
      const newGroup: Group = { id: `${Date.now()}`, name: `Group ${groups.length + 1}`, color: `#${Math.floor(Math.random()*16777215).toString(16).padStart(6, '0')}` };
      setGroups(prevGroups => [...prevGroups, newGroup]);
  };

  const removeGroup = (idToRemove: string) => {
      setGroups(prevGroups => prevGroups.filter(group => group.id !== idToRemove));
  };

  const handleGroupChange = (id: string, field: keyof Group, value: string) => {
      setGroups(prevGroups => prevGroups.map(group => 
          group.id === id ? { ...group, [field]: value } : group
      ));
  };
  
  const handleVisualizeClick = (algorithm: string) => {
    onVisualize(algorithm, container, boxes, groups, constraints);
  };

  return (
    <div className="page-container">
      <div className="sidebar">
        <div className="card">
            <h3 className="card-title">LOAD PRESET</h3>
            <div className="input-group">
                <button onClick={() => onPresetChange('10ft')} className="visualize-button">10ft</button>
                <button onClick={() => onPresetChange('20ft')} className="visualize-button">20ft</button>
                <button onClick={() => onPresetChange('40ft')} className="visualize-button">40ft</button>
            </div>
        </div>
        <div className="card">
          <h3 className="card-title">CONTAINER DATA</h3>
          <div className="input-group" style={{flexDirection: 'column'}}>
            <label>Length (cm)</label>
            <input type="number" name="length" value={container.length} onChange={handleContainerChange} className="text-input" />
            <label>Width (cm)</label>
            <input type="number" name="width" value={container.width} onChange={handleContainerChange} className="text-input" />
            <label>Height (cm)</label>
            <input type="number" name="height" value={container.height} onChange={handleContainerChange} className="text-input" />
            <label>Max Weight (kg)</label>
            <input type="number" name="maxWeight" value={container.maxWeight} onChange={handleContainerChange} className="text-input" />
          </div>
        </div>
        <div className="card">
          <h3 className="card-title">GLOBAL CONSTRAINTS</h3>
          <div className="toggle-container" style={{color: 'black'}}>
            <CustomToggle label="Enforce Load Capacity" checked={constraints.enforceLoadCapacity} onChange={(e) => handleConstraintChange('enforceLoadCapacity', e.target.checked)} />
            <CustomToggle label="Enforce Stacking Rules" checked={constraints.enforceStacking} onChange={(e) => handleConstraintChange('enforceStacking', e.target.checked)} />
            <CustomToggle label="Enforce Priority" checked={constraints.enforcePriority} onChange={(e) => handleConstraintChange('enforcePriority', e.target.checked)} />
            <CustomToggle label="Enforce LIFO" checked={constraints.enforceLIFO} onChange={(e) => handleConstraintChange('enforceLIFO', e.target.checked)} />
          </div>
        </div>
        <div className="summary-sidebar">
            <div className="summary-card">
                <p className="title">Python - BLF</p>
                <button onClick={() => handleVisualizeClick('PYTHON_BLF')} className="visualize-button">Visualize</button>
            </div>
            <div className="summary-card">
                <p className="title">Python - CLPTAC</p>
                <button onClick={() => handleVisualizeClick('PYTHON_CLPTAC')} className="visualize-button">Visualize</button>
            </div>
            <div className="summary-card">
                <p className="title">Python - Genetic Algorithm</p>
                <button onClick={() => handleVisualizeClick('PYTHON_GA')} className="visualize-button">Visualize</button>
            </div>
        </div>
      </div>

      <div className="main-content">
        <div className="card">
          <h3 className="card-title">BOXES TO LOAD ({boxes.length})</h3>
          {/* PERBAIKAN: Menggunakan class 'box-grid' baru dan menghapus col-span */}
          <div className="box-grid box-grid-header">
              <div>Qty</div>
              <div>Dimensions (L,W,H)</div>
              <div>Weight</div>
              <div>Group</div>
              <div>Rotations</div>
              <div>Max Stack (kg)</div>
              <div>Priority</div>
              <div>Destination</div>
              <div>Actions</div>
          </div>
          <div className="scrollable-list-container">
            <div className="item-list">
                {boxes.map(box => (
                  <div key={box.id} className="box-grid">
                    <input type="number" value={box.quantity} onChange={(e) => handleBoxChange(box.id, 'quantity', Number(e.target.value))} className="text-input" />
                    <div className="dimension-inputs">
                        <input type="number" value={box.length} onChange={(e) => handleBoxChange(box.id, 'length', Number(e.target.value))} className="text-input" />
                        <input type="number" value={box.width} onChange={(e) => handleBoxChange(box.id, 'width', Number(e.target.value))} className="text-input" />
                        <input type="number" value={box.height} onChange={(e) => handleBoxChange(box.id, 'height', Number(e.target.value))} className="text-input" />
                    </div>
                    <input type="number" value={box.weight} onChange={(e) => handleBoxChange(box.id, 'weight', Number(e.target.value))} className="text-input" />
                    <select value={box.group} onChange={(e) => handleBoxChange(box.id, 'group', e.target.value)} className="text-input">
                        <option value="">Select Group</option>
                        {groups.map(g => <option key={g.id} value={g.name}>{g.name}</option>)}
                    </select>
                    <input type="text" placeholder="e.g. 0,1,2" value={(box.allowed_rotations as any) || ''} onChange={(e) => handleBoxChange(box.id, 'allowed_rotations', e.target.value)} className="text-input" title="Allowed rotations (0-5), comma separated. Leave empty for all." />
                    <input type="number" value={box.max_stack_weight || ''} onChange={(e) => handleBoxChange(box.id, 'max_stack_weight', Number(e.target.value))} className="text-input" title="Max weight on top of this box."/>
                    <input type="number" value={box.priority || ''} onChange={(e) => handleBoxChange(box.id, 'priority', Number(e.target.value))} className="text-input" title="Priority (1-5, 1 is highest)"/>
                    <input type="number" value={box.destination_group || ''} onChange={(e) => handleBoxChange(box.id, 'destination_group', Number(e.target.value))} className="text-input" title="Destination group (1 is furthest)"/>
                    <div className="action-cell">
                      <button onClick={() => removeBox(box.id)} className="delete-button">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          </div>
          <button onClick={addBox} className="add-button-small">+</button>
        </div>
        <div className="card">
          <h3 className="card-title">GROUPS ({groups.length})</h3>
           <div className="scrollable-list-container">
            <div className="item-list">
                {groups.map(group => (
                     <div key={group.id} className="group-item-grid">
                        <input type="text" value={group.name} onChange={(e) => handleGroupChange(group.id, 'name', e.target.value)} className="text-input" />
                        <div className="group-color-picker">
                            <input type="color" value={group.color} onChange={(e) => handleGroupChange(group.id, 'color', e.target.value)} className="group-color-input" />
                            <span className="group-color-hex">{group.color}</span>
                        </div>
                        <div className="group-actions">
                             <button onClick={() => removeGroup(group.id)} className="delete-button">
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                             </button>
                        </div>
                    </div>
                ))}
            </div>
           </div>
           <button onClick={addGroup} className="add-button-small">+</button>
        </div>
      </div>
    </div>
  );
};

export default DataCalculationPage;
