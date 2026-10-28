from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import (
    auth,
    dashboard,
    fertilizer,
    irrigation,
    predictions,
    recommendations,
    reports,
    weather,
)

app = FastAPI(title="CropSense AI API", version="0.6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, predictions, recommendations, fertilizer, weather, irrigation, dashboard, reports):
    app.include_router(r.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
