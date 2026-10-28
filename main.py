from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import OUTPUT_DIR

app = FastAPI(
    title="AQUASMART — Geoprocessamento + Agentes",
    description="Aquisição Sentinel-1/Sentinel-2, agentes especializados, inferência e produtos geoespaciais.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(OUTPUT_DIR)), name="files")
app.include_router(router)

@app.get("/")
def home():
    return {"name": "AQUASMART", "api": "/api", "docs": "/docs"}
