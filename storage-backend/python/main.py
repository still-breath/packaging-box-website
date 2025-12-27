# main.py
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import io
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from blf_service import run_blf_packing
from clptac_service import run_clp_packing
from ga_service import run_ga_packing
from excel_utils import parse_excel_file_bytes, generate_result_excel_bytes
from excel_utils import generate_template_excel_bytes

import threading
import uuid
import queue
import json
import time
import math

app = FastAPI(
    title="Storage Box API",
    description="API for storage box optimization with authentication",
    version="1.0.0"
)

def sanitize_for_json(obj):
    """Recursively sanitize data to ensure JSON serializability."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None  # or 0, or a string like "Infinity"
        return obj
    elif isinstance(obj, (int, str, bool, type(None))):
        return obj
    else:
        # For any other type, try to convert to string
        return str(obj)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Storage Box API is running"}

origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    container_dict = request.container.dict()
    items_list = [item.dict() for item in request.items]
    groups_list = [group.dict() for group in request.groups]
    constraints_dict = request.constraints.dict()

    result = {}
    
    # Log incoming payload for debugging
    print(f"Menerima permintaan untuk algoritma: {request.algorithm}")
    try:
        print("Constraints:", constraints_dict)
        print("Items count:", len(items_list))
    except Exception:
        pass

    if request.algorithm == "PYTHON_BLF":
        result = run_blf_packing(container_dict, items_list, groups_list, constraints_dict)
    elif request.algorithm == "PYTHON_CLPTAC":
        result = run_clp_packing(container_dict, items_list, groups_list, constraints_dict)
    elif request.algorithm == "PYTHON_GA":
        result = run_ga_packing(container_dict, items_list, groups_list, constraints_dict)
    else:
        return {"error": f"Algoritma tidak dikenal: {request.algorithm}"}

    # If the algorithm wrapper returned an error dict, convert to HTTP 400
    if isinstance(result, dict) and result.get("error"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@app.post("/import/excel")
async def import_excel(file: UploadFile = File(...)):
    try:
        content = await file.read()
        parsed = parse_excel_file_bytes(content)
        # Basic validation
        if 'container' not in parsed and (not parsed.get('items') and not parsed.get('groups')):
            raise HTTPException(status_code=400, detail='Excel file missing expected sheets')
        return parsed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export/excel")
async def export_excel(payload: Dict):
    try:
        # Expect keys: result, container, groups, algorithm
        result = payload.get('result') or payload.get('calculationResult')
        container = payload.get('container', {})
        groups = payload.get('groups', [])
        algorithm = payload.get('algorithm', 'UNKNOWN')

        xlsx_bytes = generate_result_excel_bytes(result or {}, container or {}, groups or [], algorithm)
        return StreamingResponse(io.BytesIO(xlsx_bytes), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={
            'Content-Disposition': f'attachment; filename="visualization_{algorithm}.xlsx"'
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/templates/import_template.xlsx')
async def download_import_template():
    try:
        xlsx_bytes = generate_template_excel_bytes()
        return StreamingResponse(io.BytesIO(xlsx_bytes), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={
            'Content-Disposition': 'attachment; filename="import_template.xlsx"'
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Streaming job manager for GA (SSE) -----------------
# Simple in-memory job store. Not persistent — fine for local dev.
job_store: Dict[str, Dict[str, Any]] = {}


@app.post("/calculate/stream/start")
async def start_stream_calculation(request: CalculationRequest):
    container_dict = request.container.dict()
    items_list = [item.dict() for item in request.items]
    groups_list = [group.dict() for group in request.groups]
    constraints_dict = request.constraints.dict()

    job_id = uuid.uuid4().hex
    q: queue.Queue = queue.Queue()
    job_store[job_id] = {
        "queue": q,
        "logs": [],
        "result": None,
        "done": False,
        "error": None,
        "cancel_event": threading.Event(),
        "cancelled": False
    }

    def log_cb(msg: str):
        try:
            job_store[job_id]["logs"].append(msg)
            job_store[job_id]["queue"].put({"type": "log", "data": msg})
            print(f"Log callback: {msg}")  # Debug log
        except Exception as e:
            print(f"Error in log_cb: {e}")

    def run_job():
        try:
            cancel_event = job_store[job_id]["cancel_event"]
            # route to the appropriate algorithm; GA and CLPTAC support streaming
            if request.algorithm == "PYTHON_GA":
                final = run_ga_packing(container_dict, items_list, groups_list, constraints_dict, on_log=log_cb, stop_event=cancel_event)
            elif request.algorithm == "PYTHON_CLPTAC":
                # CLPTAC now supports on_log and stop_event for cooperative streaming
                final = run_clp_packing(container_dict, items_list, groups_list, constraints_dict, on_log=log_cb, stop_event=cancel_event)
            else:
                # fallback to synchronous call for other algorithms
                if request.algorithm == "PYTHON_BLF":
                    final = run_blf_packing(container_dict, items_list, groups_list, constraints_dict)
                else:
                    final = run_ga_packing(container_dict, items_list, groups_list, constraints_dict, on_log=log_cb, stop_event=cancel_event)
            # if cancelled, ensure we propagate as error
            if job_store[job_id].get("cancelled"):
                job_store[job_id]["error"] = "Cancelled by user"
                job_store[job_id]["done"] = True
                job_store[job_id]["queue"].put({"type": "error", "data": "Cancelled by user"})
                return
            
            # Sanitize result to ensure JSON serializability
            sanitized_final = sanitize_for_json(final)
            job_store[job_id]["result"] = sanitized_final
            job_store[job_id]["done"] = True
            
            # Safely serialize to JSON
            try:
                json_data = json.dumps(sanitized_final)
                print(f"Streaming done for job {job_id}, payload size: {len(json_data)} bytes")
                job_store[job_id]["queue"].put({"type": "done", "data": json_data})
            except Exception as json_err:
                print(f"JSON serialization error: {json_err}")
                error_msg = f"Failed to serialize result: {str(json_err)}"
                job_store[job_id]["error"] = error_msg
                job_store[job_id]["queue"].put({"type": "error", "data": error_msg})
        except Exception as e:
            job_store[job_id]["error"] = str(e)
            job_store[job_id]["done"] = True
            job_store[job_id]["queue"].put({"type": "error", "data": str(e)})

    thread = threading.Thread(target=run_job, daemon=True)
    thread.start()

    return {"job_id": job_id}


@app.post("/calculate/stream/{job_id}/cancel")
async def cancel_stream_job(job_id: str):
    # Mark the job cancelled and set the event so running thread stops
    if job_id not in job_store:
        return {"error": "Job not found"}

    try:
        job_store[job_id]["cancelled"] = True
        cancel_event = job_store[job_id].get("cancel_event")
        if cancel_event:
            cancel_event.set()
        # push a log entry and an error event so SSE clients see immediate feedback
        job_store[job_id]["logs"].append("Job cancelled by user")
        job_store[job_id]["queue"].put({"type": "log", "data": "Job cancelled by user"})
        job_store[job_id]["queue"].put({"type": "error", "data": "Cancelled by user"})
        job_store[job_id]["done"] = True
        return {"status": "cancelled"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/calculate/stream/{job_id}")
def stream_calculation(job_id: str):
    from fastapi import Response
    from fastapi.responses import StreamingResponse

    if job_id not in job_store:
        return {"error": "Job not found"}

    q: queue.Queue = job_store[job_id]["queue"]

    def event_generator():
        # Yield any existing logs first
        for l in job_store[job_id]["logs"]:
            yield f"data: {l}\n\n"

        # Then stream new messages
        while True:
            try:
                item = q.get(timeout=0.5)
            except Exception:
                # If job done and queue empty, break
                if job_store[job_id]["done"]:
                    break
                continue

            if item["type"] == "log":
                # SSE data message
                safe = str(item["data"]).replace("\n", " ")
                yield f"data: {safe}\n\n"
            elif item["type"] == "done":
                yield f"event: done\ndata: {item['data']}\n\n"
                break
            elif item["type"] == "error":
                yield f"event: error\ndata: {item['data']}\n\n"
                break

        # final newline to close stream
        return

    return StreamingResponse(event_generator(), media_type="text/event-stream")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Konfigurasi JWT
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required. Please set it in your .env file.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Setup OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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
                "email": "dummy@email.com"
            }
        }
    except Exception as e:
        return {"detail": str(e)}, 401

@app.get("/")
def read_root():
    return {"status": "Python Backend is running"}
