import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import spending
from .routers.v2 import router as v2_router

app = FastAPI(title="AusGov Budget Tracker API")

# Production default is the only origin allowed unless CORS_EXTRA_ORIGINS
# adds more (comma-separated) - e.g. for local dev/E2E testing against
# `next dev` on 127.0.0.1/localhost. Never a wildcard; extra origins must be
# explicitly opted in via env var, so the shipped default is unchanged.
_extra_origins = [
    o.strip() for o in os.environ.get("CORS_EXTRA_ORIGINS", "").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://vibefactory.app", *_extra_origins],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(spending.router)
app.include_router(v2_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
