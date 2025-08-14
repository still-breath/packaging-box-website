import random
import copy
import time
import json
from typing import List, Dict, Optional, Tuple

class Box:
    """Mendefinisikan properti dan perilaku sebuah boks dengan constraint."""
    def __init__(self, name: str, length: float, width: float, height: float, weight: float, group_name: str,
                 allowed_rotations: Optional[List[int]] = None,
                 max_stack_weight: Optional[float] = None,
                 priority: Optional[int] = None,
                 destination_group: Optional[int] = None):
        
        self.name = name
        self.group_name = group_name
        self.original_dims = (float(length), float(width), float(height))
        self.weight = float(weight)
        self.length, self.width, self.height = self.original_dims
        self.x, self.y, self.z, self.rotation_type = 0, 0, 0, 0
        
        # PERBAIKAN: Handle nilai None secara eksplisit untuk mencegah error perbandingan
        self.allowed_rotations = list(range(6)) if allowed_rotations is None else allowed_rotations
        self.max_stack_weight = float('inf') if max_stack_weight is None else max_stack_weight
        self.priority = 5 if priority is None else priority
        self.destination_group = 99 if destination_group is None else destination_group

    def get_volume(self) -> float: return self.length * self.width * self.height
    def get_all_rotations(self) -> List[Tuple[float, float, float]]:
        l, w, h = self.original_dims
        return [(l, w, h), (l, h, w), (w, l, h), (w, h, l), (h, l, w), (h, w, l)]
    def set_rotation(self, rotation_index: int):
        rotations = self.get_all_rotations()
        if 0 <= rotation_index < len(rotations):
            self.length, self.width, self.height = rotations[rotation_index]
            self.rotation_type = rotation_index
    def __repr__(self): return f"{self.name} ({self.length}x{self.width}x{self.height}) at ({self.x},{self.y},{self.z})"

class Container:
    def __init__(self, name: str, length: float, width: float, height: float, max_weight: float):
        self.name, self.length, self.width, self.height, self.max_weight = name, length, width, height, max_weight
        self.packed_boxes = []
    def get_volume(self) -> float: return self.length * self.width * self.height
    def get_total_packed_volume(self) -> float: return sum(box.get_volume() for box in self.packed_boxes)
    def get_fill_rate(self) -> float: return (self.get_total_packed_volume() / self.get_volume()) * 100 if self.get_volume() > 0 else 0

def can_place_box(container: Container, box_to_place: Box, x: float, y: float, z: float, constraints: Dict) -> bool:
    if (x + box_to_place.length > container.length or y + box_to_place.width > container.width or z + box_to_place.height > container.height): return False
    for p_box in container.packed_boxes:
        if not (x + box_to_place.length <= p_box.x or p_box.x + p_box.length <= x or y + box_to_place.width <= p_box.y or p_box.y + p_box.width <= y or z + box_to_place.height <= p_box.z or p_box.z + p_box.height <= z): return False
    if constraints.get('enforceStacking', False):
        if z > 0:
            support = 0
            for p_box in container.packed_boxes:
                if abs(p_box.z + p_box.height - z) < 0.01:
                    overlap_x = max(0, min(x + box_to_place.length, p_box.x + p_box.length) - max(x, p_box.x))
                    overlap_y = max(0, min(y + box_to_place.width, p_box.y + p_box.width) - max(y, p_box.y))
                    if overlap_x > 0 and overlap_y > 0:
                        if box_to_place.weight > p_box.max_stack_weight: return False
                        if box_to_place.weight > p_box.weight: return False
                        support += overlap_x * overlap_y
            if box_to_place.get_volume() > 0 and (support / (box_to_place.length * box_to_place.width)) < 0.7: return False
    return True

def find_best_position(container: Container, box: Box, constraints: Dict) -> Optional[Tuple[float, float, float]]:
    best_pos, min_z, min_y, min_x = None, float('inf'), float('inf'), float('inf')
    positions = [(0,0,0)] + [(p.x + p.length, p.y, p.z) for p in container.packed_boxes] + [(p.x, p.y + p.width, p.z) for p in container.packed_boxes] + [(p.x, p.y, p.z + p.height) for p in container.packed_boxes]
    for x, y, z in sorted(list(set(positions))):
        if not can_place_box(container, box, x, y, z, constraints): continue
        if z < min_z or (z == min_z and y < min_y) or (z == min_z and y == min_y and x < min_x):
            min_z, min_y, min_x, best_pos = z, y, x, (x, y, z)
    return best_pos

class GeneticAlgorithm:
    def __init__(self, boxes: List[Box], container: Container, constraints: Dict, population_size=50, generations=100, mutation_rate=0.1, crossover_rate=0.8, elitism_count=2):
        self.boxes, self.container, self.constraints = boxes, container, constraints if constraints else {}
        self.population_size, self.generations, self.mutation_rate, self.crossover_rate, self.elitism_count = population_size, generations, mutation_rate, crossover_rate, elitism_count
        self.population = []
    def _create_individual(self) -> Tuple[List[int], List[int]]:
        order = list(range(len(self.boxes)))
        random.shuffle(order)
        rots = [random.choice(self.boxes[i].allowed_rotations) for i in range(len(self.boxes))]
        return (order, rots)
    def _initialize_population(self): self.population = [self._create_individual() for _ in range(self.population_size)]
    def _calculate_fitness(self, individual: Tuple[List[int], List[int]]) -> Tuple[float, List[Box], List[Box]]:
        box_order, rotation_order = individual
        eval_container = Container("Eval", self.container.length, self.container.width, self.container.height, self.container.max_weight)
        
        # Buat daftar boks yang akan diproses
        processing_boxes = [copy.deepcopy(self.boxes[i]) for i in box_order]
        
        # Urutkan berdasarkan LIFO jika aktif
        if self.constraints.get('enforceLIFO', False):
            processing_boxes.sort(key=lambda b: b.destination_group)
        
        unpacked = []
        for i in range(len(processing_boxes)):
            box = processing_boxes[i]
            # Temukan indeks rotasi yang sesuai dari individu
            original_index = self.boxes.index(next(b for b in self.boxes if b.name == box.name))
            rotation_idx_for_this_box = rotation_order[box_order.index(original_index)]
            
            box.set_rotation(rotation_idx_for_this_box)
            pos = find_best_position(eval_container, box, self.constraints)
            if pos:
                box.x, box.y, box.z = pos
                eval_container.packed_boxes.append(box)
            else:
                unpacked.append(box)

        fitness = eval_container.get_fill_rate()
        if self.constraints.get('enforceLoadCapacity', False):
            weight = sum(b.weight for b in eval_container.packed_boxes)
            if weight > self.container.max_weight: fitness -= ((weight - self.container.max_weight) / self.container.max_weight) * 100
        if self.constraints.get('enforcePriority', False):
            fitness -= sum((1 / box.priority) * 100 for box in unpacked)
        return max(0, fitness), eval_container.packed_boxes, unpacked
    def _selection(self, pop_fit):
        tour = random.sample(pop_fit, 5)
        tour.sort(key=lambda x: x[0], reverse=True)
        return tour[0][1]
    def _crossover(self, p1, p2):
        if random.random() > self.crossover_rate: return p1, p2
        o1, r1 = p1; o2, r2 = p2
        s, e = sorted(random.sample(range(len(o1)), 2))
        c_o = [None] * len(o1)
        c_o[s:e+1] = o1[s:e+1]
        fill = [i for i in o2 if i not in c_o]
        idx = 0
        for i in range(len(c_o)):
            if c_o[i] is None: c_o[i] = fill[idx]; idx += 1
        cp = random.randint(1, len(r1) - 1)
        c_r = r1[:cp] + r2[cp:]
        return (c_o, c_r), p2
    def _mutate(self, ind):
        o, r = ind
        if random.random() < self.mutation_rate:
            i1, i2 = random.sample(range(len(o)), 2)
            o[i1], o[i2] = o[i2], o[i1]
            idx_mut = random.randint(0, len(r) - 1)
            o_idx = o[idx_mut]
            r[idx_mut] = random.choice(self.boxes[o_idx].allowed_rotations)
        return (o, r)
    def run(self):
        self._initialize_population()
        best_sol, best_fit = None, -1.0
        for gen in range(self.generations):
            pop_fit = [(self._calculate_fitness(ind)[0], ind) for ind in self.population]
            pop_fit.sort(key=lambda x: x[0], reverse=True)
            if pop_fit[0][0] > best_fit:
                best_fit = pop_fit[0][0]
                best_sol = self._calculate_fitness(pop_fit[0][1])
            new_pop = [pop_fit[i][1] for i in range(self.elitism_count)]
            while len(new_pop) < self.population_size:
                p1, p2 = self._selection(pop_fit), self._selection(pop_fit)
                c1, _ = self._crossover(p1, p2)
                new_pop.append(self._mutate(c1))
            self.population = new_pop
            print(f"Generasi {gen+1}/{self.generations} | Fitness: {best_fit:.2f}")
        return best_sol

def format_results_for_frontend(result: Tuple, container: Container, initial_groups: List[Dict]) -> Optional[Dict]:
    if not result: return None
    _, packed_boxes, unpacked_boxes = result
    colors = {g['name']: g['color'] for g in initial_groups}
    weight = sum(b.weight for b in packed_boxes)
    volume = sum(b.get_volume() for b in packed_boxes)
    c_vol = container.get_volume()
    fill = (volume / c_vol * 100) if c_vol > 0 else 0
    placed = [{"id": b.name, "x": b.x, "y": b.y, "z": b.z, "length": b.length, "width": b.width, "height": b.height, "weight": b.weight, "color": colors.get(b.group_name, "#CCCCCC")} for b in packed_boxes]
    unplaced = [{"id": b.name, "quantity": 1, "length": b.original_dims[0], "width": b.original_dims[1], "height": b.original_dims[2], "weight": b.weight, "group": b.group_name} for b in unpacked_boxes]
    return {"fillRate": fill, "totalWeight": weight, "placedItems": placed, "unplacedItems": unplaced}
