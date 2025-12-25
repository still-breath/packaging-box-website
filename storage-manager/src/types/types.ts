// src/types.ts

export interface Box {
  id: string;
  quantity: number;
  length: number;
  width: number;
  height: number;
  weight: number;
  group: string;

  allowed_rotations?: number[] | string;
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
  activity_name?: string;
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
  logs?: string[];
}

export type ApiResponse = CalculationResult | ErrorResponse;
