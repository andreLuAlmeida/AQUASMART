"""Aquisição Sentinel-2 SR Harmonized via Earth Engine, sem geemap."""
from __future__ import annotations

import zipfile
from pathlib import Path

import ee
import rasterio
import requests

from acquisition.google_earth_engine.auth import inicializar_earth_engine
from acquisition.google_earth_engine.config import S2_COLLECTION, S2_TARGET_SCALE

MODEL_BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A"]


def buscar_colecao(aoi, data_inicio: str, data_fim: str, cobertura_nuvens: float | None = 30):
    col = ee.ImageCollection(S2_COLLECTION).filterDate(data_inicio, data_fim).filterBounds(aoi)
    if cobertura_nuvens is not None:
        col = col.filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", cobertura_nuvens))
    return col.sort("CLOUDY_PIXEL_PERCENTAGE")


def serializar_imagem(image: ee.Image) -> dict:
    return {
        "id": image.id().getInfo(),
        "datetime": ee.Date(image.get("system:time_start")).format("YYYY-MM-dd'T'HH:mm:ss").getInfo(),
        "tile": image.get("MGRS_TILE").getInfo(),
        "cloud_cover": image.get("CLOUDY_PIXEL_PERCENTAGE").getInfo(),
        "product_id": image.get("PRODUCT_ID").getInfo(),
        "bands": image.bandNames().getInfo(),
    }


def pesquisar(area: dict, data_inicio: str, data_fim: str, max_items: int = 10, cobertura_nuvens: float = 30) -> list[dict]:
    inicializar_earth_engine(permitir_login_interativo=False)
    aoi = ee.Geometry(area)
    col = buscar_colecao(aoi, data_inicio, data_fim, cobertura_nuvens)
    n = min(int(col.size().getInfo()), max_items)
    lst = col.toList(n)
    return [serializar_imagem(ee.Image(lst.get(i))) for i in range(n)]


def _write_download(response: requests.Response, output_path: Path) -> None:
    ctype = response.headers.get("content-type", "").lower()
    if "zip" in ctype or response.content[:2] == b"PK":
        zp = output_path.with_suffix(".zip")
        zp.write_bytes(response.content)
        with zipfile.ZipFile(zp) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith((".tif", ".tiff"))]
            if not names:
                raise RuntimeError("GEE retornou ZIP sem GeoTIFF Sentinel-2.")
            with zf.open(names[0]) as src, output_path.open("wb") as dst:
                dst.write(src.read())
        zp.unlink(missing_ok=True)
    else:
        output_path.write_bytes(response.content)


def baixar_melhor_imagem(
    area: dict,
    data_inicio: str,
    data_fim: str,
    output_dir: str | Path,
    cobertura_nuvens: float = 30,
) -> dict:
    """Exporta as 8 bandas usadas pelos modelos em reflectância 0..1.

    Sentinel-2 SR Harmonized possui fator de escala 1e-4. Os modelos enviados
    foram treinados com valores médios ~0.02-0.05, portanto a escala é aplicada
    antes da inferência.
    """
    inicializar_earth_engine(permitir_login_interativo=False)
    aoi = ee.Geometry(area)
    col = buscar_colecao(aoi, data_inicio, data_fim, cobertura_nuvens)
    if int(col.size().getInfo()) == 0:
        raise LookupError("Nenhuma imagem Sentinel-2 compatível foi encontrada no GEE.")

    image = ee.Image(col.first())
    meta = serializar_imagem(image)
    missing = [b for b in MODEL_BANDS if b not in meta["bands"]]
    if missing:
        raise RuntimeError(f"Cena Sentinel-2 sem bandas necessárias: {missing}")

    # Todas as bandas são reamostradas para 10 m. Reflectância = DN * 1e-4.
    target_proj = image.select("B2").projection()
    parts = []
    for band in MODEL_BANDS:
        layer = image.select(band).multiply(0.0001).toFloat()
        if band not in {"B2", "B3", "B4", "B8"}:
            layer = layer.resample("bilinear").reproject(target_proj)
        parts.append(layer.rename(band))
    export = ee.Image.cat(*parts).select(MODEL_BANDS)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    image_id = meta["id"].split("/")[-1]
    output_path = out_dir / f"S2_GEE_{image_id}_8bands.tif"
    url = export.getDownloadURL({
        "scale": S2_TARGET_SCALE,
        "region": area,
        "format": "GEO_TIFF",
        "filePerBand": False,
    })
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    _write_download(response, output_path)

    with rasterio.open(output_path, "r+") as src:
        if src.count != len(MODEL_BANDS):
            raise RuntimeError(f"GeoTIFF S2 deveria ter 8 bandas; recebeu {src.count}.")
        for i, name in enumerate(MODEL_BANDS, 1):
            src.set_band_description(i, name)
        raster_meta = {
            "crs": str(src.crs),
            "resolution": list(src.res),
            "shape": [src.height, src.width],
            "bounds": list(src.bounds),
        }

    return {
        **meta,
        "source": "gee",
        "source_label": "Google Earth Engine",
        "arquivo": str(output_path),
        "bands_exported": MODEL_BANDS,
        "reflectance_scale_applied": 0.0001,
        **raster_meta,
    }
