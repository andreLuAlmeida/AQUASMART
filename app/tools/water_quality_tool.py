"""Tool de qualidade da água."""
from app.services.water_quality import inferir_qualidade_agua

TOOL_DEFINITION = {
    "name": "analyze_water_quality",
    "description": "Executa modelos de clorofila-a, turbidez, Secchi e PC/RFU sobre Sentinel-2.",
}


def analyze_water_quality_tool(image_path, aoi_path, parameters=None):
    return inferir_qualidade_agua(image_path, aoi_path, parameters)
