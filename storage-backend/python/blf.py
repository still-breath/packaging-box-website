import itertools
import copy
from typing import List, Tuple, Dict, Optional
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

class Box:
    def __init__(self, name: str, length: float, width: float, height: float, weight: float, 
                 quantity: int = 1,
                 # Properti constraint dari kode pertama
                 allowed_rotations: Optional[List[int]] = None,
                 max_stack_weight: Optional[float] = None,
                 priority: Optional[int] = None,
                 destination_group: Optional[int] = None):
        
        self.name = name
        self.original_dims = (length, width, height)
        self.length = length
        self.width = width
        self.height = height
        self.weight = weight
        self.quantity = quantity
        self.x = 0
        self.y = 0
        self.z = 0
        self.rotation_type = "Original"
        
        # Handle nilai None secara eksplisit untuk mencegah error perbandingan
        self.allowed_rotations = list(range(6)) if allowed_rotations is None else allowed_rotations
        self.max_stack_weight = float('inf') if max_stack_weight is None else max_stack_weight
        self.priority = 5 if priority is None else priority
        self.destination_group = 99 if destination_group is None else destination_group
    
    def get_volume(self) -> float:
        return self.length * self.width * self.height
    
    def get_all_rotations(self) -> List[Tuple[float, float, float, str]]:
        """Mendapatkan semua kemungkinan rotasi dari box yang diizinkan."""
        l, w, h = self.original_dims
        # Rotasi diberi nomor indeks 0-5
        all_rots = [
            (l, w, h, "0: LWH"), (l, h, w, "1: LHW"),
            (w, l, h, "2: WLH"), (w, h, l, "3: WHL"),
            (h, l, w, "4: HLW"), (h, w, l, "5: HWL")
        ]
        
        return [all_rots[i] for i in self.allowed_rotations]
    
    def set_rotation(self, length: float, width: float, height: float, rotation_type: str):
        self.length = length
        self.width = width
        self.height = height
        self.rotation_type = rotation_type
    
    def set_position(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z
    
    def __repr__(self):
        return f"{self.name} ({self.length}x{self.width}x{self.height}) at ({self.x},{self.y},{self.z}) - {self.rotation_type}"

class Container:
    def __init__(self, name: str, length: float, width: float, height: float, max_weight: float):
        self.name = name
        self.length = length
        self.width = width
        self.height = height
        self.max_weight = max_weight
        self.packed_boxes = []
        self.unpacked_boxes = []
        self.total_weight = 0
        self.total_volume = 0
    
    def get_volume(self) -> float:
        return self.length * self.width * self.height
    
    def get_fill_rate(self) -> float:
        if self.get_volume() == 0:
            return 0
        return (self.total_volume / self.get_volume()) * 100
    
    def can_fit_box(self, box: Box, x: float, y: float, z: float, constraints: Dict) -> bool:
        """Memeriksa apakah box bisa muat dengan mempertimbangkan semua constraint yang aktif."""
        # Cek dimensi dasar
        if (x + box.length > self.length or 
            y + box.width > self.width or 
            z + box.height > self.height):
            return False
        
        # Cek kapasitas berat jika constraint aktif
        if constraints.get('enforceLoadCapacity', False):
            if self.total_weight + box.weight > self.max_weight:
                return False
        
        # Cek overlap dengan box lain
        for packed_box in self.packed_boxes:
            if self._boxes_overlap(box, x, y, z, packed_box):
                return False
        
        # Cek stabilitas stacking jika constraint aktif
        if constraints.get('enforceStacking', False):
            if not self._is_stable(box, x, y, z):
                return False
        
        return True
    
    def _is_stable(self, box_to_place: Box, x: float, y: float, z: float) -> bool:
        """Memeriksa apakah box stabil di posisi yang diberikan."""
        # Box di ground level selalu stabil
        if z == 0:
            return True
        
        total_support_area = 0
        for p_box in self.packed_boxes:
            # Cek apakah packed box berada tepat di bawah box yang akan ditempatkan
            if abs(p_box.z + p_box.height - z) < 0.01:
                # Hitung area overlap
                overlap_x = max(0, min(x + box_to_place.length, p_box.x + p_box.length) - max(x, p_box.x))
                overlap_y = max(0, min(y + box_to_place.width, p_box.y + p_box.width) - max(y, p_box.y))
                
                if overlap_x > 0 and overlap_y > 0:
                    # Cek constraint berat stacking
                    if box_to_place.weight > p_box.max_stack_weight:
                        return False
                    
                    # Box yang lebih berat tidak boleh di atas box yang lebih ringan
                    if box_to_place.weight > p_box.weight:
                        return False
                    
                    total_support_area += overlap_x * overlap_y
        
        # Minimal 70% dari base area harus ditopang
        base_area = box_to_place.length * box_to_place.width
        if base_area > 0 and (total_support_area / base_area) < 0.7:
            return False
        
        return True
    
    def _boxes_overlap(self, box1: Box, x1: float, y1: float, z1: float, box2: Box) -> bool:
        """Memeriksa apakah dua box tumpang tindih."""
        return not (x1 + box1.length <= box2.x or 
                   box2.x + box2.length <= x1 or
                   y1 + box1.width <= box2.y or 
                   box2.y + box2.width <= y1 or
                   z1 + box1.height <= box2.z or 
                   box2.z + box2.height <= z1)
    
    def add_box(self, box: Box, x: float, y: float, z: float):
        """Menambahkan box ke kontainer di posisi yang ditentukan."""
        box.set_position(x, y, z)
        self.packed_boxes.append(box)
        self.total_weight += box.weight
        self.total_volume += box.get_volume()
    
    def reset(self):
        """Mereset kontainer ke keadaan kosong."""
        self.packed_boxes = []
        self.unpacked_boxes = []
        self.total_weight = 0
        self.total_volume = 0

class ContainerPackingOptimizer:
    def __init__(self):
        self.containers = {
            "10ft": Container("10 Feet", 284, 234, 238, 9360),
            "20ft": Container("20 Feet", 591.9, 234, 238, 18725),
            "40ft": Container("40 Feet", 1204.5, 234, 238, 22000)
        }
        
        self.box_data = [
            {"name": "Box Rokok", "dims": (38, 53, 41), "weight": 26.4, "quantities": {"10ft": 15, "20ft": 35, "40ft": 70}},
            {"name": "Box Sparepart 1", "dims": (53, 53, 76), "weight": 20, "quantities": {"10ft": 15, "20ft": 35, "40ft": 70}},
            {"name": "Box Sparepart 2", "dims": (53, 53, 58), "weight": 16, "quantities": {"10ft": 15, "20ft": 30, "40ft": 70}},
            {"name": "Box Sparepart 3", "dims": (55, 55, 33), "weight": 12, "quantities": {"10ft": 15, "20ft": 30, "40ft": 70}},
            {"name": "Box elektronik", "dims": (39, 24, 38), "weight": 13.8, "quantities": {"10ft": 25, "20ft": 50, "40ft": 90}},
            {"name": "Box Pos", "dims": (30.6, 34.3, 102), "weight": 8, "quantities": {"10ft": 15, "20ft": 30, "40ft": 65}},
            {"name": "Box Kabel", "dims": (63.5, 34, 46.5), "weight": 20, "quantities": {"10ft": 15, "20ft": 30, "40ft": 65}},
            {"name": "Box Dispenser Air", "dims": (61, 61, 56), "weight": 17, "quantities": {"10ft": 25, "20ft": 50, "40ft": 90}}
        ]
    
    def create_box_list(self, container_type: str) -> List[Box]:
        """Membuat daftar semua box dengan jumlah yang sesuai untuk jenis kontainer."""
        boxes = []
        for item in self.box_data:
            name = item["name"]
            length, width, height = item["dims"]
            weight = item["weight"]
            quantity = item["quantities"].get(container_type, 0)
            
            for i in range(quantity):
                box_name = f"{name}_{i+1}"
                # Tambahkan constraint default untuk setiap box
                box = Box(
                    box_name, length, width, height, weight,
                    # Constraint default - bisa disesuaikan per jenis box
                    allowed_rotations=None,  # Semua rotasi diizinkan
                    max_stack_weight=weight * 2,  # Maksimal 2x berat sendiri
                    priority=5,  # Priority default
                    destination_group=99  # Group default
                )
                boxes.append(box)
        return boxes
    
    def bottom_left_fill_algorithm(self, container: Container, boxes: List[Box], constraints: Dict) -> Tuple[List[Box], List[Box]]:
        """Algoritma Bottom-Left Fill dengan dukungan rotasi dan constraint."""
        container.reset()
        boxes_copy = copy.deepcopy(boxes)
        
        # Sorting berdasarkan constraint aktif
        sort_keys = []
        if constraints.get('enforceLIFO', False):
            sort_keys.append(lambda b: b.destination_group)
        if constraints.get('enforcePriority', False):
            sort_keys.append(lambda b: b.priority)
        
        # Selalu sort berdasarkan volume sebagai tie-breaker
        sort_keys.append(lambda b: -b.get_volume())
        
        # Apply sorting
        boxes_copy.sort(key=lambda b: tuple(key(b) for key in sort_keys))
        
        packed = []
        unpacked = []
        
        for box in boxes_copy:
            best_position = None
            best_rotation = None
            best_score = float('inf')
            
            # Coba semua rotasi yang diizinkan
            for rotation in box.get_all_rotations():
                length, width, height, rotation_type = rotation
                temp_box = copy.deepcopy(box)
                temp_box.set_rotation(length, width, height, rotation_type)
                
                # Generate posisi yang mungkin
                positions = self._generate_positions(container)
                
                for x, y, z in positions:
                    if container.can_fit_box(temp_box, x, y, z, constraints):
                        # Scoring: prioritas Z (tinggi), lalu Y, lalu X
                        score = z * 1e9 + y * 1e6 + x
                        if score < best_score:
                            best_score = score
                            best_position = (x, y, z)
                            best_rotation = rotation
            
            # Place box jika posisi dan rotasi terbaik ditemukan
            if best_position and best_rotation:
                length, width, height, rotation_type = best_rotation
                box.set_rotation(length, width, height, rotation_type)
                container.add_box(box, *best_position)
                packed.append(box)
            else:
                unpacked.append(box)
        
        return packed, unpacked
    
    def _generate_positions(self, container: Container) -> List[Tuple[float, float, float]]:
        """Menghasilkan posisi yang memungkinkan untuk menempatkan box."""
        positions = [(0, 0, 0)]
        
        # Tambahkan posisi berdasarkan box yang sudah ada
        for packed_box in container.packed_boxes:
            positions.extend([
                (packed_box.x + packed_box.length, packed_box.y, packed_box.z),
                (packed_box.x, packed_box.y + packed_box.width, packed_box.z),
                (packed_box.x, packed_box.y, packed_box.z + packed_box.height)
            ])
        
        # Return posisi yang unik dan terurut
        return sorted(list(set(positions)))
    
    def optimize_packing(self, container_type: str = "20ft", algorithm: str = "bottom_left", 
                        constraints: Dict = None) -> Dict:
        """Fungsi optimisasi utama dengan dukungan constraint."""
        if container_type not in self.containers:
            raise ValueError(f"Jenis kontainer tidak valid: {container_type}")
        
        # Default constraints
        if constraints is None:
            constraints = {
                'enforceLoadCapacity': True,
                'enforceStacking': True,
                'enforceLIFO': False,
                'enforcePriority': False
            }
        
        container = self.containers[container_type]
        boxes = self.create_box_list(container_type)
        
        if algorithm == "bottom_left":
            packed, unpacked = self.bottom_left_fill_algorithm(container, boxes, constraints)
        else:
            raise ValueError(f"Algoritma tidak valid: {algorithm}")
        
        container.packed_boxes = packed
        container.unpacked_boxes = unpacked
        
        return {
            "container": container,
            "packed_boxes": packed,
            "unpacked_boxes": unpacked,
            "fill_rate": container.get_fill_rate(),
            "weight_utilization": (container.total_weight / container.max_weight) * 100 if container.max_weight > 0 else 0,
            "total_boxes_packed": len(packed),
            "total_boxes_unpacked": len(unpacked),
            "constraints_used": constraints
        }
    
    def visualize_packing_3d(self, result: Dict):
        """Visualisasi packing dalam 3D."""
        container = result["container"]
        packed_boxes = result["packed_boxes"]
        
        fig = plt.figure(figsize=(15, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Gambar outline kontainer
        v = [
            (0, 0, 0), (container.length, 0, 0), (container.length, container.width, 0), (0, container.width, 0),
            (0, 0, container.height), (container.length, 0, container.height), 
            (container.length, container.width, container.height), (0, container.width, container.height)
        ]
        edges = [
            [v[0], v[1]], [v[1], v[2]], [v[2], v[3]], [v[3], v[0]],
            [v[4], v[5]], [v[5], v[6]], [v[6], v[7]], [v[7], v[4]],
            [v[0], v[4]], [v[1], v[5]], [v[2], v[6]], [v[3], v[7]]
        ]
        for edge in edges:
            points = np.array(edge)
            ax.plot(points[:, 0], points[:, 1], points[:, 2], 'k-', alpha=0.3)

        # Color mapping untuk box types
        cmap = plt.get_cmap('tab20', len(self.box_data))
        box_types = [item['name'] for item in self.box_data]
        color_map = {box_type: cmap(i) for i, box_type in enumerate(box_types)}
        
        # Gambar box
        for box in packed_boxes:
            box_type_name = box.name.rsplit('_', 1)[0]
            color = color_map.get(box_type_name, 'gray')
            
            # Tentukan vertices
            vertices = [
                (box.x, box.y, box.z),
                (box.x + box.length, box.y, box.z),
                (box.x + box.length, box.y + box.width, box.z),
                (box.x, box.y + box.width, box.z),
                (box.x, box.y, box.z + box.height),
                (box.x + box.length, box.y, box.z + box.height),
                (box.x + box.length, box.y + box.width, box.z + box.height),
                (box.x, box.y + box.width, box.z + box.height)
            ]
            
            # Tentukan faces
            faces = [
                [vertices[0], vertices[1], vertices[5], vertices[4]],
                [vertices[2], vertices[3], vertices[7], vertices[6]],
                [vertices[0], vertices[3], vertices[7], vertices[4]],
                [vertices[1], vertices[2], vertices[6], vertices[5]],
                [vertices[0], vertices[1], vertices[2], vertices[3]],
                [vertices[4], vertices[5], vertices[6], vertices[7]]
            ]
            
            ax.add_collection3d(Poly3DCollection(
                faces, 
                facecolors=color, 
                linewidths=1, 
                edgecolors='k', 
                alpha=0.7
            ))

        ax.set_xlabel('Panjang (cm)')
        ax.set_ylabel('Lebar (cm)')
        ax.set_zlabel('Tinggi (cm)')
        
        # Tambahkan informasi constraint di title
        constraints_info = []
        if result["constraints_used"].get('enforceLoadCapacity', False):
            constraints_info.append("Load Cap")
        if result["constraints_used"].get('enforceStacking', False):
            constraints_info.append("Stacking")
        if result["constraints_used"].get('enforceLIFO', False):
            constraints_info.append("LIFO")
        if result["constraints_used"].get('enforcePriority', False):
            constraints_info.append("Priority")
        
        constraint_str = ", ".join(constraints_info) if constraints_info else "No Constraints"
        ax.set_title(f'Visualisasi 3D Packing Kontainer {container.name}\n'
                    f'Fill Rate: {result["fill_rate"]:.1f}% | Constraints: {constraint_str}')
        
        ax.set_box_aspect([container.length, container.width, container.height])
        
        plt.tight_layout()
        plt.show()
    
    def print_results(self, result: Dict):
        """Mencetak hasil detail."""
        container = result["container"]
        packed_boxes = result["packed_boxes"]
        unpacked_boxes = result["unpacked_boxes"]
        
        print(f"\n{'='*70}")
        print(f"HASIL OPTIMISASI PACKING KONTAINER")
        print(f"{'='*70}")
        print(f"Kontainer: {container.name}")
        print(f"Dimensi: {container.length} x {container.width} x {container.height} cm")
        print(f"Berat Maks: {container.max_weight} kg")
        print(f"Volume Kontainer: {container.get_volume():,.0f} cm³")
        
        # Tampilkan constraint yang digunakan
        constraints = result["constraints_used"]
        print(f"\nCONSTRAINT YANG DIGUNAKAN:")
        print(f"- Load Capacity: {'✓' if constraints.get('enforceLoadCapacity', False) else '✗'}")
        print(f"- Stacking Rules: {'✓' if constraints.get('enforceStacking', False) else '✗'}")
        print(f"- LIFO (Destination): {'✓' if constraints.get('enforceLIFO', False) else '✗'}")
        print(f"- Priority Sorting: {'✓' if constraints.get('enforcePriority', False) else '✗'}")
        
        print(f"\n{'='*70}")
        print(f"RINGKASAN PACKING")
        print(f"{'='*70}")
        print(f"Fill Rate (Volume): {result['fill_rate']:.2f}%")
        print(f"Utilisasi Berat: {result['weight_utilization']:.2f}%")
        print(f"Total Volume Terpakai: {container.total_volume:,.0f} cm³")
        print(f"Total Berat Terpakai: {container.total_weight:.1f} kg")
        print(f"Box Berhasil Dimuat: {len(packed_boxes)}")
        print(f"Box Tidak Dimuat: {len(unpacked_boxes)}")
        
        print(f"\n{'='*70}")
        print(f"DETAIL BOX YANG DIMUAT")
        print(f"{'='*70}")
        for i, box in enumerate(packed_boxes, 1):
            print(f"{i:2d}. {box.name:25s} | "
                  f"Dims: {box.length:5.1f}x{box.width:5.1f}x{box.height:5.1f} | "
                  f"Pos: ({box.x:5.1f},{box.y:5.1f},{box.z:5.1f}) | "
                  f"Berat: {box.weight:4.1f}kg | "
                  f"Rotasi: {box.rotation_type}")
        
        if unpacked_boxes:
            print(f"\n{'='*70}")
            print(f"BOX YANG TIDAK DIMUAT")
            print(f"{'='*70}")
            for i, box in enumerate(unpacked_boxes, 1):
                print(f"{i:2d}. {box.name:25s} | "
                      f"Dims: {box.length:5.1f}x{box.width:5.1f}x{box.height:5.1f} | "
                      f"Berat: {box.weight:4.1f}kg")
        
        print(f"\n{'='*70}")

# Contoh penggunaan dengan berbagai constraint
def main():
    optimizer = ContainerPackingOptimizer()
    
    pilihan_kontainer = "20ft"
    
    # Contoh 1: Dengan semua constraint aktif
    print("="*70)
    print("CONTOH 1: DENGAN SEMUA CONSTRAINT AKTIF")
    print("="*70)
    
    constraints_full = {
        'enforceLoadCapacity': True,
        'enforceStacking': True,
        'enforceLIFO': False,
        'enforcePriority': False
    }
    
    result1 = optimizer.optimize_packing(
        container_type=pilihan_kontainer, 
        algorithm="bottom_left",
        constraints=constraints_full
    )
    
    optimizer.print_results(result1)
    print("\nMenghasilkan visualisasi 3D...")
    optimizer.visualize_packing_3d(result1)
    
    # Contoh 2: Tanpa constraint stacking
    print("\n" + "="*70)
    print("CONTOH 2: TANPA CONSTRAINT STACKING")
    print("="*70)
    
    constraints_no_stack = {
        'enforceLoadCapacity': True,
        'enforceStacking': False,
        'enforceLIFO': False,
        'enforcePriority': False
    }
    
    result2 = optimizer.optimize_packing(
        container_type=pilihan_kontainer, 
        algorithm="bottom_left",
        constraints=constraints_no_stack
    )
    
    optimizer.print_results(result2)
    print("\nMenghasilkan visualisasi 3D...")
    optimizer.visualize_packing_3d(result2)

if __name__ == "__main__":
    main()