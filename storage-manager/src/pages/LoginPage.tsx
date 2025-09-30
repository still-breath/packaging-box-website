// src/pages/LoginPage.tsx
import React, { useState } from 'react';

interface LoginPageProps {
  onLogin: (credentials: { username: string; password: string }) => Promise<void>;
  onSwitchToRegister: () => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLogin, onSwitchToRegister }) => {
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  const handleLogin = async (): Promise<void> => {
    if (!username || !password) {
      setError('Invalid username or password');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await onLogin({ username, password });
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter') {
      handleLogin();
    }
  };

  // Inline styles from the original component for consistency
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
    opacity: loading ? 0.6 : 1,
  };

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <div style={{ marginBottom: '2rem' }}>
           <img src="/favicon-96x96.png" alt="logo" style={{ margin: '0 auto 1.5rem' }}/>
          <h1 style={{ fontSize: '2rem', fontWeight: '700', color: '#1f2937', margin: '0 0 0.5rem 0' }}>
            STORAGE MANAGER
          </h1>
          <p style={{ color: '#6b7280', fontSize: '1rem', margin: '0' }}>
            Welcome back! Enter your credentials.
          </p>
        </div>

        <div style={{ textAlign: 'left' }}>
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>
              Username
            </label>
            <input 
              type="text" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              placeholder="Enter your username"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>
              Password
            </label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              onKeyPress={handleKeyPress}
              placeholder="Enter your password"
              style={inputStyle}
            />
          </div>

          {error && (
            <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', padding: '0.75rem 1rem', borderRadius: '6px', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
              {error}
            </div>
          )}

          <button 
            onClick={handleLogin}
            style={buttonStyle}
            disabled={loading}
          >
            {loading ? 'Signing In...' : 'Sign In'}
          </button>
        </div>

        <div style={{ marginTop: '2rem', fontSize: '0.875rem', color: '#6b7280' }}>
          Don't have an account?{' '}
          <span 
            onClick={onSwitchToRegister} 
            style={{ color: '#D9383E', fontWeight: '600', cursor: 'pointer' }}
          >
            Sign Up
          </span>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
