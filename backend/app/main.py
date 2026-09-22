"""
FastAPI main application entrypoint.
Handles both REST API (for web UI) and Teams Bot Framework webhook (/api/messages).
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity

from app.config import settings
from app.integrations.data_store import DataStore
from app.bot.bot_handler import IncidentSupportBot
from app.api import chat, incidents, health


# Initialize Bot Framework adapter
adapter_settings = BotFrameworkAdapterSettings(
    app_id=settings.MICROSOFT_APP_ID,
    app_password=settings.MICROSOFT_APP_PASSWORD
)
adapter = BotFrameworkAdapter(adapter_settings)
bot = IncidentSupportBot()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data on startup."""
    print(f"[Startup] Loading data store...")
    store = DataStore.get_instance()
    store.load()
    print(f"[Startup] {settings.APP_NAME} v{settings.APP_VERSION} ready!")
    yield
    print("[Shutdown] Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Incident Support Assistant - Backend API",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(incidents.router)


@app.post("/api/messages")
async def messages(request: Request) -> Response:
    """
    Microsoft Teams Bot Framework webhook endpoint.
    Teams sends all bot messages to this endpoint.
    """
    if "application/json" in request.headers.get("Content-Type", ""):
        body = await request.json()
    else:
        return Response(status_code=415)

    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    async def call_bot(turn_context):
        await bot.on_turn(turn_context)

    try:
        await adapter.process_activity(activity, auth_header, call_bot)
        return Response(status_code=201)
    except Exception as error:
        print(f"[Bot Error] {error}")
        return Response(status_code=500, content=str(error))


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": {
            "chat": "/api/chat",
            "incidents": "/api/incidents",
            "services_health": "/api/incidents/services/health",
            "teams_webhook": "/api/messages",
            "health": "/health",
            "docs": "/docs"
        }
    }
