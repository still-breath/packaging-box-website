// src/pages/RegisterPage.tsx
import React, { useState } from 'react';
import { registerUser } from '../api';

interface RegisterPageProps {
  onRegister: (credentials: { username: string; email: string; password: string }) => Promise<void>;
  onSwitchToLogin: () => void;
  isLoading?: boolean;
}

const RegisterPage: React.FC<RegisterPageProps> = ({ onRegister, onSwitchToLogin, isLoading: propIsLoading }) => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [success, setSuccess] = useState<boolean>(false);

  const handleRegister = async (): Promise<void> => {
    const { username, email, password, confirmPassword } = formData;
    
    if (!username || !email || !password || !confirmPassword) {
      setError('All fields are required');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (!email.includes('@')) {
      setError('Please enter a valid email address');
      return;
    }
    setLoading(true);
    setError('');
    setSuccess(false);
    try {
      await registerUser({
        username: formData.username,
        email: formData.email,
        password: formData.password
      });
      setSuccess(true);
      setTimeout(() => {
        window.location.href = '/login';
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Failed to register. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter') {
      handleRegister();
    }
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
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.75rem 1rem',
    marginBottom: '1rem',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    fontSize: '1rem',
    backgroundColor: '#f9fafb',
    outline: 'none',
    transition: 'all 0.3s',
  };

  const buttonStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.75rem 1rem',
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '1rem',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.3s',
    marginTop: '1.5rem',
    opacity: loading ? 0.7 : 1,
  };

  const titleStyle: React.CSSProperties = {
    fontSize: '1.75rem',
    fontWeight: '600',
    color: '#111827',
    marginBottom: '0.5rem',
    textAlign: 'center',
  };

  const subtitleStyle: React.CSSProperties = {
    color: '#6b7280',
    fontSize: '1rem',
    marginBottom: '2rem',
    textAlign: 'center',
  };

  const errorStyle: React.CSSProperties = {
    backgroundColor: '#fee2e2',
    border: '1px solid #fecaca',
    color: '#dc2626',
    padding: '0.75rem 1rem',
    borderRadius: '6px',
    fontSize: '0.875rem',
    marginBottom: '1rem',
    textAlign: 'center',
  };

  const successStyle: React.CSSProperties = {
    backgroundColor: '#dcfce7',
    border: '1px solid #bbf7d0',
    color: '#16a34a',
    padding: '0.75rem 1rem',
    borderRadius: '6px',
    fontSize: '0.875rem',
    marginBottom: '1rem',
    textAlign: 'center',
  };

  const linkStyle: React.CSSProperties = {
    color: '#3b82f6',
    textDecoration: 'none',
    fontWeight: '500',
    cursor: 'pointer',
  };

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <h1 style={titleStyle}>Create your account</h1>
        <p style={subtitleStyle}>Get started with our platform today</p>

        {error && <div style={errorStyle}>{error}</div>}
        {success && <div style={successStyle}>Registration successful! Redirecting...</div>}

        <input
          type="text"
          name="username"
          placeholder="Username"
          value={formData.username}
          onChange={handleChange}
          onKeyPress={handleKeyPress}
          style={inputStyle}
          disabled={loading}
        />

        <input
          type="email"
          name="email"
          placeholder="Email address"
          value={formData.email}
          onChange={handleChange}
          onKeyPress={handleKeyPress}
          style={inputStyle}
          disabled={loading}
        />

        <input
          type="password"
          name="password"
          placeholder="Password"
          value={formData.password}
          onChange={handleChange}
          onKeyPress={handleKeyPress}
          style={inputStyle}
          disabled={loading}
        />

        <input
          type="password"
          name="confirmPassword"
          placeholder="Confirm password"
          value={formData.confirmPassword}
          onChange={handleChange}
          onKeyPress={handleKeyPress}
          style={inputStyle}
          disabled={loading}
        />

        <button
          onClick={handleRegister}
          disabled={loading}
          style={buttonStyle}
        >
          {loading ? 'Creating account...' : 'Sign up'}
        </button>

        <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
          <p style={{ color: '#6b7280' }}>
            Already have an account?{' '}
            <span
              onClick={onSwitchToLogin}
              style={linkStyle}
            >
              Sign in
            </span>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
