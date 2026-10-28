"""Agente determinístico responsável pela AOI."""
from app.services.aoi_service import aoi_summary, salvar_geojson_temporario, validar_geojson_aoi


class AOIAgent:
    name = "AOI Agent"

    def prepare(self, area: dict) -> dict:
        normalized = validar_geojson_aoi(area)
        path = salvar_geojson_temporario(normalized)
        return {
            "geometry": normalized,
            "path": str(path),
            "summary": aoi_summary(normalized),
        }
