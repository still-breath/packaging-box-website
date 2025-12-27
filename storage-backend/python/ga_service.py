# ga_service.py
from typing import List, Dict

from ga_logic import Box as AlgoBox, Container as AlgoContainer, GeneticAlgorithm, format_results_for_frontend

def run_ga_packing(container_data: Dict, items_data: List[Dict], groups_data: List[Dict], constraints: Dict, on_log=None, stop_event=None) -> Dict:
    """
    Membungkus algoritma GA dengan penanganan nilai None yang lebih baik.
    """
    try:
        # Validate: do not allow priority values when EnforcePriority is off
        has_priority = any(('priority' in item and item.get('priority') is not None) for item in items_data)
        if has_priority and not constraints.get('enforcePriority', False):
            return {"error": "Priority diberikan pada beberapa kotak tetapi 'enforcePriority' belum diaktifkan. Aktifkan 'enforcePriority' sebelum menggunakan priority."}

        # Validate: do not allow stacking-related fields when EnforceStacking is off
        has_stacking = any(('max_stack_weight' in item and item.get('max_stack_weight') is not None) for item in items_data)
        if has_stacking and not constraints.get('enforceStacking', False):
            return {"error": "Field stacking (max_stack_weight) diberikan tetapi 'Enforce Stacking' belum diaktifkan. Aktifkan 'Enforce Stacking' sebelum menggunakan nilai stacking."}

        # Validate: do not allow destination_group when EnforceLIFO is off
        has_lifo = any(('destination_group' in item and item.get('destination_group') is not None) for item in items_data)
        if has_lifo and not constraints.get('enforceLIFO', False):
            return {"error": "Field LIFO (destination_group) diberikan tetapi 'Enforce LIFO' belum diaktifkan. Aktifkan 'Enforce LIFO' sebelum menggunakan nilai destination_group."}

        container = AlgoContainer(
            name='container',
            length=container_data['length'],
            width=container_data['width'],
            height=container_data['height'],
            max_weight=container_data['maxWeight']
        )

        boxes_to_pack = []
        for item in items_data:
            group_name = item['group']
            for i in range(item.get('quantity', 1)):
                unique_name = f"{group_name}_{i+1}"
                
                # PERBAIKAN: Mengambil nilai constraint dengan aman.
                # Kelas Box yang baru akan menangani jika nilai ini None.
                new_box = AlgoBox(
                    name=unique_name,
                    length=item['length'],
                    width=item['width'],
                    height=item['height'],
                    weight=item['weight'],
                    group_name=group_name,
                    allowed_rotations=item.get('allowed_rotations'),
                    max_stack_weight=item.get('max_stack_weight'),
                    priority=item.get('priority'),
                    destination_group=item.get('destination_group')
                )
                boxes_to_pack.append(new_box)
        
        ga = GeneticAlgorithm(
            boxes=boxes_to_pack,
            container=container,
            constraints=constraints,
            population_size=500,
            generations=50,
            mutation_rate=0.4,
            crossover_rate=0.9,
            elitism_count=5
        )
        
        print("Starting GA calculation")  # Debug log
        
        # attach stop_event to GA instance so it can be observed inside run()
        if stop_event is not None:
            try:
                setattr(ga, 'stop_event', stop_event)
            except Exception:
                pass

        raw_result, logs = ga.run(on_log=on_log, )

        if not raw_result:
            return {"error": "Genetic Algorithm tidak menghasilkan solusi yang valid."}

        final_result = format_results_for_frontend(raw_result, container, groups_data)
        final_result['logs'] = logs

        return final_result

    except Exception as e:
        print(f"Terjadi error saat menjalankan algoritma GA: {e}")
        return {"error": str(e)}
