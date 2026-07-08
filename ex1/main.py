from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Any, Optional

DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/parking_db"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ParkingSlotModel(Base):
    __tablename__ = "parking_slots"
    id = Column(Integer, primary_key=True, index=True)
    slot_code = Column(String(50), unique=True, nullable=False)
    zone_name = Column(String(255), nullable=False)
    max_weight = Column(Integer, nullable=False)
    is_available = Column(Boolean, default=True)

class ParkingSlotCreateSchema(BaseModel):
    slot_code: str = Field(..., min_length=1, max_length=50)
    zone_name: str = Field(..., min_length=3, max_length=255)
    max_weight: int = Field(..., gt=0)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="Parking Lot Management API")

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

@app.post("/parking-slots", status_code=status.HTTP_201_CREATED)
def create_parking_slot(request: Request, payload: ParkingSlotCreateSchema, db: Session = Depends(get_db)):
    existing_slot = db.query(ParkingSlotModel).filter(ParkingSlotModel.slot_code == payload.slot_code).first()
    if existing_slot:
        raise HTTPException(status_code=400, detail="Mã vị trí đỗ xe này đã tồn tại trên hệ thống!")

    db_slot = ParkingSlotModel(
        slot_code=payload.slot_code,
        zone_name=payload.zone_name,
        max_weight=payload.max_weight
    )
    
    try:
        db.add(db_slot)
        db.commit()
        db.refresh(db_slot)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi cơ sở dữ liệu hệ thống: {str(e)}")

    return make_unified_response(
        status_code=201,
        message="Thêm vị trí đỗ xe thành công",
        data={
            "id": db_slot.id,
            "slot_code": db_slot.slot_code,
            "zone_name": db_slot.zone_name,
            "max_weight": db_slot.max_weight,
            "is_available": db_slot.is_available
        },
        path=request.url.path
    )

@app.get("/parking-slots")
def get_all_parking_slots(request: Request, db: Session = Depends(get_db)):
    slots = db.query(ParkingSlotModel).all()
    data_list = [
        {
            "id": s.id,
            "slot_code": s.slot_code,
            "zone_name": s.zone_name,
            "max_weight": s.max_weight,
            "is_available": s.is_available
        } for s in slots
    ]
    return make_unified_response(
        status_code=200,
        message="Lấy danh sách vị trí đỗ xe thành công",
        data=data_list,
        path=request.url.path
    )

@app.get("/parking-slots/{slot_id}")
def get_parking_slot_detail(request: Request, slot_id: int, db: Session = Depends(get_db)):
    slot = db.query(ParkingSlotModel).filter(ParkingSlotModel.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Parking slot not found")
        
    return make_unified_response(
        status_code=200,
        message="Lấy chi tiết vị trí đỗ xe thành công",
        data={
            "id": slot.id,
            "slot_code": slot.slot_code,
            "zone_name": slot.zone_name,
            "max_weight": slot.max_weight,
            "is_available": slot.is_available
        },
        path=request.url.path
    )