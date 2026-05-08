from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import login
from app.core.database import get_db

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str


@router.post("/login", response_model=LoginResponse)
def user_login(payload: LoginRequest, db: Session = Depends(get_db)):
    result = login(db, payload.username, payload.password)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    return result
