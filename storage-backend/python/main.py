# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# --- Impor semua fungsi service dari file masing-masing ---
# Pastikan semua file (blf_service.py, clptac_service.py, ga_service.py)
# berada di direktori yang sama dengan main.py
from blf_service import run_blf_packing
from clptac_service import run_clp_packing
from ga_service import run_ga_packing

# Inisialisasi aplikasi FastAPI
app = FastAPI()

# Konfigurasi CORS untuk mengizinkan permintaan dari frontend React Anda
origins = [
    "http://localhost:3000", # Alamat default untuk create-react-app
    "http://localhost:3001",
    "http://localhost:5173", # Alamat default untuk Vite
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Model Data Pydantic untuk Validasi Request ---
class ContainerModel(BaseModel):
    length: float
    width: float
    height: float
    maxWeight: float

class ItemModel(BaseModel):
    id: str
    quantity: int
    length: float
    width: float
    height: float
    weight: float
    group: str
    allowed_rotations: Optional[List[int]] = None
    max_stack_weight: Optional[float] = None
    priority: Optional[int] = None
    destination_group: Optional[int] = None

class GroupModel(BaseModel):
    id: str
    name: str
    color: str

class ConstraintsModel(BaseModel):
    enforceLoadCapacity: bool
    enforceStacking: bool
    enforcePriority: bool
    enforceLIFO: bool

class CalculationRequest(BaseModel):
    container: ContainerModel
    items: List[ItemModel]
    groups: List[GroupModel]
    algorithm: str
    constraints: ConstraintsModel

@app.post("/calculate/python")
async def handle_python_calculation(request: CalculationRequest):
    """
    Menerima permintaan kalkulasi dan memanggil fungsi service yang sesuai.
    """
    container_dict = request.container.dict()
    items_list = [item.dict() for item in request.items]
    groups_list = [group.dict() for group in request.groups]
    constraints_dict = request.constraints.dict()

    result = {}
    
    print(f"Menerima permintaan untuk algoritma: {request.algorithm}")

    if request.algorithm == "PYTHON_BLF":
        result = run_blf_packing(container_dict, items_list, groups_list, constraints_dict)
    elif request.algorithm == "PYTHON_CLPTAC":
        result = run_clp_packing(container_dict, items_list, groups_list, constraints_dict)
    elif request.algorithm == "PYTHON_GA":
        result = run_ga_packing(container_dict, items_list, groups_list, constraints_dict)
    else:
        return {"error": f"Algoritma tidak dikenal: {request.algorithm}"}

    return result

@app.get("/")
def read_root():
    return {"status": "Python Backend is running"}
