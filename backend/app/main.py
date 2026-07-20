from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.calorie import router as calorie_router
from app.api.plans import router as plans_router
from app.api.profile import router as profile_router
from app.api.records import router as records_router

app = FastAPI(title="FitPlan AI API", version="0.1.0")
app.include_router(auth_router)
app.include_router(calorie_router)
app.include_router(profile_router)
app.include_router(records_router)
app.include_router(plans_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
