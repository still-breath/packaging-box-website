# clptac_service.py
from typing import List, Dict
from clptac import CLPContainer, CLPBox, solve_clp_with_gurobi, solve_clp_with_greedy

def run_clp_packing(container_data: Dict, items_data: List[Dict], groups_data: List[Dict], constraints: Dict) -> Dict:

    try:
        container = CLPContainer(
            length=container_data['length'],
            width=container_data['width'],
            height=container_data['height'],
            max_weight=container_data['maxWeight']
        )

        boxes = []
        box_map = {}
        current_box_id = 0
        for item in items_data:
            for _ in range(item.get('quantity', 1)):
                current_box_id += 1
                rotations = item.get('allowed_rotations')
                new_box = CLPBox(
                    id=current_box_id,
                    dims=(item['length'], item['width'], item['height']),
                    weight=item['weight'],
                    allowed_rotations=rotations if rotations is not None else list(range(6)),
                    max_stack_weight=item.get('max_stack_weight', float('inf')),
                    priority=item.get('priority', 5),
                    destination_group=item.get('destination_group', 99)
                )
                boxes.append(new_box)
                box_map[current_box_id] = {"group": item['group']}

        # LOGIKA HYBRID: Pilih algoritma berdasarkan jumlah boks
        greedy_threshold = 20
        solution = solve_clp_with_gurobi(container, boxes, constraints, time_limit=600)
        
        # if len(boxes) > greedy_threshold:
        #     print(f"INFO: Jumlah box ({len(boxes)}) > {greedy_threshold}. Menggunakan mode GREEDY.")
        #     solution = solve_clp_with_greedy(container, boxes, constraints)
        # else:
        #     print(f"INFO: Jumlah box ({len(boxes)}) <= {greedy_threshold}. Menggunakan mode GUROBI.")
        #     solution = solve_clp_with_gurobi(container, boxes, constraints, time_limit=30)
        
        if not solution or "error" in solution:
            return solution or {"error": "Algoritma tidak mengembalikan solusi."}

        # Adaptasi hasil
        group_color_map = {group['name']: group['color'] for group in groups_data}
        placed_items, total_weight, total_volume = [], 0, 0
        
        for packed_box in solution.get("packed", []):
            box_info = box_map.get(packed_box.id, {})
            group_name = box_info.get("group", "Unknown")
            final_dims = packed_box.final_dims
            
            placed_items.append({
                "id": f"{group_name}_{packed_box.id}",
                "x": packed_box.x, "y": packed_box.y, "z": packed_box.z,
                "length": final_dims[0], "width": final_dims[1], "height": final_dims[2],
                "weight": packed_box.weight,
                "color": group_color_map.get(group_name, "#cccccc")
            })
            total_weight += packed_box.weight
            total_volume += final_dims[0] * final_dims[1] * final_dims[2]

        unplaced_items = []
        for box in solution.get("unpacked", []):
            box_info = box_map.get(box.id, {})
            group_name = box_info.get("group", "Unknown")
            unplaced_items.append({
                "id": f"{group_name}_{box.id}",
                "length": box.dims[0], "width": box.dims[1], "height": box.dims[2],
                "weight": box.weight, "group": group_name
            })

        fill_rate = (total_volume / container.volume * 100) if container.volume > 0 else 0
        
        return {
            "fillRate": fill_rate, "totalWeight": total_weight,
            "placedItems": placed_items, "unplacedItems": unplaced_items
        }

    except Exception as e:
        print(f"Error dalam CLP service: {e}")
        return {"error": str(e)}
