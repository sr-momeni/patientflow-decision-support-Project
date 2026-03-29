from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import database
from backend.api.routes import router as api_router
from backend.chatbot.chatbot_routes import router as chatbot_router
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_BUILD_DIR = BASE_DIR.parent / "frontend" / "build"
FRONTEND_INDEX = FRONTEND_BUILD_DIR / "index.html"
FRONTEND_ASSETS_DIR = FRONTEND_BUILD_DIR / "static"


def _allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="Patient Flow Decision Support API", version="beta")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins() or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    database.init_db()


app.include_router(api_router)
app.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])


if FRONTEND_INDEX.exists():
    if FRONTEND_ASSETS_DIR.exists():
        app.mount("/static", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="frontend-static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend() -> FileResponse:
        return FileResponse(FRONTEND_INDEX)

    @app.exception_handler(404)
    async def spa_fallback(request, exc):
        path = request.url.path
        api_prefixes = (
            "/chatbot",
            "/triage",
            "/metrics",
            "/patient-history",
            "/clinical",
            "/login",
            "/signup",
            "/add-patient",
            "/scoring",
            "/allocate",
        )
        if path.startswith(api_prefixes):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        return FileResponse(FRONTEND_INDEX)
else:
    @app.get("/", include_in_schema=False)
    async def root_status():
        return {
            "message": "Patient Flow API running",
            "frontend_build": False,
            "frontend_expected_path": str(FRONTEND_INDEX),
            "chatbot_ui": "/chatbot/ui",
        }