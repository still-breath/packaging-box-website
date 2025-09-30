# main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# --- Impor semua fungsi service dari file masing-masing ---
# Pastikan semua file (blf_service.py, clptac_service.py, ga_service.py)
# berada di direktori yang sama dengan main.py
from blf_service import run_blf_packing
from clptac_service import run_clp_packing
from ga_service import run_ga_packing

# Inisialisasi aplikasi FastAPI
app = FastAPI(
    title="Storage Box API",
    description="API for storage box optimization with authentication",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Storage Box API is running"}

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

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

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

# Konfigurasi password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Konfigurasi JWT
SECRET_KEY = "your-secret-key-here"  # Ganti dengan secret key yang aman
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Setup OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Fungsi helper
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/auth/register")
async def register(user_data: UserCreate):
    try:
        # Validasi input
        if not user_data.username or not user_data.email or not user_data.password:
            return {"detail": "Missing required fields"}, 400
            
        hashed_password = get_password_hash(user_data.password)
        # TODO: Save to database
        
        # Return success response
        return {
            "status": "success",
            "user": {
                "id": 1,  # dummy id
                "username": user_data.username,
                "email": user_data.email,
                "created_at": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        return {"detail": str(e)}, 400

@app.post("/auth/login")
async def login(login_data: LoginRequest):
    try:
        # TODO: Validate against database
        if not login_data.username or not login_data.password:
            return {"detail": "Missing username or password"}, 400
            
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": login_data.username},
            expires_delta=access_token_expires
        )
        
        # Return success response
        return {
            "status": "success",
            "token": access_token,
            "token_type": "bearer",
            "user": {
                "username": login_data.username,
                "email": "dummy@email.com"  # Will be replaced with DB data
            }
        }
    except Exception as e:
        return {"detail": str(e)}, 401

@app.get("/")
def read_root():
    return {"status": "Python Backend is running"}
