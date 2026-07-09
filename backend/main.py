"""AI-First CRM — HCP Module. FastAPI entrypoint."""
import os
import sys

# Ensure backend/ is on sys.path when launched as `uvicorn main:app`
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import agent, hcp, interactions
from config import settings
from db.database import engine
from db.models import Base
from seed import seed as run_seed

# Create tables + seed sample HCPs on startup
Base.metadata.create_all(bind=engine)
try:
    run_seed()
except Exception as e:
    print(f"Seed warning: {e}")

app = FastAPI(
    title="AI-First CRM HCP Module",
    description="LangGraph-powered CRM for Healthcare Professional interaction logging",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hcp.router)
app.include_router(interactions.router)
app.include_router(agent.router)


@app.get("/")
def root():
    return {
        "message": "AI-First CRM HCP Module API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    groq_ok = bool(
        settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("your_")
    )
    return {
        "status": "ok",
        "groq_configured": groq_ok,
        "model": settings.GROQ_MODEL,
    }
