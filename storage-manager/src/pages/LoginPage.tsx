// src/pages/LoginPage.tsx
import React, { useState } from 'react';

interface LoginPageProps {
  onLogin: (credentials: { username: string; password: string }) => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');

  const handleLogin = (): void => {
    if (username === 'admin' && password === 'admin') {
      onLogin({ username, password });
      setError('');
    } else {
      setError('Invalid username or password');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter') {
      handleLogin();
    }
  };

  const handleInputFocus = (e: React.FocusEvent<HTMLInputElement>): void => {
    const target = e.target as HTMLInputElement;
    target.style.borderColor = '#D9383E';
    target.style.backgroundColor = 'white';
    target.style.boxShadow = '0 0 0 3px rgba(217, 56, 62, 0.1)';
  };

  const handleInputBlur = (e: React.FocusEvent<HTMLInputElement>): void => {
    const target = e.target as HTMLInputElement;
    target.style.borderColor = '#e5e7eb';
    target.style.backgroundColor = '#f9fafb';
    target.style.boxShadow = 'none';
  };

  const handleButtonMouseEnter = (e: React.MouseEvent<HTMLButtonElement>): void => {
    const target = e.target as HTMLButtonElement;
    target.style.backgroundColor = '#c12e33';
    target.style.transform = 'translateY(-1px)';
    target.style.boxShadow = '0 4px 8px rgba(217, 56, 62, 0.3)';
  };

  const handleButtonMouseLeave = (e: React.MouseEvent<HTMLButtonElement>): void => {
    const target = e.target as HTMLButtonElement;
    target.style.backgroundColor = '#D9383E';
    target.style.transform = 'translateY(0)';
    target.style.boxShadow = '0 2px 4px rgba(217, 56, 62, 0.2)';
  };

  const containerStyle: React.CSSProperties = {
    minHeight: '100vh',
    backgroundColor: '#1f2937',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif'
  };

  const cardStyle: React.CSSProperties = {
    width: '100%',
    maxWidth: '420px',
    padding: '3rem 2.5rem',
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 10px 15px -3px rgba(0, 0, 0, 0.1)',
    textAlign: 'center'
  };

  const logoStyle: React.CSSProperties = {
    width: '80px',
    height: '80px',
    borderRadius: '12px',
    margin: '0 auto 1.5rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '2rem',
    fontWeight: 'bold',
    color: 'white'
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.75rem 1rem',
    border: '2px solid #e5e7eb',
    borderRadius: '8px',
    fontSize: '1rem',
    backgroundColor: '#f9fafb',
    boxSizing: 'border-box',
    transition: 'all 0.2s ease',
    outline: 'none'
  };

  const buttonStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.875rem 1rem',
    fontSize: '1rem',
    fontWeight: '600',
    color: 'white',
    backgroundColor: '#D9383E',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    boxShadow: '0 2px 4px rgba(217, 56, 62, 0.2)'
  };

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        {/* Logo dan Header */}
        <div style={{ marginBottom: '2rem' }}>
          <div style={logoStyle}>
            <img src="/favicon-96x96.png" alt="logo" />
          </div>
          <h1 style={{
            fontSize: '2rem',
            fontWeight: '700',
            color: '#1f2937',
            margin: '0 0 0.5rem 0'
          }}>
            STORAGE MANAGER
          </h1>
          <p style={{
            color: '#6b7280',
            fontSize: '1rem',
            margin: '0 0 0.5rem 0'
          }}>
            Welcome back!
          </p>
          <p style={{
            color: '#9ca3af',
            fontSize: '0.875rem',
            margin: '0'
          }}>
            Enter your credentials to access the dashboard
          </p>
        </div>

        {/* Form */}
        <div style={{ textAlign: 'left' }}>
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{
              display: 'block',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: '#374151',
              marginBottom: '0.5rem'
            }}>
              Username
            </label>
            <input 
              type="text" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              placeholder="Enter your username"
              style={inputStyle}
              onFocus={handleInputFocus}
              onBlur={handleInputBlur}
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{
              display: 'block',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: '#374151',
              marginBottom: '0.5rem'
            }}>
              Password
            </label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              onKeyPress={handleKeyPress}
              placeholder="Enter your password"
              style={inputStyle}
              onFocus={handleInputFocus}
              onBlur={handleInputBlur}
            />
          </div>

          {error && (
            <div style={{
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              color: '#dc2626',
              padding: '0.75rem 1rem',
              borderRadius: '6px',
              fontSize: '0.875rem',
              marginBottom: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <span>⚠️</span>
              {error}
            </div>
          )}

          <button 
            onClick={handleLogin}
            style={buttonStyle}
            onMouseEnter={handleButtonMouseEnter}
            onMouseLeave={handleButtonMouseLeave}
          >
            Sign In
          </button>
        </div>

        {/* Footer */}
        <div style={{
          marginTop: '2rem',
          paddingTop: '1.5rem',
          borderTop: '1px solid #e5e7eb',
          fontSize: '0.75rem',
          color: '#9ca3af',
          textAlign: 'center'
        }}>
          <div style={{ marginBottom: '0.25rem' }}>
            Default credentials: admin / admin
          </div>
          <div>
            Secure access to your storage management system
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;