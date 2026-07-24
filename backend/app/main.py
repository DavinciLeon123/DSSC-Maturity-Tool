from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.initiatives import router as initiatives_router
from app.api.v1.questionnaire import router as questionnaire_router
from app.api.v1.reports import router as reports_router
from app.api.v1.scoring import router as scoring_router
from app.core.config import settings
from app.services.mami_config import (
    load_dssc_questionnaire_config,
    load_questionnaire_config,
    load_questionnaire_configs,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load legacy v1 questionnaire config (kept for reference)
    app.state.questionnaire_config = load_questionnaire_config()
    # Load v2 questionnaire configs keyed by participant type {"DSI": {...}, "SP": {...}}
    app.state.questionnaire_configs = load_questionnaire_configs()
    # Load the new universal DSSC questionnaire config (52 questions / 6
    # categories, no participant_type split) — the sole startup config
    # singleton now that the ZEN/MAMI subsystem is removed (SCOR-03).
    app.state.dssc_questionnaire_config = load_dssc_questionnaire_config()
    yield


app = FastAPI(
    title="MAMI Checker API",
    description="API for the MAMI Framework DSI Assessment Tool — CoE-DSC / TNO",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "CoE-DSC", "url": "https://coe-dsc.nl"},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]  # slowapi's handler type predates Starlette's generic Request[State]

app.include_router(auth_router, prefix="/api/v1")
app.include_router(initiatives_router, prefix="/api/v1")
app.include_router(questionnaire_router, prefix="/api/v1")
app.include_router(scoring_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
