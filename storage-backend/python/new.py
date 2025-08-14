import gurobipy as gp
from gurobipy import GRB
import datetime
import math

def read_timed_thpack(filename):
    """
    Membaca file instans dengan format thpack.
    Baris pertama: dimensi kontainer.
    Baris berikutnya: dimensi boks dan waktu tiba.
    Mendukung angka desimal.
    """
    boxes = {}
    vehicles = {}
    try:
        with open(filename, "r") as f:
            # Baca dimensi kontainer (baris pertama)
            line = f.readline()
            dims = list(map(float, line.strip().split()))
            vehicles[1] = tuple(dims)  # Hanya mendukung satu kontainer

            # Baca dimensi boks (baris berikutnya)
            box_id = 1
            for line in f:
                if line.strip():
                    parts = list(map(float, line.strip().split()))
                    # Format: (panjang, lebar, tinggi, waktu_tiba)
                    boxes[box_id] = tuple(parts)
                    box_id += 1
    except FileNotFoundError:
        print(f"Error! File tidak ditemukan di {filename}")
        return None, None
    except Exception as e:
        print(f"Error saat membaca file: {e}")
        return None, None

    return boxes, vehicles


# Definisi rotasi lengkap untuk fill rate yang lebih tinggi
rotations = [
    (0, 1, 2),  # Original
    (0, 2, 1),  # Rotate around x-axis
    (1, 0, 2),  # Rotate around z-axis
    (1, 2, 0),  # Rotate around y-axis
    (2, 0, 1),  # Rotate around x-axis
    (2, 1, 0)   # Rotate around z-axis
]

def get_valid_rotations(b_dims, Lmax, Wmax, Hmax):
    """Mendapatkan rotasi valid dengan lebih banyak opsi"""
    valid = []
    for rid, rot in enumerate(rotations):
        if b_dims[rot[0]] <= Lmax and b_dims[rot[1]] <= Wmax and b_dims[rot[2]] <= Hmax:
            valid.append((rid, rot))
    return valid


def calculate_box_priority(box_id, boxes, container_volume):
    """Hitung prioritas box berdasarkan volume dan aspect ratio"""
    b_dims = boxes[box_id]
    volume = b_dims[0] * b_dims[1] * b_dims[2]
    volume_ratio = volume / container_volume
    
    # Prioritaskan box dengan volume besar dan aspect ratio yang baik
    aspect_penalty = max(b_dims) / min(b_dims) if min(b_dims) > 0 else 1
    priority = volume_ratio / aspect_penalty
    
    return priority


def solve_clp_with_boxes(boxes, vehicles, output_file, time_limit):
    """
    Membuat dan menyelesaikan model optimisasi untuk Container Loading Problem.
    """
    if not vehicles:
        print("Data kontainer kosong.")
        return

    # Asumsi hanya ada satu kontainer
    k = 1
    v_dims = vehicles[k]
    Lmax, Wmax, Hmax = v_dims[0], v_dims[1], v_dims[2]
    container_volume = Lmax * Wmax * Hmax

    box_ids = list(boxes.keys())
    
    # Sortir box berdasarkan prioritas untuk fill rate yang lebih baik
    box_priorities = [(i, calculate_box_priority(i, boxes, container_volume)) for i in box_ids]
    box_priorities.sort(key=lambda x: x[1], reverse=True)
    sorted_box_ids = [x[0] for x in box_priorities]
    
    valid_rotations = {i: get_valid_rotations(boxes[i], Lmax, Wmax, Hmax) for i in sorted_box_ids}
    
    # Filter box_ids yang punya rotasi valid saja
    box_ids_with_valid = [i for i in sorted_box_ids if len(valid_rotations[i]) > 0]
    
    for i in box_ids:
        print(f"Box {i}: {len(valid_rotations[i])} valid rotation(s)")
        if len(valid_rotations[i]) == 0:
            print(f"  WARNING: Box {i} does not fit in the container in any rotation! Box will be ignored in optimization.")

    # --- Hybrid: fallback ke greedy jika box terlalu banyak ---
    greedy_threshold = 25  # Turunkan threshold untuk lebih sering menggunakan optimisasi
    if len(box_ids_with_valid) > greedy_threshold:
        print(f"INFO: Jumlah box {len(box_ids_with_valid)} > {greedy_threshold}. Menggunakan mode greedy placement agar efisien.")
        greedy_clp_placement(boxes, vehicles, output_file)
        return

    try:
        # --- Membuat Model Gurobi ---
        model = gp.Model("CLP_Python")
        
        # Parameter Gurobi yang lebih optimal untuk fill rate tinggi
        model.setParam("MIPFocus", 1)  # Focus on finding good feasible solutions
        model.setParam("Heuristics", 0.8)  # Increase heuristics
        model.setParam("Presolve", 2)
        model.setParam("Cuts", 2)  # Aggressive cuts
        model.setParam("MIPGap", 0.01)  # Allow 1% gap for faster solving
        model.setParam("TimeLimit", time_limit)
        model.setParam("Threads", 4)  # Use multiple threads

        # --- Variabel ---
        # p[i,k] = 1 jika boks i masuk ke kontainer k
        p = model.addVars(box_ids_with_valid, [k], vtype=GRB.BINARY, name="p")

        # x[i], y[i], z[i] = koordinat pojok kiri bawah boks i
        x = model.addVars(box_ids_with_valid, lb=0, ub=Lmax, name="x")
        y = model.addVars(box_ids_with_valid, lb=0, ub=Wmax, name="y")
        z = model.addVars(box_ids_with_valid, lb=0, ub=Hmax, name="z")

        # r[i,rot] = 1 jika boks i menggunakan rotasi rot
        r = model.addVars(box_ids_with_valid, range(len(rotations)), vtype=GRB.BINARY, name="r")

        # Variabel untuk non-overlapping constraints
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

        # --- Fungsi Tujuan: Maksimalkan Volume yang Terisi dengan Weighted Priority ---
        total_volume = gp.quicksum(
            p[i, k] * boxes[i][0] * boxes[i][1] * boxes[i][2] * (1 + 0.1 * calculate_box_priority(i, boxes, container_volume))
            for i in box_ids_with_valid
        )
        model.setObjective(total_volume, GRB.MAXIMIZE)

        # --- Batasan (Constraints) ---
        # Boundary constraints with rotation
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

        # --- Optimisasi ---
        model.optimize()

        # --- Tulis Hasil ke File ---
        if model.Status == GRB.OPTIMAL or model.Status == GRB.TIME_LIMIT:
            with open(output_file, "w") as f_out:
                f_out.write(
                    f"Vehicle 1. Dimensions ({v_dims[0]}, {v_dims[1]}, {v_dims[2]}).\n\n"
                )

                packed_volume = 0
                packed_boxes = 0
                for i in box_ids_with_valid:
                    # Periksa apakah boks i masuk ke dalam kontainer
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
                fill_rate = mean_volume_used * 100  # dalam persen

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

def greedy_clp_placement(boxes, vehicles, output_file):
    """
    Penempatan box secara greedy yang lebih cerdas dengan multiple passes
    untuk meningkatkan fill rate hingga 85%+
    """
    if not vehicles:
        print("Data kontainer kosong.")
        return

    k = 1
    v_dims = vehicles[k]
    Lmax, Wmax, Hmax = v_dims[0], v_dims[1], v_dims[2]
    container_volume = Lmax * Wmax * Hmax
    
    box_ids = list(boxes.keys())
    
    # Sortir box berdasarkan volume (descending) untuk better packing
    box_volumes = [(i, boxes[i][0] * boxes[i][1] * boxes[i][2]) for i in box_ids]
    box_volumes.sort(key=lambda x: x[1], reverse=True)
    sorted_box_ids = [x[0] for x in box_volumes]
    
    placed_boxes = []  # List of dict: {id, x, y, z, rot, dims}
    occupied = []  # List of (x, y, z, l, w, h)

    def is_overlap(x1, y1, z1, l1, w1, h1, x2, y2, z2, l2, w2, h2):
        return not (
            x1 + l1 <= x2 or x2 + l2 <= x1 or
            y1 + w1 <= y2 or y2 + w2 <= y1 or
            z1 + h1 <= z2 or z2 + h2 <= z1
        )

    def get_support_area(x, y, z, l, w, h):
        """Hitung area dukungan untuk box pada posisi tertentu"""
        support_area = 0
        if z == 0:  # Bottom of container
            support_area = l * w
        else:
            for ob in occupied:
                ox, oy, oz, ol, ow, oh = ob
                if abs(oz + oh - z) < 0.01:  # Same level
                    # Calculate intersection area
                    x_overlap = max(0, min(x + l, ox + ol) - max(x, ox))
                    y_overlap = max(0, min(y + w, oy + ow) - max(y, oy))
                    support_area += x_overlap * y_overlap
        return support_area

    def find_best_position(b_dims, rot):
        """Cari posisi terbaik untuk box dengan rotasi tertentu"""
        l, w, h = b_dims[rot[0]], b_dims[rot[1]], b_dims[rot[2]]
        
        # Generate candidate positions
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
            return (-support, z, y, x)  # Negative support for descending order
        
        valid_candidates.sort(key=position_score)
        return valid_candidates[0]

    # Multiple passes untuk meningkatkan fill rate
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

    # Output
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
        f_out.write(f"Greedy placement mode (enhanced)\n")
        
    print(f"Enhanced greedy solution written to {output_file}")
    print(f"Fill rate: {fill_rate:.2f}%")
    print(f"Boxes packed: {len(placed_boxes)}/{len(box_ids)}")

if __name__ == "__main__":
    # --- Konfigurasi ---
    input_file = "../datasets/10ft.txt"
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"solusi_20ft_python_{timestamp}.txt"
    time_limit = 600  # Batas waktu optimisasi dalam detik (10 menit)

    print(f"Membaca file instans: {input_file}")
    boxes, vehicles = read_timed_thpack(input_file)

    if boxes and vehicles:
        print(f"Berhasil membaca {len(boxes)} boks dan {len(vehicles)} kontainer.")
        print(f"Memulai optimisasi dengan batas waktu {time_limit} detik...")
        solve_clp_with_boxes(boxes, vehicles, output_file, time_limit)
        print("Proses selesai.")