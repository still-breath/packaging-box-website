// src/pages/History.tsx
import React, { useEffect, useState } from 'react';
import { getCalculations, deleteCalculation } from '../api';

interface HistoryPageProps {
  token: string | null;
  onView: (calculationId: number | string) => void;
}

const HistoryPage = ({ token, onView }: HistoryPageProps) => {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCalculations(token);
      setItems(data || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (id: number | string) => {
    if (!window.confirm('Delete this history item?')) return;
    try {
      setLoading(true);
      await deleteCalculation(id, token);
      await load();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="main-content" style={{ gridTemplateColumns: '1fr', gap: '1rem' }}>
        <div className="card">
          <h3 className="card-title">History</h3>

          {loading && <div className="placeholder-container"><div>Loading...</div></div>}
          {error && <p style={{ color: 'red' }}>{error}</p>}

          {!loading && items.length === 0 && (
            <div className="placeholder-container">
              <div>No saved calculations found.</div>
            </div>
          )}

          {!loading && items.length > 0 && (
            <div className="history-table">
              <div className="history-header-grid">
                <div>Activity</div>
                <div>Algorithm</div>
                <div>Created At</div>
                <div>Actions</div>
              </div>

              <div className="scrollable-list-container">
                <div className="item-list">
                  {items.map(it => (
                    <div key={it.id} className="history-item-grid">
                      <div>
                        <div style={{ fontWeight: 700 }}>{it.activity_name || '(no name)'}</div>
                        <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>ID: {it.id}</div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{ fontSize: '0.9rem' }}>{it.algorithm}</div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', color: '#6b7280' }}>{new Date(it.created_at).toLocaleString('id-ID')}</div>
                      <div className="history-actions" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                        <button onClick={() => onView(it.id)} className="history-action-button view">View</button>
                        <button onClick={() => handleDelete(it.id)} className="history-action-button delete">Delete</button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default HistoryPage;
