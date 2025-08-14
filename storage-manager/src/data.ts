// src/data.ts
import { Container, Box, Group } from './types/types';

// Mendefinisikan tipe untuk preset
type Preset = {
  container: Container;
  boxes: Box[];
};

// Data untuk setiap jenis kontainer berdasarkan tabel Anda (dalam cm)
const containerData: { [key: string]: Container } = {
  '10ft': {
    width: 234,
    length: 284,
    height: 238,
    maxWeight: 9360,
  },
  '20ft': {
    width: 234,
    length: 591.9,
    height: 238,
    maxWeight: 18725,
  },
  '40ft': {
    width: 234,
    length: 1204.5,
    height: 238,
    maxWeight: 22000,
  },
};

// Data untuk setiap jenis box berdasarkan tabel Anda (dalam cm)
// Urutan dimensi: Panjang, Tinggi, Lebar
const allBoxesData = [
    { name: 'Box Rokok', dims: { length: 38, height: 41, width: 53 }, weight: 26.4, quantities: { '10ft': 15, '20ft': 35, '40ft': 70 } },
    { name: 'Box Sparepart 1', dims: { length: 53, height: 76, width: 53 }, weight: 20, quantities: { '10ft': 15, '20ft': 35, '40ft': 70 } },
    { name: 'Box Sparepart 2', dims: { length: 53, height: 58, width: 53 }, weight: 16, quantities: { '10ft': 15, '20ft': 30, '40ft': 70 } },
    { name: 'Box Sparepart 3', dims: { length: 55, height: 33, width: 55 }, weight: 12, quantities: { '10ft': 15, '20ft': 30, '40ft': 70 } },
    { name: 'Box elektronik', dims: { length: 39, height: 38, width: 24 }, weight: 13.8, quantities: { '10ft': 25, '20ft': 50, '40ft': 90 } },
    { name: 'Box Pos', dims: { length: 30.6, height: 102, width: 34.3 }, weight: 8, quantities: { '10ft': 15, '20ft': 30, '40ft': 65 } },
    { name: 'Box Kabel', dims: { length: 63.5, height: 46.5, width: 34 }, weight: 20, quantities: { '10ft': 15, '20ft': 30, '40ft': 65 } },
    { name: 'Box Dispenser Air', dims: { length: 61, height: 56, width: 61 }, weight: 17, quantities: { '10ft': 25, '20ft': 50, '40ft': 90 } },
];

// Fungsi untuk menghasilkan daftar box berdasarkan jenis kontainer
const getBoxesForPreset = (preset: '10ft' | '20ft' | '40ft'): Box[] => {
    return allBoxesData.map((box, index) => ({
        id: `box-${index + 1}`,
        quantity: box.quantities[preset],
        length: box.dims.length,
        width: box.dims.width,
        height: box.dims.height,
        weight: box.weight,
        group: box.name, // Menggunakan nama box sebagai grup default
    }));
};

// Gabungkan semua data ke dalam satu objek preset yang diekspor
export const presets: { [key: string]: Preset } = {
  '10ft': {
    container: containerData['10ft'],
    boxes: getBoxesForPreset('10ft'),
  },
  '20ft': {
    container: containerData['20ft'],
    boxes: getBoxesForPreset('20ft'),
  },
  '40ft': {
    container: containerData['40ft'],
    boxes: getBoxesForPreset('40ft'),
  },
};

// Membuat grup default dari nama-nama box
export const getDefaultGroups = (): Group[] => {
    const colors = ['#A95E90', '#6C6C9E', '#3E8E7E', '#E4A84F', '#D1603D', '#A44A3F', '#4A442D', '#5E4B56'];
    return allBoxesData.map((box, index) => ({
        id: `group-${index + 1}`,
        name: box.name,
        color: colors[index % colors.length],
    }));
};
