// src/api/index.ts

import { UserCredentials, ApiResponse } from '../types/types';

const API_BASE_URL = 'http://localhost:8080';

// --- Auth API --- 

export const registerUser = async (credentials: UserCredentials) => {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || 'Registration failed');
  }

  return response.json();
};

export const loginUser = async (credentials: UserCredentials) => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || 'Login failed');
  }

  const data = await response.json();
  return data.token;
};

// --- Calculation API --- 

export const postCalculation = async (requestBody: any, token: string): Promise<ApiResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/calculate/golang`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || 'Calculation request failed');
  }

  return response.json();
};
