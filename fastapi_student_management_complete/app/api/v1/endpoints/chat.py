from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import require_login
from app.core.database import get_db
from app.services.chat_service import ask_ai

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    chart: dict | None = None


@router.post("/chat", response_model=ChatResponse)
def chat_with_ai(payload: ChatRequest, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    try:
        return ask_ai(db, payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
