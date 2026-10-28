"""Validação e normalização de áreas de interesse (AOI)."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import box, mapping, shape

from app.config import DEFAULT_AOI, TEMP_DIR


def _geometry_from_payload(payload: dict[str, Any]):
    """Aceita Geometry, Feature ou FeatureCollection GeoJSON."""
    kind = payload.get("type")
    if kind == "Feature":
        return shape(payload["geometry"])
    if kind == "FeatureCollection":
        geoms = [shape(f["geometry"]) for f in payload.get("features", [])]
        if not geoms:
            raise ValueError("FeatureCollection da AOI está vazia.")
        gs = gpd.GeoSeries(geoms, crs="EPSG:4326")
        return gs.union_all() if hasattr(gs, "union_all") else gs.unary_union
    if kind in {"Polygon", "MultiPolygon"}:
        return shape(payload)
    raise ValueError("AOI deve ser Polygon, MultiPolygon, Feature ou FeatureCollection.")


def validar_geojson_aoi(payload: dict[str, Any]) -> dict:
    geom = _geometry_from_payload(payload)
    if geom.is_empty:
        raise ValueError("AOI vazia.")
    if not geom.is_valid:
        geom = geom.buffer(0)
    if geom.is_empty or not geom.is_valid:
        raise ValueError("Geometria da AOI inválida.")
    if geom.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("A AOI deve ser poligonal.")
    return mapping(geom)


def bbox_para_geojson(west: float, south: float, east: float, north: float) -> dict:
    if west >= east or south >= north:
        raise ValueError("Bounding box inválida.")
    return mapping(box(west, south, east, north))


def shapefile_para_geojson(shapefile_path: str | Path) -> dict:
    gdf = gpd.read_file(shapefile_path)
    if gdf.empty:
        raise ValueError("AOI vazia.")
    if gdf.crs is None:
        raise ValueError("AOI não possui CRS.")
    gdf = gdf.to_crs("EPSG:4326")
    geom = gdf.geometry.union_all() if hasattr(gdf.geometry, "union_all") else gdf.geometry.unary_union
    return mapping(geom)


def default_aoi_geojson() -> dict:
    return shapefile_para_geojson(DEFAULT_AOI)


def salvar_geojson_temporario(area: dict, prefix: str = "aoi") -> Path:
    area = validar_geojson_aoi(area)
    folder = TEMP_DIR / "aoi"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{prefix}_{uuid.uuid4().hex}.geojson"
    feature = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {}, "geometry": area}],
    }
    path.write_text(json.dumps(feature), encoding="utf-8")
    return path


def criar_regiao_contexto(area: dict, buffer_m: float) -> dict:
    """Cria envelope retangular com buffer em metros em torno da AOI.

    O buffer é calculado em um CRS UTM estimado automaticamente e devolvido em
    EPSG:4326, adequado para GEE/CDSE.
    """
    geom = _geometry_from_payload({"type": "Feature", "geometry": validar_geojson_aoi(area)})
    gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")
    utm = gdf.estimate_utm_crs()
    if utm is None:
        raise ValueError("Não foi possível estimar um CRS projetado para a AOI.")
    gdf_utm = gdf.to_crs(utm)
    buffered = gdf_utm.geometry.iloc[0].buffer(buffer_m).envelope
    out = gpd.GeoSeries([buffered], crs=utm).to_crs("EPSG:4326").iloc[0]
    return mapping(out)


def aoi_summary(area: dict) -> dict:
    geom = _geometry_from_payload({"type": "Feature", "geometry": validar_geojson_aoi(area)})
    gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")
    utm = gdf.estimate_utm_crs()
    area_m2 = float(gdf.to_crs(utm).area.iloc[0]) if utm else None
    minx, miny, maxx, maxy = geom.bounds
    return {
        "geometry_type": geom.geom_type,
        "area_m2": area_m2,
        "bbox": [minx, miny, maxx, maxy],
    }
