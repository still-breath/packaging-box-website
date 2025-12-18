import io
from typing import Dict, List, Any
import pandas as pd


def parse_excel_file_bytes(file_bytes: bytes) -> Dict[str, Any]:
    """
    Parse an Excel file bytes into a dict containing container, items, groups
    Expected sheets: 'container', 'items', 'groups'
    """
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    result: Dict[str, Any] = {}

    # Container
    if 'container' in xls.sheet_names:
        dfc = pd.read_excel(xls, 'container')
        # Expect first row contains fields length,width,height,maxWeight
        if not dfc.empty:
            row = dfc.iloc[0]
            result['container'] = {
                'length': float(row.get('length', 0)),
                'width': float(row.get('width', 0)),
                'height': float(row.get('height', 0)),
                'maxWeight': float(row.get('maxWeight', 0)),
            }

    # Groups
    groups: List[Dict[str, Any]] = []
    if 'groups' in xls.sheet_names:
        dfg = pd.read_excel(xls, 'groups')
        for _, r in dfg.iterrows():
            groups.append({
                'id': str(r.get('id', '')),
                'name': str(r.get('name', '')),
                'color': str(r.get('color', '#CCCCCC'))
            })
    result['groups'] = groups

    # Items
    items: List[Dict[str, Any]] = []
    if 'items' in xls.sheet_names:
        dfi = pd.read_excel(xls, 'items')
        for _, r in dfi.iterrows():
            # allowed_rotations may be stored as string '0,1,2' or numeric
            rotations = r.get('allowed_rotations', None)
            if pd.isna(rotations):
                allowed = None
            elif isinstance(rotations, str):
                try:
                    allowed = [int(x.strip()) for x in rotations.split(',') if x.strip()!='']
                except Exception:
                    allowed = None
            else:
                # single numeric value
                try:
                    allowed = [int(rotations)]
                except Exception:
                    allowed = None

            items.append({
                'id': str(r.get('id', '')),
                'quantity': int(r.get('quantity', 1)),
                'length': float(r.get('length', 0)),
                'width': float(r.get('width', 0)),
                'height': float(r.get('height', 0)),
                'weight': float(r.get('weight', 0)),
                'group': str(r.get('group', '')),
                'allowed_rotations': allowed,
                'max_stack_weight': float(r.get('max_stack_weight', 0)) if not pd.isna(r.get('max_stack_weight', None)) else None,
                'priority': int(r.get('priority', 5)) if not pd.isna(r.get('priority', None)) else None,
                'destination_group': int(r.get('destination_group', 0)) if not pd.isna(r.get('destination_group', None)) else None,
            })
    result['items'] = items

    return result


def generate_result_excel_bytes(result: Dict[str, Any], container: Dict[str, Any], groups: List[Dict[str, Any]], algorithm: str) -> bytes:
    """
    Generate an excel file (bytes) from visualization/result data.
    Sheets: summary, placed, unplaced, container, groups
    """
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        # summary
        summary = {
            'algorithm': [algorithm],
            'fillRate': [result.get('fillRate', result.get('fillRate', None) or result.get('fillRate', 0))],
            'totalWeight': [result.get('totalWeight', 0)]
        }
        pd.DataFrame(summary).to_excel(writer, sheet_name='summary', index=False)

        # container
        pd.DataFrame([container]).to_excel(writer, sheet_name='container', index=False)

        # groups
        if groups:
            pd.DataFrame(groups).to_excel(writer, sheet_name='groups', index=False)

        # placed
        placed = result.get('placedItems', [])
        if placed:
            pd.DataFrame(placed).to_excel(writer, sheet_name='placed', index=False)

        # unplaced
        unplaced = result.get('unplacedItems', [])
        if unplaced:
            pd.DataFrame(unplaced).to_excel(writer, sheet_name='unplaced', index=False)

    return out.getvalue()


def generate_template_excel_bytes() -> bytes:
    """
    Generate a simple import template XLSX with headers for `container`, `groups`, `items`.
    """
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        # container sheet - single-row template
        dfc = pd.DataFrame([{
            'length': 600,  # cm
            'width': 235,
            'height': 260,
            'maxWeight': 2000
        }])
        dfc.to_excel(writer, sheet_name='container', index=False)

        # groups sheet
        dfg = pd.DataFrame([{
            'id': '1',
            'name': 'Default Group',
            'color': '#FF0000'
        }])
        dfg.to_excel(writer, sheet_name='groups', index=False)

        # items sheet with header examples
        dfi = pd.DataFrame([{
            'id': 'box-1',
            'quantity': 1,
            'length': 50,
            'width': 40,
            'height': 30,
            'weight': 10,
            'group': 'Default Group',
            'allowed_rotations': '0,1,2',
            'max_stack_weight': 100,
            'priority': 5,
            'destination_group': 1
        }])
        dfi.to_excel(writer, sheet_name='items', index=False)

    return out.getvalue()
