"""Tool de aquisição usada pelo agente orquestrador."""
from app.services.acquisition_service import adquirir

TOOL_DEFINITION = {
    "name": "acquire_satellite_image",
    "description": "Adquire Sentinel-1 ou Sentinel-2 via GEE/Copernicus com fallback seguro.",
}


def acquire_satellite_image_tool(**kwargs):
    return adquirir(**kwargs)
