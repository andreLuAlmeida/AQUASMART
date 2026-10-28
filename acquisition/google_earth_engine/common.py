"""Utilitários compartilhados pelos módulos Sentinel do Earth Engine."""

from pathlib import Path

import ee
import rasterio


def geojson_para_ee(area: dict) -> ee.Geometry:
    """Converte uma geometria GeoJSON (Polygon/MultiPolygon) para ee.Geometry."""
    if not isinstance(area, dict):
        raise ValueError("A área deve ser uma geometria GeoJSON em formato de objeto.")

    tipo = area.get("type")
    if tipo not in {"Polygon", "MultiPolygon"}:
        raise ValueError("A API aceita área GeoJSON do tipo Polygon ou MultiPolygon.")

    if not area.get("coordinates"):
        raise ValueError("A geometria GeoJSON não possui coordenadas.")

    return ee.Geometry(area)


def escrever_nomes_bandas(tif_path, nomes: list[str]) -> None:
    """Grava descrições das bandas dentro de um GeoTIFF exportado."""
    caminho = Path(tif_path)
    if not caminho.exists():
        raise FileNotFoundError(f"GeoTIFF não encontrado após exportação: {caminho}")

    with rasterio.open(caminho, "r+") as dataset:
        for indice, nome in enumerate(nomes, start=1):
            dataset.set_band_description(indice, nome)
