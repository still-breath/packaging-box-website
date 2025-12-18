import gurobipy as gp
from gurobipy import GRB
import tempfile
import os
from typing import List, Dict, Any, Optional, Tuple
import math
import copy

# Import the functions from your new.py file
from new import solve_clp_with_boxes, greedy_clp_placement, get_valid_rotations, rotations

class CLPContainer:
    def __init__(self, length: float, width: float, height: float, max_weight: float):
        self.length = length
        self.width = width
        self.height = height
        self.max_weight = max_weight
        self.volume = length * width * height

class CLPBox:
    def __init__(self, id: int, dims: Tuple[float, float, float], weight: float, 
                 allowed_rotations: Optional[List[int]] = None, 
                 max_stack_weight: Optional[float] = None,
                 priority: Optional[int] = None, 
                 destination_group: Optional[int] = None):
        self.id = id
        self.dims = dims  # (length, width, height)
        self.weight = weight
        self.allowed_rotations = allowed_rotations if allowed_rotations is not None else list(range(6))
        self.max_stack_weight = max_stack_weight if max_stack_weight is not None else float('inf')
        self.priority = priority if priority is not None else 5
        self.destination_group = destination_group if destination_group is not None else 99
        
        # These will be set when the box is placed
        self.x = 0
        self.y = 0
        self.z = 0
        self.rotation = 0
        self.final_dims = dims

def solve_clp_with_gurobi(container: CLPContainer, boxes: List[CLPBox], 
                         constraints: Dict, time_limit: int = 600) -> Dict:
    """
    Enhanced Gurobi solver with flexible constraints
    """
    try:
        # Create temporary input file in thpack format
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_input:
            # Write container dimensions
            temp_input.write(f"{container.length} {container.width} {container.height}\n")
            
            # Write box dimensions (we'll add dummy arrival time of 0)
            for box in boxes:
                temp_input.write(f"{box.dims[0]} {box.dims[1]} {box.dims[2]} 0\n")
            
            temp_input_path = temp_input.name
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_output:
            temp_output_path = temp_output.name
        
        # Prepare data structures for the enhanced function
        boxes_dict = {}
        for i, box in enumerate(boxes, 1):
            boxes_dict[i] = (box.dims[0], box.dims[1], box.dims[2], 0)  # Add arrival time 0
        
        vehicles_dict = {1: (container.length, container.width, container.height)}
        
        # Call the enhanced optimization function with constraints
        enhanced_solve_clp_with_boxes(boxes_dict, vehicles_dict, temp_output_path, 
                                    time_limit, container, boxes, constraints)
        
        # Parse the output file
        result = parse_clp_output(temp_output_path, boxes)
        
        # Clean up temporary files
        os.unlink(temp_input_path)
        os.unlink(temp_output_path)
        
        return result
        
    except Exception as e:
        print(f"Error in solve_clp_with_gurobi: {e}")
        return {"error": str(e)}

def solve_clp_with_greedy(container: CLPContainer, boxes: List[CLPBox], 
                         constraints: Dict) -> Dict:
    """
    Enhanced greedy solver with flexible constraints
    """
    try:
        # Prepare data structures for the enhanced function
        boxes_dict = {}
        for i, box in enumerate(boxes, 1):
            boxes_dict[i] = (box.dims[0], box.dims[1], box.dims[2], 0)  # Add arrival time 0
        
        vehicles_dict = {1: (container.length, container.width, container.height)}
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_output:
            temp_output_path = temp_output.name
        
        # Call the enhanced greedy function with constraints
        enhanced_greedy_clp_placement(boxes_dict, vehicles_dict, temp_output_path, 
                                    container, boxes, constraints)
        
        # Parse the output file
        result = parse_clp_output(temp_output_path, boxes)
        
        # Clean up temporary file
        os.unlink(temp_output_path)
        
        return result
        
    except Exception as e:
        print(f"Error in solve_clp_with_greedy: {e}")
        return {"error": str(e)}

def parse_clp_output(output_file: str, original_boxes: List[CLPBox]) -> Dict:
    """
    Parse the output file from the CLP solver and return structured results
    """
    packed_boxes = []
    unpacked_boxes = []
    fill_rate = 0
    
    try:
        with open(output_file, 'r') as f:
            lines = f.readlines()
        
        # Create a mapping of box IDs to original boxes
        box_map = {i+1: box for i, box in enumerate(original_boxes)}
        placed_ids = set()
        
        # Parse placed boxes
        for line in lines:
            line = line.strip()
            if line and not line.startswith('Vehicle') and not line.startswith('Boxes') and not line.startswith('Mean') and not line.startswith('Fill') and not line.startswith('Time') and not line.startswith('MIP') and not line.startswith('Objective') and not line.startswith('Greedy'):
                parts = line.split('\t')
                if len(parts) >= 7:
                    try:
                        box_id = int(parts[0])
                        x = float(parts[1])
                        y = float(parts[2])
                        z = float(parts[3])
                        length = float(parts[4])
                        width = float(parts[5])
                        height = float(parts[6])
                        
                        if box_id in box_map:
                            original_box = box_map[box_id]
                            
                            # Create a new box object with placement info
                            placed_box = CLPBox(
                                id=original_box.id,
                                dims=original_box.dims,
                                weight=original_box.weight,
                                allowed_rotations=original_box.allowed_rotations,
                                max_stack_weight=original_box.max_stack_weight,
                                priority=original_box.priority,
                                destination_group=original_box.destination_group
                            )
                            
                            # Set placement coordinates and final dimensions
                            placed_box.x = x
                            placed_box.y = y
                            placed_box.z = z
                            placed_box.final_dims = (length, width, height)
                            
                            packed_boxes.append(placed_box)
                            placed_ids.add(box_id)
                    except (ValueError, IndexError):
                        continue
            
            # Extract fill rate
            if line.startswith('Fill rate:'):
                try:
                    fill_rate = float(line.split(':')[1].strip().replace('%', ''))
                except:
                    fill_rate = 0
        
        # Find unpacked boxes
        for i, box in enumerate(original_boxes, 1):
            if i not in placed_ids:
                unpacked_boxes.append(box)
        
        return {
            "packed": packed_boxes,
            "unpacked": unpacked_boxes,
            "fill_rate": fill_rate,
            "total_boxes": len(original_boxes),
            "packed_count": len(packed_boxes)
        }
        
    except Exception as e:
        print(f"Error parsing output: {e}")
        return {"error": f"Error parsing output: {e}"}

def enhanced_solve_clp_with_boxes(boxes_dict: Dict, vehicles_dict: Dict, 
                                 output_file: str, time_limit: int = 600,
                                 container: CLPContainer = None, 
                                 boxes: List[CLPBox] = None, 
                                 constraints: Dict = None):
    """
    Enhanced version with flexible constraints support
    """
    if not vehicles_dict:
        print("Data kontainer kosong.")
        return

    if constraints is None:
        constraints = {}

    # Asumsi hanya ada satu kontainer
    k = 1
    v_dims = vehicles_dict[k]
    Lmax, Wmax, Hmax = v_dims[0], v_dims[1], v_dims[2]
    container_volume = Lmax * Wmax * Hmax

    box_ids = list(boxes_dict.keys())
    
    # Enhanced box sorting with constraints
    def calculate_enhanced_priority(box_id, boxes, container_volume, boxes_objects, constraints):
        """Enhanced priority calculation with constraints"""
        b_dims = boxes[box_id]
        volume = b_dims[0] * b_dims[1] * b_dims[2]
        volume_ratio = volume / container_volume
        
        # Multi-criteria priority
        aspect_penalty = max(b_dims) / min(b_dims) if min(b_dims) > 0 else 1
        compactness = (b_dims[0] * b_dims[1] * b_dims[2]) / (b_dims[0] + b_dims[1] + b_dims[2])
        
        base_priority = (volume_ratio * compactness) / (aspect_penalty * 0.5 + 0.5)
        
        # Apply constraint-based adjustments
        if boxes_objects and constraints:
            box_obj = boxes_objects[box_id - 1]  # Convert to 0-based index
            
            # Priority constraint
            if constraints.get('enforcePriority', False):
                priority_bonus = (6 - box_obj.priority) * 0.2
                base_priority += priority_bonus
            
            # LIFO constraint (destination group)
            if constraints.get('enforceLIFO', False):
                lifo_bonus = (100 - box_obj.destination_group) * 0.01
                base_priority += lifo_bonus
        
        return base_priority
    
    # Sort boxes by enhanced priority with constraints
    if boxes:
        box_priorities = [(i, calculate_enhanced_priority(i, boxes_dict, container_volume, boxes, constraints)) 
                         for i in box_ids]
        box_priorities.sort(key=lambda x: x[1], reverse=True)
        sorted_box_ids = [x[0] for x in box_priorities]
    else:
        # Fallback to original sorting
        box_priorities = [(i, calculate_enhanced_priority(i, boxes_dict, container_volume, None, None)) 
                         for i in box_ids]
        box_priorities.sort(key=lambda x: x[1], reverse=True)
        sorted_box_ids = [x[0] for x in box_priorities]
    
    valid_rotations = {i: get_valid_rotations(boxes_dict[i], Lmax, Wmax, Hmax) for i in sorted_box_ids}
    
    # Filter only boxes with valid rotations and apply allowed_rotations constraint
    box_ids_with_valid = []
    for i in sorted_box_ids:
        if len(valid_rotations[i]) > 0:
            # Apply allowed_rotations constraint
            if boxes:
                box_obj = boxes[i - 1]  # Convert to 0-based index
                # Filter valid rotations by allowed rotations
                filtered_rotations = [(rid, rot) for rid, rot in valid_rotations[i] 
                                    if rid in box_obj.allowed_rotations]
                valid_rotations[i] = filtered_rotations
                if len(filtered_rotations) > 0:
                    box_ids_with_valid.append(i)
            else:
                box_ids_with_valid.append(i)
    
    # Reduced threshold for more optimization attempts
    # greedy_threshold = 20
    # if len(box_ids_with_valid) > greedy_threshold:
    #     print(f"INFO: Jumlah box {len(box_ids_with_valid)} > {greedy_threshold}. Menggunakan enhanced greedy mode.")
    #     enhanced_greedy_clp_placement(boxes_dict, vehicles_dict, output_file, container, boxes, constraints)
    #     return

    try:
        # Create Gurobi model with enhanced parameters
        model = gp.Model("Enhanced_CLP_Flexible")
        
        # Enhanced Gurobi parameters for better fill rate
        model.setParam("MIPFocus", 1)  # Focus on feasible solutions
        model.setParam("Heuristics", 0.9)  # Aggressive heuristics
        model.setParam("Presolve", 2)  # Aggressive presolve
        model.setParam("Cuts", 3)  # Very aggressive cuts
        model.setParam("MIPGap", 0.005)  # Tighter gap (0.5%)
        model.setParam("TimeLimit", time_limit)
        model.setParam("Threads", 6)  # More threads
        model.setParam("NodeMethod", 1)  # Dual simplex
        model.setParam("Method", 1)  # Dual simplex for root
        
        # Variables
        p = model.addVars(box_ids_with_valid, [k], vtype=GRB.BINARY, name="p")
        x = model.addVars(box_ids_with_valid, lb=0, ub=Lmax, name="x")
        y = model.addVars(box_ids_with_valid, lb=0, ub=Wmax, name="y")
        z = model.addVars(box_ids_with_valid, lb=0, ub=Hmax, name="z")
        r = model.addVars(box_ids_with_valid, range(len(rotations)), vtype=GRB.BINARY, name="r")

        # Non-overlapping variables
        a, b, c, d, e, f = {}, {}, {}, {}, {}, {}
        for i in box_ids_with_valid:
            for j in box_ids_with_valid:
                if i < j:
                    a[i, j] = model.addVar(vtype=GRB.BINARY, name=f"a_{i}_{j}")
                    b[i, j] = model.addVar(vtype=GRB.BINARY, name=f"b_{i}_{j}")
                    c[i, j] = model.addVar(vtype=GRB.BINARY, name=f"c_{i}_{j}")
                    d[i, j] = model.addVar(vtype=GRB.BINARY, name=f"d_{i}_{j}")
                    e[i, j] = model.addVar(vtype=GRB.BINARY, name=f"e_{i}_{j}")
                    f[i, j] = model.addVar(vtype=GRB.BINARY, name=f"f_{i}_{j}")

        # Enhanced objective function with constraints
        volume_term = gp.LinExpr()
        for i in box_ids_with_valid:
            base_volume = boxes_dict[i][0] * boxes_dict[i][1] * boxes_dict[i][2]
            volume_coefficient = base_volume
            
            # Apply constraint-based bonuses
            if boxes and constraints:
                box_obj = boxes[i - 1]  # Convert to 0-based index
                
                # Priority bonus
                if constraints.get('enforcePriority', False):
                    priority_bonus = (6 - box_obj.priority) * 0.1
                    volume_coefficient *= (1 + priority_bonus)
                
                # LIFO bonus
                if constraints.get('enforceLIFO', False):
                    lifo_bonus = (100 - box_obj.destination_group) * 0.005
                    volume_coefficient *= (1 + lifo_bonus)
            
            volume_term += p[i, k] * volume_coefficient
        
        # Stability bonus (prefer boxes with lower z-coordinates)
        stability_bonus = gp.quicksum(
            p[i, k] * (Hmax - z[i]) * 0.01  # Small bonus for lower placement
            for i in box_ids_with_valid
        )
        
        model.setObjective(volume_term + stability_bonus, GRB.MAXIMIZE)

        # Weight capacity constraint
        if constraints.get('enforceLoadCapacity', False) and container and boxes:
            total_weight = gp.quicksum(
                p[i, k] * boxes[i - 1].weight
                for i in box_ids_with_valid
            )
            model.addConstr(total_weight <= container.max_weight, "weight_capacity")

        # Stacking constraint
        if constraints.get('enforceStacking', False) and boxes:
            for i in box_ids_with_valid:
                box_obj = boxes[i - 1]
                if box_obj.max_stack_weight < float('inf'):
                    # Weight of boxes stacked on top of box i
                    weight_above = gp.quicksum(
                        p[j, k] * boxes[j - 1].weight
                        for j in box_ids_with_valid
                        if j != i
                    )
                    # This is a simplified constraint - in practice, you'd need more complex logic
                    # to determine which boxes are actually stacked on top
                    model.addConstr(
                        weight_above <= box_obj.max_stack_weight + 
                        (1 - p[i, k]) * sum(boxes[j - 1].weight for j in range(len(boxes))),
                        f"stacking_{i}"
                    )

        # Container constraints
        for i in box_ids_with_valid:
            b_dims = boxes_dict[i]
            for rid, rot in valid_rotations[i]:
                model.addConstr(x[i] + b_dims[rot[0]] <= Lmax + Lmax * (1 - r[i, rid]))
                model.addConstr(y[i] + b_dims[rot[1]] <= Wmax + Wmax * (1 - r[i, rid]))
                model.addConstr(z[i] + b_dims[rot[2]] <= Hmax + Hmax * (1 - r[i, rid]))

        # Rotation constraints
        for i in box_ids_with_valid:
            model.addConstr(gp.quicksum(r[i, rid] for rid, _ in valid_rotations[i]) == p[i, k])
            for rid in range(len(rotations)):
                if rid not in [v[0] for v in valid_rotations[i]]:
                    model.addConstr(r[i, rid] == 0)

        # Enhanced non-overlapping constraints
        for i in box_ids_with_valid:
            for j in box_ids_with_valid:
                if i < j:
                    b_dims_i = boxes_dict[i]
                    b_dims_j = boxes_dict[j]
                    
                    # Tighter M calculation
                    M = 1.5 * max(Lmax, Wmax, Hmax)
                    
                    for rid_i, rot_i in valid_rotations[i]:
                        for rid_j, rot_j in valid_rotations[j]:
                            # X-axis separation
                            model.addConstr(
                                x[i] + b_dims_i[rot_i[0]] <= x[j] + M * (1 - a[i, j]) + M * (2 - r[i, rid_i] - r[j, rid_j])
                            )
                            model.addConstr(
                                x[j] + b_dims_j[rot_j[0]] <= x[i] + M * (1 - b[i, j]) + M * (2 - r[i, rid_i] - r[j, rid_j])
                            )
                            # Y-axis separation
                            model.addConstr(
                                y[i] + b_dims_i[rot_i[1]] <= y[j] + M * (1 - c[i, j]) + M * (2 - r[i, rid_i] - r[j, rid_j])
                            )
                            model.addConstr(
                                y[j] + b_dims_j[rot_j[1]] <= y[i] + M * (1 - d[i, j]) + M * (2 - r[i, rid_i] - r[j, rid_j])
                            )
                            # Z-axis separation
                            model.addConstr(
                                z[i] + b_dims_i[rot_i[2]] <= z[j] + M * (1 - e[i, j]) + M * (2 - r[i, rid_i] - r[j, rid_j])
                            )
                            model.addConstr(
                                z[j] + b_dims_j[rot_j[2]] <= z[i] + M * (1 - f[i, j]) + M * (2 - r[i, rid_i] - r[j, rid_j])
                            )
                    
                    # At least one separation must be active
                    model.addConstr(
                        a[i, j] + b[i, j] + c[i, j] + d[i, j] + e[i, j] + f[i, j] >= p[i, k] + p[j, k] - 1
                    )

        # Optimize
        model.optimize()

        # Write results
        if model.Status == GRB.OPTIMAL or model.Status == GRB.TIME_LIMIT:
            with open(output_file, "w") as f_out:
                f_out.write(f"Vehicle 1. Dimensions ({v_dims[0]}, {v_dims[1]}, {v_dims[2]}).\n\n")

                packed_volume = 0
                packed_boxes = 0
                packed_weight = 0
                
                for i in box_ids_with_valid:
                    if p[i, k].X > 0.99:
                        rot_idx = max(range(len(rotations)), key=lambda rid: r[i, rid].X if rid in [v[0] for v in valid_rotations[i]] else -1)
                        rot = rotations[rot_idx]
                        b_dims = (boxes_dict[i][rot[0]], boxes_dict[i][rot[1]], boxes_dict[i][rot[2]])
                        pos_x, pos_y, pos_z = round(x[i].X, 2), round(y[i].X, 2), round(z[i].X, 2)
                        f_out.write(f"{i} \t {pos_x} \t {pos_y} \t {pos_z} \t {b_dims[0]:.2f}\t {b_dims[1]:.2f}\t {b_dims[2]:.2f}\t NA\n")
                        packed_volume += b_dims[0] * b_dims[1] * b_dims[2]
                        packed_boxes += 1
                        if boxes:
                            packed_weight += boxes[i - 1].weight

                mean_volume_used = (packed_volume / container_volume) if container_volume > 0 else 0
                fill_rate = mean_volume_used * 100

                f_out.write(f"\nVehicles used: 1\n")
                f_out.write(f"Boxes packed: {packed_boxes}/{len(box_ids_with_valid)}\n")
                f_out.write(f"Mean volume used per vehicle: {mean_volume_used:.4f}\n")
                f_out.write(f"Fill rate: {fill_rate:.2f}%\n")
                f_out.write(f"Total weight: {packed_weight:.2f}\n")
                f_out.write(f"Time to solve: {model.Runtime:.4f}s\n")
                f_out.write(f"MIPGap: {model.MIPGap:.4f}\n")
                f_out.write(f"Objective value: {model.ObjVal:.2f}\n")
                f_out.write(f"Enhanced Gurobi with constraints\n")
                
            print(f"Enhanced solution found with fill rate: {fill_rate:.2f}%")
            print(f"Constraints applied: {list(constraints.keys())}")
        else:
            print("No optimal solution found within time limit.")

    except gp.GurobiError as e:
        print(f"Gurobi error {e.errno}: {e}")
    except Exception as e:
        print(f"Error occurred: {e}")

def enhanced_greedy_clp_placement(boxes_dict: Dict, vehicles_dict: Dict, output_file: str,
                                 container: CLPContainer = None, 
                                 boxes: List[CLPBox] = None, 
                                 constraints: Dict = None,
                                 restarts: int = 5):
    """
    Enhanced greedy placement with flexible constraints
    """
    if not vehicles_dict:
        print("Data kontainer kosong.")
        return

    if constraints is None:
        constraints = {}

    k = 1
    v_dims = vehicles_dict[k]
    Lmax, Wmax, Hmax = v_dims[0], v_dims[1], v_dims[2]
    container_volume = Lmax * Wmax * Hmax
    
    box_ids = list(boxes_dict.keys())
    
    # Apply initial constraint-based sorting
    if boxes and constraints:
        initial_sort_keys = []
        
        # LIFO constraint
        if constraints.get('enforceLIFO', False):
            initial_sort_keys.append(lambda i: boxes[i - 1].destination_group)
        
        # Priority constraint
        if constraints.get('enforcePriority', False):
            initial_sort_keys.append(lambda i: boxes[i - 1].priority)
        
        if initial_sort_keys:
            box_ids.sort(key=lambda i: tuple(key(i) for key in initial_sort_keys))
    
    # Enhanced sorting with multiple criteria
    def enhanced_box_score(box_id):
        b_dims = boxes_dict[box_id]
        volume = b_dims[0] * b_dims[1] * b_dims[2]
        aspect_ratio = max(b_dims) / min(b_dims) if min(b_dims) > 0 else 1
        compactness = volume / (b_dims[0] + b_dims[1] + b_dims[2])
        
        base_score = (volume, -aspect_ratio, compactness)
        
        # Apply constraint bonuses
        if boxes and constraints:
            box_obj = boxes[box_id - 1]
            score_multiplier = 1.0
            
            if constraints.get('enforcePriority', False):
                score_multiplier *= (1 + (6 - box_obj.priority) * 0.1)
            
            if constraints.get('enforceLIFO', False):
                score_multiplier *= (1 + (100 - box_obj.destination_group) * 0.005)
            
            return (base_score[0] * score_multiplier, base_score[1], base_score[2])
        
        return base_score
    
    base_sorted_box_ids = sorted(box_ids, key=enhanced_box_score, reverse=True)

    import random

    def _compact_placed_boxes(placed_boxes, occupied, Lmax, Wmax, Hmax):
        """Compact placed boxes towards origin to reduce fragmentation."""
        def is_overlap(x1, y1, z1, l1, w1, h1, x2, y2, z2, l2, w2, h2):
            return not (
                x1 + l1 <= x2 or x2 + l2 <= x1 or
                y1 + w1 <= y2 or y2 + w2 <= y1 or
                z1 + h1 <= z2 or z2 + h2 <= z1
            )

        for pb in placed_boxes:
            moved = True
            while moved:
                moved = False
                # try x
                for nx in range(int(pb['x']) - 1, -1, -1):
                    coll = False
                    for ob in occupied:
                        if ob[0] == pb['x'] and ob[1] == pb['y'] and ob[2] == pb['z']:
                            continue
                        if is_overlap(nx, pb['y'], pb['z'], pb['dims'][0], pb['dims'][1], pb['dims'][2], ob[0], ob[1], ob[2], ob[3], ob[4], ob[5]):
                            coll = True
                            break
                    if coll:
                        break
                    pb['x'] = nx
                    moved = True
                # try y
                for ny in range(int(pb['y']) - 1, -1, -1):
                    coll = False
                    for ob in occupied:
                        if ob[0] == pb['x'] and ob[1] == pb['y'] and ob[2] == pb['z']:
                            continue
                        if is_overlap(pb['x'], ny, pb['z'], pb['dims'][0], pb['dims'][1], pb['dims'][2], ob[0], ob[1], ob[2], ob[3], ob[4], ob[5]):
                            coll = True
                            break
                    if coll:
                        break
                    pb['y'] = ny
                    moved = True
                # try z
                for nz in range(int(pb['z']) - 1, -1, -1):
                    coll = False
                    for ob in occupied:
                        if ob[0] == pb['x'] and ob[1] == pb['y'] and ob[2] == pb['z']:
                            continue
                        if is_overlap(pb['x'], pb['y'], nz, pb['dims'][0], pb['dims'][1], pb['dims'][2], ob[0], ob[1], ob[2], ob[3], ob[4], ob[5]):
                            coll = True
                            break
                    if coll:
                        break
                    pb['z'] = nz
                    moved = True
    
    best_solution = None
    best_fill = -1.0

    # perform multiple restarts to improve packing
    for attempt in range(max(1, restarts)):
        if attempt == 0:
            sorted_box_ids = base_sorted_box_ids.copy()
        else:
            sorted_box_ids = base_sorted_box_ids.copy()
            random.shuffle(sorted_box_ids)

        placed_boxes = []
        occupied = []
        total_weight = 0
        def is_overlap(x1, y1, z1, l1, w1, h1, x2, y2, z2, l2, w2, h2):
            return not (
                x1 + l1 <= x2 or x2 + l2 <= x1 or
                y1 + w1 <= y2 or y2 + w2 <= y1 or
                z1 + h1 <= z2 or z2 + h2 <= z1
            )

        def get_support_area(x, y, z, l, w, h):
            if z == 0:
                return l * w
            
            support_area = 0
            for ox, oy, oz, ol, ow, oh in occupied:
                if abs(oz + oh - z) < 0.01:
                    x_overlap = max(0, min(x + l, ox + ol) - max(x, ox))
                    y_overlap = max(0, min(y + w, oy + ow) - max(y, oy))
                    support_area += x_overlap * y_overlap
            return support_area

        def get_corner_distance(x, y, z):
            """Distance from bottom-left-back corner (prefer corner placement)"""
            return math.sqrt(x*x + y*y + z*z)

        def check_stacking_constraint(box_obj, x, y, z, l, w, h):
            """Check if stacking constraint is satisfied"""
            if not constraints.get('enforceStacking', False) or box_obj.max_stack_weight >= float('inf'):
                return True
            
            # Calculate weight of boxes that would be stacked on top
            weight_above = 0
            for pb in placed_boxes:
                # Check if pb is above current box
                if (pb['z'] > z + h and
                    not (pb['x'] + pb['dims'][0] <= x or x + l <= pb['x'] or
                         pb['y'] + pb['dims'][1] <= y or y + w <= pb['y'])):
                    weight_above += boxes[pb['id'] - 1].weight
            
            return weight_above <= box_obj.max_stack_weight

        def find_best_positions(b_dims, rot, box_obj, num_positions=10):
            """Find multiple good positions and return the best one"""
            l, w, h = b_dims[rot[0]], b_dims[rot[1]], b_dims[rot[2]]
            
            # Generate more candidate positions
            candidates = [(0, 0, 0)]
            
            # Grid-based positions for better coverage
            step_x = max(1, Lmax // 10)
            step_y = max(1, Wmax // 10)
            step_z = max(1, Hmax // 10)
            
            for x in range(0, int(Lmax - l + 1), int(step_x)):
                for y in range(0, int(Wmax - w + 1), int(step_y)):
                    for z in range(0, int(Hmax - h + 1), int(step_z)):
                        candidates.append((x, y, z))
            
            # Add positions based on existing boxes
            for pb in placed_boxes:
                candidates.extend([
                    (pb['x'] + pb['dims'][0], pb['y'], pb['z']),
                    (pb['x'], pb['y'] + pb['dims'][1], pb['z']),
                    (pb['x'], pb['y'], pb['z'] + pb['dims'][2]),
                    (pb['x'] + pb['dims'][0], pb['y'] + pb['dims'][1], pb['z']),
                    (pb['x'] + pb['dims'][0], pb['y'], pb['z'] + pb['dims'][2]),
                    (pb['x'], pb['y'] + pb['dims'][1], pb['z'] + pb['dims'][2])
                ])

            valid_candidates = []
            for x, y, z in candidates:
                if (x + l <= Lmax and y + w <= Wmax and z + h <= Hmax and
                    not any(is_overlap(x, y, z, l, w, h, *ob) for ob in occupied)):
                    
                    support = get_support_area(x, y, z, l, w, h)
                    corner_dist = get_corner_distance(x, y, z)
                    stability = support / (l * w) if l * w > 0 else 0
                    
                    score = (support, -corner_dist, -z, stability)
                    valid_candidates.append((x, y, z, score))
            
            if not valid_candidates:
                return None
                
            # Sort by score and return best position
            valid_candidates.sort(key=lambda x: x[3], reverse=True)
            return valid_candidates[0][:3]

        # Multi-pass placement with different strategies
        remaining_boxes = sorted_box_ids.copy()

        for pass_num in range(4):  # 4 passes for better fill rate
            print(f"Enhanced greedy pass {pass_num + 1}: {len(remaining_boxes)} boxes remaining")
            
            if pass_num == 1:
                # Sort by smallest dimension first
                remaining_boxes.sort(key=lambda i: min(boxes_dict[i][:3]))
            elif pass_num == 2:
                # Sort by aspect ratio (prefer cubic shapes)
                remaining_boxes.sort(key=lambda i: max(boxes_dict[i][:3])/min(boxes_dict[i][:3]))
            elif pass_num == 3:
                # Sort by volume density
                remaining_boxes.sort(key=lambda i: boxes_dict[i][0]*boxes_dict[i][1]*boxes_dict[i][2], reverse=True)
            
            boxes_to_remove = []
            
            for i in remaining_boxes:
                b_dims = boxes_dict[i]
                best_pos = None
                best_rot = None
                best_score = -1
                
                # Try all valid rotations
                valid_rots = get_valid_rotations(b_dims, Lmax, Wmax, Hmax)
                
                for rid, rot in valid_rots:
                    pos_result = find_best_positions(b_dims, rot, boxes[i - 1])
                    if pos_result:
                        x, y, z = pos_result
                        l, w, h = b_dims[rot[0]], b_dims[rot[1]], b_dims[rot[2]]
                        
                        support = get_support_area(x, y, z, l, w, h)
                        corner_dist = get_corner_distance(x, y, z)
                        stability = support / (l * w) if l * w > 0 else 0
                        
                        # Enhanced scoring function
                        score = (support * 2 - corner_dist * 0.1 - z * 0.5 + stability * 10)
                        
                        if score > best_score:
                            best_pos = (x, y, z)
                            best_rot = rot
                            best_score = score
                
                if best_pos:
                    x, y, z = best_pos
                    l, w, h = b_dims[best_rot[0]], b_dims[best_rot[1]], b_dims[best_rot[2]]
                    
                    placed_boxes.append({
                        'id': i, 'x': x, 'y': y, 'z': z, 
                        'rot': best_rot, 'dims': (l, w, h)
                    })
                    occupied.append((x, y, z, l, w, h))
                    boxes_to_remove.append(i)
            
            # Remove placed boxes
            for i in boxes_to_remove:
                remaining_boxes.remove(i)
                
            if not boxes_to_remove:
                break

            # after placing, apply compaction to improve density
            try:
                _compact_placed_boxes(placed_boxes, occupied, Lmax, Wmax, Hmax)
            except Exception:
                pass

            packed_volume = sum(pb['dims'][0] * pb['dims'][1] * pb['dims'][2] for pb in placed_boxes)
            mean_volume_used = (packed_volume / container_volume) if container_volume > 0 else 0
            fill_rate = mean_volume_used * 100

            if fill_rate > best_fill:
                best_fill = fill_rate
                best_solution = (placed_boxes.copy(), occupied.copy())

    # write best solution
    if best_solution is None:
        best_solution = ([], [])

    placed_boxes, occupied = best_solution

    with open(output_file, "w") as f_out:
        f_out.write(f"Vehicle 1. Dimensions ({v_dims[0]}, {v_dims[1]}, {v_dims[2]}).\n\n")

        packed_volume = 0
        for pb in placed_boxes:
            f_out.write(f"{pb['id']} \t {pb['x']:.2f} \t {pb['y']:.2f} \t {pb['z']:.2f} \t {pb['dims'][0]:.2f}\t {pb['dims'][1]:.2f}\t {pb['dims'][2]:.2f}\t NA\n")
            packed_volume += pb['dims'][0] * pb['dims'][1] * pb['dims'][2]

        mean_volume_used = (packed_volume / container_volume) if container_volume > 0 else 0
        fill_rate = mean_volume_used * 100

        f_out.write(f"\nVehicles used: 1\n")
        f_out.write(f"Boxes packed: {len(placed_boxes)}/{len(box_ids)}\n")
        f_out.write(f"Mean volume used per vehicle: {mean_volume_used:.4f}\n")
        f_out.write(f"Fill rate: {fill_rate:.2f}%\n")
        f_out.write(f"Enhanced greedy placement mode - best of {restarts} restarts\n")

    print(f"Enhanced greedy solution with fill rate: {fill_rate:.2f}%")
    print(f"Boxes packed: {len(placed_boxes)}/{len(box_ids)}")