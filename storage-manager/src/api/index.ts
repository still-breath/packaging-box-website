// src/api/index.ts

import { 
  UserCredentials, 
  ApiResponse, 
  RegisterResponse, 
  LoginResponse, 
  CalculationRequest,
  ErrorResponse 
} from '../types/types';

const API_BASE_URL = 'http://localhost:8080';

// --- Auth API --- 

export const registerUser = async (credentials: UserCredentials): Promise<RegisterResponse> => {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error((data as ErrorResponse).error || 'Registration failed');
  }

  return data as RegisterResponse;
};

export const loginUser = async (credentials: UserCredentials): Promise<string> => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error((data as ErrorResponse).error || 'Login failed');
  }

  return (data as LoginResponse).token;
};

// --- Calculation API --- 

export const postCalculation = async (requestBody: CalculationRequest, token: string): Promise<ApiResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/calculate/golang`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(requestBody),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error((data as ErrorResponse).error || 'Calculation request failed');
  }

  return data as ApiResponse;
};
