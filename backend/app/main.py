from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.calorie import router as calorie_router
from app.api.chat import router as chat_router
from app.api.plans import router as plans_router
from app.api.notifications import router as notifications_router
from app.api.profile import router as profile_router
from app.api.records import router as records_router
from app.core.config import get_settings
from app.core.errors import PlanConflictError, PlanIntegrityError
from app.services.notification_scheduler import create_daily_push_scheduler


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Start optional background services only when their configuration is present."""
    scheduler = create_daily_push_scheduler(get_settings())
    if scheduler is not None:
        scheduler.start()
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(title="FitPlan AI API", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(calorie_router)
app.include_router(chat_router)
app.include_router(profile_router)
app.include_router(records_router)
app.include_router(plans_router)
app.include_router(notifications_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(PlanConflictError)
async def plan_conflict_handler(_request: Request, _exc: PlanConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": "Plan conflict"})


@app.exception_handler(PlanIntegrityError)
async def plan_integrity_handler(_request: Request, _exc: PlanIntegrityError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Plan data is invalid"})
