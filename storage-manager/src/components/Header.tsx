// src/components/Header.tsx
import React from 'react';
import './Header.css';

interface HeaderProps {
  page: 'data' | 'visualization';
  setPage: (page: 'data' | 'visualization') => void;
  onLogout: () => void;
}

const Header = ({ page, setPage, onLogout }: HeaderProps) => (
  <header className="header">
    <div className="header-left">
      <img src="/apple-icon-57x57.png" alt="Logo" className="header-logo" />
      <h1 className="header-title">STORAGE MANAGER</h1>
      <nav className="header-nav">
        <button onClick={() => setPage('data')} className={`nav-button ${page === 'data' ? 'active' : ''}`}>Data & Calculation</button>
        <button onClick={() => setPage('visualization')} className={`nav-button ${page === 'visualization' ? 'active' : ''}`}>Visualization</button>
      </nav>
    </div>
    <div className="header-right">
      <button onClick={onLogout} className="logout-button">Logout</button>
    </div>
  </header>
);

export default Header;
