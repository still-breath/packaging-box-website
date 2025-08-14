// src/components/Header.tsx
import React from 'react';

interface HeaderProps {
  page: string;
  setPage: (page: 'data' | 'visualization') => void;
}

const Header = ({ page, setPage }: HeaderProps) => (
  <header className="header">
    <div className="header-left">
      <div className="header-logo-bg">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#D9383E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
      </div>
      <h1 className="header-title">STORAGE MANAGER</h1>
      <nav className="header-nav">
        <button onClick={() => setPage('data')} className={`nav-button ${page === 'data' ? 'active' : ''}`}>Data & Calculation</button>
        <button onClick={() => setPage('visualization')} className={`nav-button ${page === 'visualization' ? 'active' : ''}`}>Visualization</button>
      </nav>
    </div>
  </header>
);

export default Header;
