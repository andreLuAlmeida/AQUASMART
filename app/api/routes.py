from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.agents.aquasmart_agent import AquaSmartAgent
from app.api.schemas import AgentRequest, AnalysisRequest, TestAnalysisRequest
from app.config import AUTO_SOURCE_ORDER, WATER_QUALITY_LABELS, WATER_QUALITY_MODELS
from app.services.aoi_service import default_aoi_geojson
from app.services.demo_service import analisar_cena_teste, listar_cenas_teste
from app.services.job_service import create_job, get_job, run_job

router = APIRouter(prefix="/api")
agent = AquaSmartAgent()


@router.get("/")
def root():
    return {
        "name": "AQUASMART",
        "version": "0.2.0",
        "workflow": "AOI -> aquisição -> padronização -> agentes/tools -> modelos -> mapas/métricas",
    }


@router.get("/health")
def health():
    model_status = {k: v.exists() for k, v in WATER_QUALITY_MODELS.items()}
    return {"status": "ok", "water_quality_models": model_status}


@router.get("/capabilities")
def capabilities():
    return {
        "analysis_types": [
            {"id": "macrophytes", "label": "Macrófitas", "sensor": "Sentinel-1", "model": "U-Net ResNet34"},
            {"id": "water_quality", "label": "Qualidade da água", "sensor": "Sentinel-2", "model": "Modelos .pkl"},
        ],
        "sources": [
            {"id": "auto", "label": "Automática", "recommended": True},
            {"id": "gee", "label": "Google Earth Engine"},
            {"id": "copernicus", "label": "Copernicus Data Space", "note": "Catálogo implementado; fallback para GEE até homologação SAFE→raster."},
        ],
        "auto_source_order": AUTO_SOURCE_ORDER,
        "water_quality_parameters": [
            {"id": k, "label": WATER_QUALITY_LABELS[k], "model_available": WATER_QUALITY_MODELS[k].exists()}
            for k in WATER_QUALITY_MODELS
        ],
        "aoi_methods": ["map_polygon", "map_rectangle", "coordinates", "geojson", "kml", "shapefile_zip", "saved_default"],
    }


@router.get("/aoi/default")
def default_aoi():
    return {"name": "Lagoa REGAP", "geometry": default_aoi_geojson()}


@router.post("/jobs")
def submit_analysis(req: AnalysisRequest, background_tasks: BackgroundTasks):
    job = create_job(req.model_dump())
    background_tasks.add_task(run_job, job["id"])
    return {"id": job["id"], "status": job["status"], "poll_url": f"/api/jobs/{job['id']}"}


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    return job


@router.post("/analysis")
def analysis_sync(req: AnalysisRequest):
    try:
        return agent.analyze(req.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


# Endpoints legados/teste.
@router.get("/demo/scenes")
def scenes():
    return {"count": len(listar_cenas_teste()), "scenes": listar_cenas_teste()}


@router.post("/demo/macrophytes")
def macrofitas(req: TestAnalysisRequest):
    try:
        return analisar_cena_teste(req.image_index)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@router.post("/agent/run")
def run_agent(req: AgentRequest):
    return agent.run(req.message)
