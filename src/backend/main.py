from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import spending
from .routers.v2 import router as v2_router

app = FastAPI(title="AusGov Budget Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://vibefactory.app"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(spending.router)
app.include_router(v2_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
