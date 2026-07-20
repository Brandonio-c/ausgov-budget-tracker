from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import spending

app = FastAPI(title="AusGov Budget Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://vibefactory.app"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(spending.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
