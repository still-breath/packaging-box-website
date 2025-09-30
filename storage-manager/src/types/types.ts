// src/types.ts

// --- Model Types ---
export interface Box {
  id: string;
  quantity: number;
  length: number;
  width: number;
  height: number;
  weight: number;
  group: string;

  // Properti untuk constraint (opsional)
  allowed_rotations?: number[] | string; // Izinkan string untuk input UI sementara
  max_stack_weight?: number;
  priority?: number;
  destination_group?: number;
}

export interface Container {
  length: number;
  width: number;
  height: number;
  maxWeight: number; 
}

export interface PlacedBox {
  id: string;
  x: number;
  y: number;
  z: number;
  length: number;
  width: number;
  height: number;
  weight: number;
  color: string;
}

export interface Group {
  id: string;
  name: string;
  color: string;
}

// --- Request Types ---
export interface UserCredentials {
  username: string;
  password: string;
  email?: string;
}

export interface CalculationRequest {
  container: Container;
  items: Box[];
  groups: Group[];
  algorithm: string;
  constraints: {
    enforceLoadCapacity: boolean;
    enforceStacking: boolean;
    enforcePriority: boolean;
    enforceLIFO: boolean;
  };
}

// --- Response Types ---
export interface ErrorResponse {
  error: string;
}

export interface RegisterResponse {
  message: string;
  user_id: number;
}

export interface LoginResponse {
  token: string;
}

export interface CalculationResult {
  fillRate: number; 
  totalWeight: number; 
  placedItems: PlacedBox[];
  unplacedItems: Box[];
}

export type ApiResponse = CalculationResult | ErrorResponse;
