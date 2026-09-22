"""
REST API endpoints for chat (used by frontend web UI).
"""
from fastapi import APIRouter, HTTPException
from app.ai.assistant import AIAssistant
from app.models import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])
assistant = AIAssistant()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to the AI assistant and get a response."""
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        return assistant.chat(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assistant error: {str(e)}")
