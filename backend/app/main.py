from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.database_init import init_database
from app.services.gov_aid_refresh import refresh_from_json


@asynccontextmanager
async def lifespan(_: FastAPI):
    db = SessionLocal()
    try:
        init_database(db)
        refresh_from_json(db)
    finally:
        db.close()
    yield


_settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[_settings.RATE_LIMIT])
app = FastAPI(title="BNPL Advisor for SMEs", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/", include_in_schema=False)
def root():
    """Browser-friendly entry: API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    from app.core.config import get_settings

    s = get_settings()
    return {
        "status": "ok",
        "version": "4.0",
        "features": [
            "rag_chat",
            "vector_rag",
            "langchain_agents",
            "ml_predict",
            "unsupervised_insights",
            "bandit_ucb",
            "rl_policy",
            "invoice_ocr",
            "finetune_llm_stub",
            "compare_financing",
            "cash_forecast",
            "jwt_auth_optional",
            "gov_aid_refresh",
            "sector_playbooks",
            "audit_log",
        ],
        "vector_rag": s.USE_VECTOR_RAG,
        "llm_configured": bool(s.active_llm_api_key),
        "llm_provider": "chutes" if s.CHUTES_API_KEY else ("openai" if s.OPENAI_API_KEY else "none"),
        "openai_configured": bool(s.OPENAI_API_KEY),
        "chutes_configured": bool(s.CHUTES_API_KEY),
        "app_env": s.APP_ENV,
    }
