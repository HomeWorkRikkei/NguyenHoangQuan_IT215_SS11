from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Any, Optional

DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/smarthome_db"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SmartHomePlanModel(Base):
    __tablename__ = "smart_home_plans"
    id = Column(Integer, primary_key=True, index=True)
    plan_code = Column(String(50), unique=True, nullable=False, index=True)
    plan_name = Column(String(255), nullable=False)
    device_quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

class SmartHomePlanCreateSchema(BaseModel):
    plan_code: str = Field(..., min_length=1, max_length=50)
    plan_name: str = Field(..., min_length=1, max_length=255)
    device_quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0.0)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="Smart Home Plans API")

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
    error_type = "Not Found" if exc.status_code == 404 else "Bad Request"
    return make_unified_response(
        status_code=exc.status_code, message=exc.detail, error=error_type, path=request.url.path
    )

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    return make_unified_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Dữ liệu đầu vào không hợp lệ hoặc sai định dạng quy định!",
        error="Unprocessable Entity",
        path=request.url.path
    )

@app.post("/smart-home-plans", status_code=status.HTTP_201_CREATED)
def create_smart_home_plan(request: Request, payload: SmartHomePlanCreateSchema, db: Session = Depends(get_db)):
    existing_plan = db.query(SmartHomePlanModel).filter(SmartHomePlanModel.plan_code == payload.plan_code).first()
    if existing_plan:
        raise HTTPException(status_code=400, detail="Plan code already exists")

    db_plan = SmartHomePlanModel(
        plan_code=payload.plan_code,
        plan_name=payload.plan_name,
        device_quantity=payload.device_quantity,
        price=payload.price
    )
    
    try:
        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống cơ sở dữ liệu: {str(e)}")

    return make_unified_response(
        status_code=201,
        message="Thêm gói thiết bị mới thành công",
        data={
            "id": db_plan.id,
            "plan_code": db_plan.plan_code,
            "plan_name": db_plan.plan_name,
            "device_quantity": db_plan.device_quantity,
            "price": db_plan.price
        },
        path=request.url.path
    )

@app.get("/smart-home-plans")
def get_all_smart_home_plans(request: Request, db: Session = Depends(get_db)):
    plans = db.query(SmartHomePlanModel).all()
    data_list = [
        {
            "id": p.id,
            "plan_code": p.plan_code,
            "plan_name": p.plan_name,
            "device_quantity": p.device_quantity,
            "price": p.price
        } for p in plans
    ]
    return make_unified_response(
        status_code=200, message="Lấy danh sách thành công", data=data_list, path=request.url.path
    )

@app.get("/smart-home-plans/{plan_id}")
def get_smart_home_plan_detail(request: Request, plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(SmartHomePlanModel).filter(SmartHomePlanModel.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    return make_unified_response(
        status_code=200,
        message="Lấy thông tin chi tiết gói thiết bị thành công",
        data={
            "id": plan.id,
            "plan_code": plan.plan_code,
            "plan_name": plan.plan_name,
            "device_quantity": plan.device_quantity,
            "price": plan.price
        },
        path=request.url.path
    )