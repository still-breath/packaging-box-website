// src/types.ts

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

export interface CalculationResult {
  fillRate: number; 
  totalWeight: number; 
  placedItems: PlacedBox[];
  unplacedItems: Box[];
  error?: never; 
}

export interface Group {
  id: string;
  name: string;
  color: string;
}

export type ApiResponse = CalculationResult | { error: string };
