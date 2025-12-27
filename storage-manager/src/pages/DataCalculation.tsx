// src/pages/DataCalculation.tsx
import React, { useRef, useState } from 'react';
import { importExcel, createItemGroup, updateItemGroup, deleteItemGroup } from '../api';
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
  onPresetChange: (presetName: '' | '10ft' | '20ft' | '40ft') => void;
  onVisualize: (algorithm: string, container: Container, boxes: Box[], groups: Group[], constraints: any, activityName?: string) => void;
}

const DataCalculationPage = ({ 
    container, boxes, groups, constraints,
    setContainer, setBoxes, setGroups, setConstraints,
    onPresetChange, onVisualize 
}: DataCalculationPageProps) => {

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [selectedPreset, setSelectedPreset] = useState<'' | '10ft' | '20ft' | '40ft'>('');
  const [selectedExcelAction, setSelectedExcelAction] = useState<'' | 'IMPORT' | 'TEMPLATE'>('');
  const [activityName, setActivityName] = useState<string>('');
  const [constraintModal, setConstraintModal] = useState<{ visible: boolean; warnings: { priority: boolean; stacking: boolean; lifo: boolean } }>({ visible: false, warnings: { priority: false, stacking: false, lifo: false } });
  const pendingVisualizeRef = useRef<{ algorithm: string } | null>(null);

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    try {
      const parsed = await importExcel(f);
      if (parsed.container) setContainer(parsed.container);
      if (parsed.groups) setGroups(parsed.groups);
      if (parsed.items) {
        const mapped = parsed.items.map((it: any) => ({
          id: it.id || `${Date.now()}-${Math.random()}`,
          quantity: it.quantity || 1,
          length: it.length || 0,
          width: it.width || 0,
          height: it.height || 0,
          weight: it.weight || 0,
          group: it.group || '',
          allowed_rotations: it.allowed_rotations || '',
          max_stack_weight: it.max_stack_weight || undefined,
          priority: it.priority || undefined,
          destination_group: it.destination_group || undefined,
        }));
        setBoxes(mapped);
      }
    } catch (err) {
      console.error('Import failed', err);
      alert('Import failed: ' + (err as any).message);
    }
  };

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
      const name = `Group ${groups.length + 1}`;
      const color = `#${Math.floor(Math.random()*16777215).toString(16).padStart(6, '0')}`;
      const token = localStorage.getItem('authToken');
      const hasServerGroups = groups.some(g => /^[0-9]+$/.test(String(g.id)));
      if (token && hasServerGroups) {
        // try to persist to backend first
        createItemGroup(name, color, token).then((res: any) => {
          const created = { id: String(res.id), name: res.name, color: res.color } as Group;
          setGroups(prevGroups => [...prevGroups, created]);
        }).catch(err => {
          console.error('Failed to create group on server', err);
          const newGroup: Group = { id: `${Date.now()}`, name, color };
          setGroups(prevGroups => [...prevGroups, newGroup]);
          alert('Group created locally but failed to persist to server.');
        });
        return;
      }

      const newGroup: Group = { id: `local-${Date.now()}`, name, color };
      setGroups(prevGroups => [...prevGroups, newGroup]);
  };

  const removeGroup = (idToRemove: string) => {
      const token = localStorage.getItem('authToken');
      const isServerId = /^[0-9]+$/.test(String(idToRemove));
      if (token && isServerId) {
        const prev = groups;
        setGroups(prevGroups => prevGroups.filter(group => group.id !== idToRemove));
        deleteItemGroup(idToRemove, token).catch(err => {
          console.error('Failed to delete group on server', err);
          alert('Failed to delete group on server. Reverting.');
          setGroups(prev);
        });
        return;
      }
      // local-only id or not logged in — just remove locally
      setGroups(prevGroups => prevGroups.filter(group => group.id !== idToRemove));
  };

  const handleGroupChange = (id: string, field: keyof Group, value: string) => {
      const token = localStorage.getItem('authToken');
      const prev = groups;
      // optimistic update
      setGroups(prevGroups => prevGroups.map(group => 
          group.id === id ? { ...group, [field]: value } : group
      ));

      const isServerId = /^[0-9]+$/.test(String(id));
      if (token && isServerId) {
        const g = (groups.find(gr => gr.id === id) || { name: '', color: '' });
        const newName = field === 'name' ? value : g.name;
        const newColor = field === 'color' ? value : g.color;
        updateItemGroup(id, newName, newColor, token).catch(err => {
          console.error('Failed to update group on server', err);
          alert('Failed to save group changes to server. Reverting.');
          setGroups(prev);
        });
      }
  };
  
  const handleVisualizeClick = (algorithm: string) => {
    const hasPrioritySet = boxes.some(b => {
      const p = Number(b.priority);
      return Number.isFinite(p) && p >= 1 && p <= 5;
    });
    const hasStackingSet = boxes.some(b => {
      const s = Number(b.max_stack_weight);
      return Number.isFinite(s) && s > 0;
    });
    const hasLifoSet = boxes.some(b => {
      const d = Number(b.destination_group);
      return Number.isFinite(d) && d >= 1;
    });

    const warnPriority = hasPrioritySet && !constraints.enforcePriority;
    const warnStacking = hasStackingSet && !constraints.enforceStacking;
    const warnLifo = hasLifoSet && !constraints.enforceLIFO;

    if (warnPriority || warnStacking || warnLifo) {
      // show modal with options
      setConstraintModal({ visible: true, warnings: { priority: warnPriority, stacking: warnStacking, lifo: warnLifo } });
      pendingVisualizeRef.current = { algorithm };
      return;
    }

    onVisualize(algorithm, container, boxes, groups, constraints, activityName);
  };

  const doVisualizeAfterModal = (action: 'enable' | 'clear' | 'cancel') => {
    const alg = pendingVisualizeRef.current?.algorithm || '';
    const warnings = constraintModal.warnings;
    setConstraintModal({ visible: false, warnings: { priority: false, stacking: false, lifo: false } });
    pendingVisualizeRef.current = null;

    if (action === 'cancel') return;

    if (action === 'enable') {
      const newConstraints = {
        ...constraints,
        enforcePriority: constraints.enforcePriority || warnings.priority,
        enforceStacking: constraints.enforceStacking || warnings.stacking,
        enforceLIFO: constraints.enforceLIFO || warnings.lifo,
      };
      setConstraints(newConstraints as any);
      // slight delay so toggles update visually
      setTimeout(() => onVisualize(alg, container, boxes, groups, newConstraints, activityName), 150);
      return;
    }

    if (action === 'clear') {
      // clear offending fields from boxes then proceed
      const cleaned = boxes.map(b => ({ ...b,
        priority: warnings.priority ? undefined : b.priority,
        max_stack_weight: warnings.stacking ? undefined : b.max_stack_weight,
        destination_group: warnings.lifo ? undefined : b.destination_group,
      }));
      setBoxes(cleaned);
      // proceed with visualize after state update
      setTimeout(() => onVisualize(alg, container, cleaned, groups, constraints, activityName), 150);
      return;
    }
  };

  return (
    <div className="page-container">
      {constraintModal.visible && (
        <div className="modal-overlay" style={{position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1200}}>
          <div className="modal" style={{background: 'white', padding: '1rem 1.25rem', borderRadius: '8px', width: '420px', boxShadow: '0 6px 18px rgba(0,0,0,0.2)'}}>
            <h3 style={{marginTop: 0}}>Constraint mismatch</h3>
            <div style={{marginBottom: '0.75rem'}}>
              <p>Some boxes include constraint fields but the corresponding enforcement toggles are OFF. Choose an action:</p>
              <ul style={{margin: '0.25rem 0 0 1rem'}}>
                {constraintModal.warnings.priority && <li>Priority values are present but <strong>Enforce Priority</strong> is disabled.</li>}
                {constraintModal.warnings.stacking && <li>Max stack weight values are present but <strong>Enforce Stacking</strong> is disabled.</li>}
                {constraintModal.warnings.lifo && <li>Destination group values are present but <strong>Enforce LIFO</strong> is disabled.</li>}
              </ul>
            </div>
            <div style={{display: 'flex', gap: '0.5rem', justifyContent: 'flex-end'}}>
              <button onClick={() => doVisualizeAfterModal('cancel')} style={{padding: '0.4rem 0.7rem'}}>Cancel</button>
              <button onClick={() => doVisualizeAfterModal('clear')} style={{padding: '0.4rem 0.7rem'}}>Clear fields</button>
              <button onClick={() => doVisualizeAfterModal('enable')} style={{padding: '0.4rem 0.7rem'}} className="primary">Enable constraints</button>
            </div>
          </div>
        </div>
      )}
      <div className="sidebar">
        <div className="card">
            <h3 className="card-title">LOAD PRESET</h3>
                <div className="input-group" style={{display: 'flex', gap: '0.5rem', alignItems: 'center'}}>
                  <div style={{display: 'flex', gap: '0.5rem', alignItems: 'center'}}>
                    <select
                      onChange={(e) => {
                          const val = e.target.value as '' | '10ft' | '20ft' | '40ft';
                          setSelectedPreset(val);
                          onPresetChange(val);
                        }}
                      value={selectedPreset}
                      style={{
                        padding: '0.35rem 0.5rem',
                        fontSize: '0.85rem',
                        width: '120px',
                        boxSizing: 'border-box',
                      }}
                    >
                      <option value="">Preset</option>
                      <option value="10ft">10ft</option>
                      <option value="20ft">20ft</option>
                      <option value="40ft">40ft</option>
                    </select>
                  </div>

                  <select
                    value={selectedExcelAction}
                    onChange={async (e) => {
                      const val = e.target.value as '' | 'IMPORT' | 'TEMPLATE';
                      setSelectedExcelAction(val);
                      if (val === 'IMPORT') {
                        fileInputRef.current?.click();
                        return;
                      }

                      // TEMPLATE: download immediately when selected
                      try {
                        const resp = await fetch('http://localhost:8000/templates/import_template.xlsx');
                        if (!resp.ok) throw new Error('Failed to download template');
                        const blob = await resp.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'import_template.xlsx';
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        window.URL.revokeObjectURL(url);
                      } catch (err) {
                        console.error('Template download failed', err);
                        alert('Template download failed');
                      }
                    }}
                    style={{
                      padding: '0.35rem 0.5rem',
                      fontSize: '0.85rem',
                      width: '120px',
                      boxSizing: 'border-box',
                    }}
                  >
                    <option value="">Excel Data</option>
                    <option value="IMPORT">Import Excel</option>
                    <option value="TEMPLATE">Download Template</option>
                  </select>

                  <input ref={fileInputRef} type="file" accept=".xlsx,.xls" style={{display: 'none'}} onChange={handleFileChange} />
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
            {/* Priority hint removed — validation happens on Visualize click */}
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
          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem' }}>Activity Name (optional)</label>
            <input type="text" value={activityName} onChange={(e) => setActivityName(e.target.value)} className="text-input" placeholder="e.g. Load for shipment #123" />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3 className="card-title" style={{ margin: 0 }}>BOXES TO LOAD ({boxes.length})</h3>
            <button onClick={addBox} className="add-button-small" aria-label="Add box" style={{ marginLeft: '0.5rem' }}>+</button>
          </div>
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
                    <input type="number" value={box.priority || ''} onChange={(e) => handleBoxChange(box.id, 'priority', Number(e.target.value))} className="text-input" title="Priority (1-5, 1 is highest)" />
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
        </div>
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3 className="card-title" style={{ margin: 0 }}>GROUPS ({groups.length})</h3>
            <button onClick={addGroup} className="add-button-small" aria-label="Add group" style={{ marginLeft: '0.5rem' }}>+</button>
          </div>
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
        </div>
      </div>
    </div>
  );
};

export default DataCalculationPage;