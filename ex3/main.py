from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Any, Optional, Literal

DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/hospital_db"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class MedicalDeviceModel(Base):
    __tablename__ = "medical_devices"
    id = Column(Integer, primary_key=True, index=True)
    device_code = Column(String(50), unique=True, nullable=False, index=True)
    device_name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=False)
    status = Column(Enum("ACTIVE", "INACTIVE"), default="ACTIVE", nullable=False)

class MedicalDeviceCreateSchema(BaseModel):
    device_code: str = Field(..., min_length=1, max_length=50)
    device_name: str = Field(..., min_length=3, max_length=255)
    department: str = Field(..., min_length=1, max_length=100)
    status: Optional[Literal["ACTIVE", "INACTIVE"]] = "ACTIVE"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="Medical Devices Management API")

def make_unified_response(
    status_code: int, message: str, data: Any = None, error: Optional[str] = None, path: str = ""
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "statusCode": status_code,
            "message": message,
            "error": error,
            "data": data,
            "path": path,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    )

@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    return make_unified_response(
        status_code=exc.status_code,
        message=exc.detail,
        error="Not Found" if exc.status_code == 404 else "Bad Request",
        path=request.url.path
    )

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    return make_unified_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Dữ liệu đầu vào không hợp lệ hoặc sai định dạng quy định!",
        error="Unprocessable Entity",
        path=request.url.path
    )

@app.post("/devices", status_code=status.HTTP_201_CREATED)
def create_device(request: Request, payload: MedicalDeviceCreateSchema, db: Session = Depends(get_db)):
    existing_device = db.query(MedicalDeviceModel).filter(MedicalDeviceModel.device_code == payload.device_code).first()
    if existing_device:
        raise HTTPException(status_code=400, detail="Mã số thiết bị y tế này đã tồn tại trên hệ thống!")

    db_device = MedicalDeviceModel(
        device_code=payload.device_code,
        device_name=payload.device_name,
        department=payload.department,
        status=payload.status
    )
    
    try:
        db.add(db_device)
        db.commit()
        db.refresh(db_device)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi nghẽn mạch ghi dữ liệu hệ thống: {str(e)}")

    return make_unified_response(
        status_code=201,
        message="Thêm thiết bị y tế thành công",
        data={
            "id": db_device.id,
            "device_code": db_device.device_code,
            "device_name": db_device.device_name,
            "department": db_device.department,
            "status": db_device.status
        },
        path=request.url.path
    )

@app.get("/devices")
def get_all_devices(request: Request, db: Session = Depends(get_db)):
    devices = db.query(MedicalDeviceModel).all()
    data_list = [
        {
            "id": d.id,
            "device_code": d.device_code,
            "device_name": d.device_name,
            "department": d.department,
            "status": d.status
        } for d in devices
    ]
    return make_unified_response(
        status_code=200, message="Lấy danh sách thiết bị y tế thành công", data=data_list, path=request.url.path
    )

@app.get("/devices/{device_id}")
def get_device_detail(request: Request, device_id: int, db: Session = Depends(get_db)):
    device = db.query(MedicalDeviceModel).filter(MedicalDeviceModel.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    return make_unified_response(
        status_code=200,
        message="Lấy thông tin chi tiết thiết bị y tế thành công",
        data={
            "id": device.id,
            "device_code": device.device_code,
            "device_name": device.device_name,
            "department": device.department,
            "status": device.status
        },
        path=request.url.path
    )