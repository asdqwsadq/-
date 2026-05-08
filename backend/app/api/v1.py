from __future__ import annotations

from fastapi import APIRouter

from app.kongming_agent.backend.app.api.admin import router as admin_router
from app.kongming_agent.backend.app.api.agent import router as agent_router
from app.kongming_agent.backend.app.api.feedback import router as feedback_router
from app.kongming_agent.backend.app.api.health import router as health_router
from app.kongming_agent.backend.app.api.knowledge import router as knowledge_router


router = APIRouter()
router.include_router(health_router)
router.include_router(agent_router)
router.include_router(knowledge_router)
router.include_router(feedback_router)
router.include_router(admin_router)
