import gurobipy as gp
from gurobipy import GRB
import datetime
import math
import random

def read_timed_thpack(filename):
    boxes = {}
    vehicles = {}
    try:
        with open(filename, "r") as f:
            line = f.readline()
            dims = list(map(float, line.strip().split()))
            vehicles[1] = tuple(dims)             
            box_id = 1
            for line in f:
                if line.strip():
                    parts = list(map(float, line.strip().split()))                    
                    boxes[box_id] = tuple(parts)
                    box_id += 1
    except FileNotFoundError:
        print(f"Error! File tidak ditemukan di {filename}")
        return None, None
    except Exception as e:
        print(f"Error saat membaca file: {e}")
        return None, None

    return boxes, vehicles


rotations = [
    (0, 1, 2),
    (0, 2, 1),
    (1, 0, 2),
    (1, 2, 0),
    (2, 0, 1),
    (2, 1, 0)
]

def get_valid_rotations(b_dims, Lmax, Wmax, Hmax):   
    valid = []
    for rid, rot in enumerate(rotations):
        if b_dims[rot[0]] <= Lmax and b_dims[rot[1]] <= Wmax and b_dims[rot[2]] <= Hmax:
            valid.append((rid, rot))
    return valid


def calculate_box_priority(box_id, boxes, container_volume):
    b_dims = boxes[box_id]
    volume = b_dims[0] * b_dims[1] * b_dims[2]
    volume_ratio = volume / container_volume
        
    aspect_penalty = max(b_dims) / min(b_dims) if min(b_dims) > 0 else 1
    priority = volume_ratio / aspect_penalty
    
    return priority


def solve_clp_with_boxes(boxes, vehicles, output_file, time_limit):
    if not vehicles:
        print("Data kontainer kosong.")
        return
    
    k = 1
    v_dims = vehicles[k]
    Lmax, Wmax, Hmax = v_dims[0], v_dims[1], v_dims[2]
    container_volume = Lmax * Wmax * Hmax

    box_ids = list(boxes.keys())
        
    box_priorities = [(i, calculate_box_priority(i, boxes, container_volume)) for i in box_ids]
    box_priorities.sort(key=lambda x: x[1], reverse=True)
    sorted_box_ids = [x[0] for x in box_priorities]
    
    valid_rotations = {i: get_valid_rotations(boxes[i], Lmax, Wmax, Hmax) for i in sorted_box_ids}
        
    box_ids_with_valid = [i for i in sorted_box_ids if len(valid_rotations[i]) > 0]
    
    for i in box_ids:
        print(f"Box {i}: {len(valid_rotations[i])} valid rotation(s)")
        if len(valid_rotations[i]) == 0:
            print(f"  WARNING: Box {i} does not fit in the container in any rotation! Box will be ignored in optimization.")
    
    greedy_threshold = 25
    if len(box_ids_with_valid) > greedy_threshold:
        print(f"INFO: Jumlah box {len(box_ids_with_valid)} > {greedy_threshold}. Menggunakan mode greedy placement agar efisien.")
        greedy_clp_placement(boxes, vehicles, output_file)
        return

    try:        
        model = gp.Model("CLP_Python")
                
        model.setParam("MIPFocus", 1)
        model.setParam("Heuristics", 0.8)
        model.setParam("Presolve", 2)
        model.setParam("Cuts", 2)
        model.setParam("MIPGap", 0.01)
        model.setParam("TimeLimit", time_limit)
        model.setParam("Threads", 4)
        
        p = model.addVars(box_ids_with_valid, [k], vtype=GRB.BINARY, name="p")

        x = model.addVars(box_ids_with_valid, lb=0, ub=Lmax, name="x")
        y = model.addVars(box_ids_with_valid, lb=0, ub=Wmax, name="y")
        z = model.addVars(box_ids_with_valid, lb=0, ub=Hmax, name="z")

        r = model.addVars(box_ids_with_valid, range(len(rotations)), vtype=GRB.BINARY, name="r")

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


        total_volume = gp.quicksum(
            p[i, k] * boxes[i][0] * boxes[i][1] * boxes[i][2] * (1 + 0.1 * calculate_box_priority(i, boxes, container_volume))
            for i in box_ids_with_valid
        )
        model.setObjective(total_volume, GRB.MAXIMIZE)

        for i in box_ids_with_valid:
            b_dims = boxes[i]
            for rid, rot in valid_rotations[i]:
                # Tighter bounds
                model.addConstr(x[i] + b_dims[rot[0]] <= Lmax + Lmax * (1 - r[i, rid]))
                model.addConstr(y[i] + b_dims[rot[1]] <= Wmax + Wmax * (1 - r[i, rid]))
                model.addConstr(z[i] + b_dims[rot[2]] <= Hmax + Hmax * (1 - r[i, rid]))

        # Rotation constraints
        for i in box_ids_with_valid:
            model.addConstr(gp.quicksum(r[i, rid] for rid, _ in valid_rotations[i]) == p[i, k])
            for rid in range(len(rotations)):
                if rid not in [v[0] for v in valid_rotations[i]]:
                    model.addConstr(r[i, rid] == 0)

        # Non-overlapping constraints dengan optimasi memory
        for i in box_ids_with_valid:
            for j in box_ids_with_valid:
                if i < j:
                    b_dims_i = boxes[i]
                    b_dims_j = boxes[j]
                    
                    # Reduced M value for tighter constraints
                    M = min(2 * max(Lmax, Wmax, Hmax), 
                           max(max(b_dims_i), max(b_dims_j)) + max(Lmax, Wmax, Hmax))
                    
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
    
        model.optimize()

        if model.Status == GRB.OPTIMAL or model.Status == GRB.TIME_LIMIT:
            with open(output_file, "w") as f_out:
                f_out.write(
                    f"Vehicle 1. Dimensions ({v_dims[0]}, {v_dims[1]}, {v_dims[2]}).\n\n"
                )

                packed_volume = 0
                packed_boxes = 0
                for i in box_ids_with_valid:
                    if p[i, k].X > 0.99:
                        rot_idx = max(range(len(rotations)), key=lambda rid: r[i, rid].X if rid in [v[0] for v in valid_rotations[i]] else -1)
                        rot = rotations[rot_idx]
                        b_dims = (boxes[i][rot[0]], boxes[i][rot[1]], boxes[i][rot[2]])
                        pos_x, pos_y, pos_z = (
                            round(x[i].X, 2),
                            round(y[i].X, 2),
                            round(z[i].X, 2),
                        )
                        f_out.write(
                            f"{i} \t {pos_x} \t {pos_y} \t {pos_z} \t {b_dims[0]:.2f}\t {b_dims[1]:.2f}\t {b_dims[2]:.2f}\t NA\n"
                        )
                        packed_volume += b_dims[0] * b_dims[1] * b_dims[2]
                        packed_boxes += 1

                mean_volume_used = (
                    (packed_volume / container_volume) if container_volume > 0 else 0
                )
                fill_rate = mean_volume_used * 100

                f_out.write(f"\nVehicles used: 1\n")
                f_out.write(f"Boxes packed: {packed_boxes}/{len(box_ids_with_valid)}\n")
                f_out.write(f"Mean volume used per vehicle: {mean_volume_used:.4f}\n")
                f_out.write(f"Fill rate: {fill_rate:.2f}%\n")
                f_out.write(f"Time to solve: {model.Runtime:.4f}s\n")
                f_out.write(f"MIPGap: {model.MIPGap:.4f}\n")
                f_out.write(f"Objective value: {model.ObjVal:.2f}\n")
                
            print(f"Solusi ditemukan dan ditulis ke {output_file}")
            print(f"Fill rate: {fill_rate:.2f}%")
        else:
            print("Tidak ada solusi optimal yang ditemukan dalam batas waktu.")

    except gp.GurobiError as e:
        print(f"Error Gurobi code {e.errno}: {e}")
    except Exception as e:
        print(f"Terjadi error: {e}")

def _compact_placed_boxes(placed_boxes, occupied, Lmax, Wmax, Hmax):
    """Attempt to compact placed boxes towards origin (0,0,0) without overlap.
    Modifies placed_boxes and occupied in place."""
    # Helper to check overlap
    def is_overlap(x1, y1, z1, l1, w1, h1, x2, y2, z2, l2, w2, h2):
        return not (
            x1 + l1 <= x2 or x2 + l2 <= x1 or
            y1 + w1 <= y2 or y2 + w2 <= y1 or
            z1 + h1 <= z2 or z2 + h2 <= z1
        )

    # Try for each box to move it towards origin along x, then y, then z
    for pb in placed_boxes:
        changed = True
        while changed:
            changed = False
            # try move left (decrease x)
            best_x = pb['x']
            for nx in range(int(pb['x']) - 1, -1, -1):
                collision = False
                for ob in occupied:
                    if ob is pb:
                        continue
                # check overlaps with existing occupied boxes
                for ob in occupied:
                    if ob is pb:
                        continue
                    if is_overlap(nx, pb['y'], pb['z'], pb['dims'][0], pb['dims'][1], pb['dims'][2], ob[0], ob[1], ob[2], ob[3], ob[4], ob[5]):
                        collision = True
                        break
                if collision:
                    break
                best_x = nx
            if best_x < pb['x']:
                # update occupied and pb
                for idx, ob in enumerate(occupied):
                    if ob[0] == pb['x'] and ob[1] == pb['y'] and ob[2] == pb['z'] and ob[3] == pb['dims'][0] and ob[4] == pb['dims'][1] and ob[5] == pb['dims'][2]:
                        occupied[idx] = (best_x, ob[1], ob[2], ob[3], ob[4], ob[5])
                        break
                pb['x'] = best_x
                changed = True

            # try move front (decrease y)
            best_y = pb['y']
            for ny in range(int(pb['y']) - 1, -1, -1):
                collision = False
                for ob in occupied:
                    if ob is pb:
                        continue
                    if is_overlap(pb['x'], ny, pb['z'], pb['dims'][0], pb['dims'][1], pb['dims'][2], ob[0], ob[1], ob[2], ob[3], ob[4], ob[5]):
                        collision = True
                        break
                if collision:
                    break
                best_y = ny
            if best_y < pb['y']:
                for idx, ob in enumerate(occupied):
                    if ob[0] == pb['x'] and ob[1] == pb['y'] and ob[2] == pb['z'] and ob[3] == pb['dims'][0] and ob[4] == pb['dims'][1] and ob[5] == pb['dims'][2]:
                        occupied[idx] = (ob[0], best_y, ob[2], ob[3], ob[4], ob[5])
                        break
                pb['y'] = best_y
                changed = True

            # try move down (decrease z)
            best_z = pb['z']
            for nz in range(int(pb['z']) - 1, -1, -1):
                collision = False
                for ob in occupied:
                    if ob is pb:
                        continue
                    if is_overlap(pb['x'], pb['y'], nz, pb['dims'][0], pb['dims'][1], pb['dims'][2], ob[0], ob[1], ob[2], ob[3], ob[4], ob[5]):
                        collision = True
                        break
                if collision:
                    break
                best_z = nz
            if best_z < pb['z']:
                for idx, ob in enumerate(occupied):
                    if ob[0] == pb['x'] and ob[1] == pb['y'] and ob[2] == pb['z'] and ob[3] == pb['dims'][0] and ob[4] == pb['dims'][1] and ob[5] == pb['dims'][2]:
                        occupied[idx] = (ob[0], ob[1], best_z, ob[3], ob[4], ob[5])
                        break
                pb['z'] = best_z
                changed = True


def greedy_clp_placement(boxes, vehicles, output_file, restarts: int = 5):
    if not vehicles:
        print("Data kontainer kosong.")
        return

    k = 1
    v_dims = vehicles[k]
    Lmax, Wmax, Hmax = v_dims[0], v_dims[1], v_dims[2]
    container_volume = Lmax * Wmax * Hmax
    
    box_ids = list(boxes.keys())

    box_volumes = [(i, boxes[i][0] * boxes[i][1] * boxes[i][2]) for i in box_ids]
    box_volumes.sort(key=lambda x: x[1], reverse=True)
    base_sorted_box_ids = [x[0] for x in box_volumes]

    best_solution = None
    best_fill = -1.0

    for attempt in range(max(1, restarts)):
        # Slight randomization between restarts to explore different packings
        sorted_box_ids = base_sorted_box_ids.copy()
        if attempt > 0:
            # perform a small shuffle to break ties / explore alternatives
            random.shuffle(sorted_box_ids)

        placed_boxes = []
        occupied = []

    def is_overlap(x1, y1, z1, l1, w1, h1, x2, y2, z2, l2, w2, h2):
        return not (
            x1 + l1 <= x2 or x2 + l2 <= x1 or
            y1 + w1 <= y2 or y2 + w2 <= y1 or
            z1 + h1 <= z2 or z2 + h2 <= z1
        )

    def get_support_area(x, y, z, l, w, h):        
        support_area = 0
        if z == 0:
            support_area = l * w
        else:
            for ob in occupied:
                ox, oy, oz, ol, ow, oh = ob
                if abs(oz + oh - z) < 0.01:                    
                    x_overlap = max(0, min(x + l, ox + ol) - max(x, ox))
                    y_overlap = max(0, min(y + w, oy + ow) - max(y, oy))
                    support_area += x_overlap * y_overlap
        return support_area

    def find_best_position(b_dims, rot):
        """Cari posisi terbaik untuk box dengan rotasi tertentu"""
        l, w, h = b_dims[rot[0]], b_dims[rot[1]], b_dims[rot[2]]
                
        candidates = [(0, 0, 0)]  # Bottom-left-back corner
        
        # Add positions based on existing boxes
        for pb in placed_boxes:
            # Right side
            candidates.append((pb['x'] + pb['dims'][0], pb['y'], pb['z']))
            # Front side
            candidates.append((pb['x'], pb['y'] + pb['dims'][1], pb['z']))
            # Top side
            candidates.append((pb['x'], pb['y'], pb['z'] + pb['dims'][2]))
            # Corners
            candidates.append((pb['x'] + pb['dims'][0], pb['y'] + pb['dims'][1], pb['z']))
            candidates.append((pb['x'] + pb['dims'][0], pb['y'], pb['z'] + pb['dims'][2]))
            candidates.append((pb['x'], pb['y'] + pb['dims'][1], pb['z'] + pb['dims'][2]))
        
        # Remove duplicates and invalid positions
        valid_candidates = []
        for pos in candidates:
            x, y, z = pos
            if (x + l <= Lmax and y + w <= Wmax and z + h <= Hmax and
                not any(is_overlap(x, y, z, l, w, h, *ob) for ob in occupied)):
                valid_candidates.append(pos)
        
        if not valid_candidates:
            return None
            
        # Sort by priority: lower z, higher support area, lower y, lower x
        def position_score(pos):
            x, y, z = pos
            support = get_support_area(x, y, z, l, w, h)
            return (-support, z, y, x)
        
        valid_candidates.sort(key=position_score)
        return valid_candidates[0]

        # Multiple passes for using fill rate
        remaining_boxes = sorted_box_ids.copy()
    
    for pass_num in range(3):  # 3 passes
        print(f"Greedy pass {pass_num + 1}: {len(remaining_boxes)} boxes remaining")
        
        if pass_num == 1:
            # Second pass: sort by different criteria
            remaining_boxes.sort(key=lambda i: min(boxes[i][:3]))  # Sort by smallest dimension
        elif pass_num == 2:
            # Third pass: sort by aspect ratio
            remaining_boxes.sort(key=lambda i: max(boxes[i][:3])/min(boxes[i][:3]))
        
        boxes_to_remove = []
        
        for i in remaining_boxes:
            b_dims = boxes[i]
            best_pos = None
            best_rot = None
            best_support = -1
            
            # Try all rotations
            for rid, rot in enumerate(rotations):
                if b_dims[rot[0]] <= Lmax and b_dims[rot[1]] <= Wmax and b_dims[rot[2]] <= Hmax:
                    pos = find_best_position(b_dims, rot)
                    if pos:
                        support = get_support_area(pos[0], pos[1], pos[2], 
                                                 b_dims[rot[0]], b_dims[rot[1]], b_dims[rot[2]])
                        if support > best_support:
                            best_pos = pos
                            best_rot = rot
                            best_support = support
            
            if best_pos:
                x, y, z = best_pos
                l, w, h = b_dims[best_rot[0]], b_dims[best_rot[1]], b_dims[best_rot[2]]
                
                placed_boxes.append({
                    'id': i, 'x': x, 'y': y, 'z': z, 
                    'rot': best_rot, 'dims': (l, w, h)
                })
                occupied.append((x, y, z, l, w, h))
                boxes_to_remove.append(i)
        
        # Remove placed boxes from remaining list
        for i in boxes_to_remove:
            remaining_boxes.remove(i)
            
        if not boxes_to_remove:
            break  # No more boxes can be placed

        # After a run, apply compaction to tighten packing
        try:
            _compact_placed_boxes(placed_boxes, occupied, Lmax, Wmax, Hmax)
        except Exception:
            pass

        # Evaluate fill
        packed_volume = sum(pb['dims'][0] * pb['dims'][1] * pb['dims'][2] for pb in placed_boxes)
        mean_volume_used = (packed_volume / container_volume) if container_volume > 0 else 0
        fill_rate = mean_volume_used * 100

        if fill_rate > best_fill:
            best_fill = fill_rate
            best_solution = (placed_boxes.copy(), occupied.copy())

    # Write best solution to file
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
        f_out.write(f"Greedy placement mode (enhanced) - best of {restarts} restarts\n")

    print(f"Enhanced greedy best solution written to {output_file}")
    print(f"Fill rate: {fill_rate:.2f}%")
    print(f"Boxes packed: {len(placed_boxes)}/{len(box_ids)}")

if __name__ == "__main__":
    input_file = "../datasets/10ft.txt"
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"solusi_20ft_python_{timestamp}.txt"
    time_limit = 600

    print(f"Membaca file instans: {input_file}")
    boxes, vehicles = read_timed_thpack(input_file)

    if boxes and vehicles:
        print(f"Berhasil membaca {len(boxes)} boks dan {len(vehicles)} kontainer.")
        print(f"Memulai optimisasi dengan batas waktu {time_limit} detik...")
        solve_clp_with_boxes(boxes, vehicles, output_file, time_limit)
        print("Proses selesai.")