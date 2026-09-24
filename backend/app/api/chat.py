"""
REST API endpoints for chat (used by frontend web UI).
"""
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from app.ai.assistant import AIAssistant
from app.models import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

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


@router.post("/upload-image", response_model=ChatResponse)
async def upload_image(
    file: UploadFile = File(...),
    conversation_id: str = Form(default=""),
) -> ChatResponse:
    """Analyze an incident screenshot and reuse the existing Smart Investigation flow."""
    allowed = {"png", "jpg", "jpeg", "webp"}
    filename = (file.filename or "" ).lower()
    file_ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    if file_ext not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported image type. Upload PNG, JPG, JPEG, or WEBP.")

    try:
        contents = await file.read()
        logger.info("Image received by endpoint: filename=%s, size=%s bytes", file.filename, len(contents))
        response = assistant.analyze_screenshot(contents, filename=file.filename or "screenshot", conversation_id=conversation_id or None)
        logger.info("Endpoint returning response: %s", response)
        return response
    except Exception as e:
        logger.exception("Upload endpoint failed while processing image=%s", file.filename)
        raise HTTPException(status_code=500, detail=f"Screenshot analysis error: {str(e)}")
