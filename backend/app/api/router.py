from fastapi import APIRouter

from app.api.endpoints import (
    advanced,
    agent_v2,
    application_tracker,
    auth,
    bandit,
    benchmark,
    catalog,
    chat,
    compare,
    dashboard,
    digest,
    features_extra,
    grant_checklist,
    grants,
    history,
    insights,
    lead_score,
    lenders,
    metrics,
    nudges,
    pitch,
    predict,
    profile,
    report,
    upload,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(upload.router)
api_router.include_router(compare.router)
api_router.include_router(catalog.router)
api_router.include_router(grants.router)
api_router.include_router(profile.router)
api_router.include_router(report.router)
api_router.include_router(dashboard.router)
api_router.include_router(predict.router)
api_router.include_router(history.router)
api_router.include_router(metrics.router)
api_router.include_router(chat.router)
api_router.include_router(agent_v2.router)
api_router.include_router(insights.router)
api_router.include_router(bandit.router)
api_router.include_router(advanced.router)
api_router.include_router(nudges.router)
api_router.include_router(lead_score.router)
api_router.include_router(pitch.router)
api_router.include_router(benchmark.router)
api_router.include_router(digest.router)
api_router.include_router(lenders.router)
api_router.include_router(grant_checklist.router)
api_router.include_router(application_tracker.router)
api_router.include_router(features_extra.router)
