from typing import List, Dict
from blf import Box, Container, ContainerPackingOptimizer  # ✅ Tambahkan import Box dan Container

def run_blf_packing(container_data: Dict, items_data: List[Dict], groups_data: List[Dict], constraints: Dict) -> Dict:
    """
    Membungkus algoritma BLF dengan penanganan nilai None yang lebih baik.
    """
    try:
        container = Container(
            name="blf_container",
            length=container_data['length'],
            width=container_data['width'],
            height=container_data['height'],
            max_weight=container_data['maxWeight']
        )

        boxes = []
        for item in items_data:
            for i in range(item.get('quantity', 1)):
                boxes.append(
                    Box(
                        name=f"{item['group']}_{i+1}",
                        length=item['length'],
                        width=item['width'],
                        height=item['height'],
                        weight=item['weight'],
                        quantity=1,
                        allowed_rotations=item.get('allowed_rotations'),
                        max_stack_weight=item.get('max_stack_weight'),
                        priority=item.get('priority'),
                        destination_group=item.get('destination_group')
                    )
                )

        optimizer = ContainerPackingOptimizer()
        packed, unpacked = optimizer.bottom_left_fill_algorithm(container, boxes, constraints)
        
        group_color_map = {group['name']: group['color'] for group in groups_data}
        
        placed_items = []
        for box in packed:
            group_name = box.name.rsplit('_', 1)[0]
            placed_items.append({
                "id": box.name,
                "x": box.x, "y": box.y, "z": box.z,
                "length": box.length, "width": box.width, "height": box.height,
                "weight": box.weight,
                "color": group_color_map.get(group_name, "#cccccc")
            })

        unplaced_items = []
        for box in unpacked:
            unplaced_items.append({
                "id": box.name,
                "length": box.original_dims[0],
                "width": box.original_dims[1],
                "height": box.original_dims[2],
                "weight": box.weight,
                "group": box.name.rsplit('_', 1)[0]
            })

        return {
            "fillRate": container.get_fill_rate(),
            "totalWeight": container.total_weight,
            "placedItems": placed_items,
            "unplacedItems": unplaced_items
        }
    except Exception as e:
        print(f"Error dalam BLF service: {e}")
        return {"error": str(e)}