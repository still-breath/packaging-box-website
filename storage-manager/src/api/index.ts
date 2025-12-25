// src/api/index.ts

import { 
  UserCredentials, 
  ApiResponse, 
  RegisterResponse, 
  LoginResponse, 
  CalculationRequest,
  ErrorResponse 
} from '../types/types';

// Read base URLs from environment for easier local/docker configs
const API_BASE_URL = (process.env.REACT_APP_API_BASE_URL || process.env.API_BASE_URL) || 'http://localhost:8080';
const PY_API_BASE_URL = (process.env.REACT_APP_PY_API_BASE_URL || process.env.PY_API_BASE_URL) || 'http://localhost:8000';

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

export const importExcel = async (file: File): Promise<any> => {
  const fd = new FormData();
  fd.append('file', file);
  const resp = await fetch(`${PY_API_BASE_URL}/import/excel`, {
    method: 'POST',
    body: fd
  });
  if (!resp.ok) throw new Error('Failed to import excel');
  return await resp.json();
};

export const exportExcel = async (payload: any): Promise<Blob> => {
  const resp = await fetch(`${PY_API_BASE_URL}/export/excel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error('Failed to export excel');
  return await resp.blob();
};

// --- Item Groups API ---

export const getItemGroups = async (token: string | null): Promise<Array<{id: number; name: string; color: string}>> => {
  const headers: any = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE_URL}/api/item-groups`, { headers });
  if (!resp.ok) throw new Error('Failed to fetch item groups');
  return await resp.json();
};

export const createItemGroup = async (name: string, color: string, token: string | null) => {
  if (!token) throw new Error('Authentication required to create group');
  const resp = await fetch(`${API_BASE_URL}/api/item-groups`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ name, color })
  });
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(txt || 'Failed to create item group');
  }
  return await resp.json();
};

export const updateItemGroup = async (id: number | string, name: string, color: string, token: string | null) => {
  if (!token) throw new Error('Authentication required to update group');
  const resp = await fetch(`${API_BASE_URL}/api/item-groups/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ name, color })
  });
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(txt || 'Failed to update item group');
  }
  return await resp.json();
};

export const deleteItemGroup = async (id: number | string, token: string | null) => {
  if (!token) throw new Error('Authentication required to delete group');
  const resp = await fetch(`${API_BASE_URL}/api/item-groups/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
  });
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(txt || 'Failed to delete item group');
  }
  return await resp.json();
};

// --- Calculations / History ---
export const getCalculations = async (token: string | null) => {
  const headers: any = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE_URL}/api/calculations`, { headers });
  if (!resp.ok) throw new Error('Failed to fetch calculations');
  return await resp.json();
};

export const getCalculationById = async (id: number | string, token: string | null) => {
  const headers: any = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE_URL}/api/calculations/${id}`, { headers });
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(txt || 'Failed to fetch calculation');
  }
  return await resp.json();
};

export const deleteCalculation = async (id: number | string, token: string | null) => {
  if (!token) throw new Error('Authentication required');
  const resp = await fetch(`${API_BASE_URL}/api/calculations/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
  });
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(txt || 'Failed to delete calculation');
  }
  return await resp.json();
};
