// src/components/Header.tsx
import React from 'react';

interface HeaderProps {
  page: string;
  setPage: (page: 'data' | 'visualization') => void;
}

const Header = ({ page, setPage }: HeaderProps) => (
  <header className="header">
    <div className="header-left">
      <img src="/apple-icon-57x57.png" alt="Logo" className="header-logo" />
      <h1 className="header-title">STORAGE MANAGER</h1>
      <nav className="header-nav">
        <button onClick={() => setPage('data')} className={`nav-button ${page === 'data' ? 'active' : ''}`}>Data & Calculation</button>
        <button onClick={() => setPage('visualization')} className={`nav-button ${page === 'visualization' ? 'active' : ''}`}>Visualization</button>
      </nav>
    </div>
  </header>
);

export default Header;
