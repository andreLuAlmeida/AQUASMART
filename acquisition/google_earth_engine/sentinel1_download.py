"""Aquisição Sentinel-1 GRD (VV/VH) via Google Earth Engine."""
from __future__ import annotations

import zipfile
from pathlib import Path

import ee
import rasterio
import requests

from acquisition.google_earth_engine.auth import inicializar_earth_engine
from acquisition.google_earth_engine.config import (
    S1_COLLECTION,
    S1_INSTRUMENT_MODE,
    S1_REQUIRED_POLARIZATIONS,
    S1_TARGET_SCALE,
)


def geojson_para_ee(area: dict) -> ee.Geometry:
    return ee.Geometry(area)


def buscar_colecao(aoi: ee.Geometry, data_inicio: str, data_fim: str, orbit_pass: str | None = None):
    colecao = (
        ee.ImageCollection(S1_COLLECTION)
        .filterDate(data_inicio, data_fim)
        .filterBounds(aoi)
        .filter(ee.Filter.eq("instrumentMode", S1_INSTRUMENT_MODE))
    )
    for pol in S1_REQUIRED_POLARIZATIONS:
        colecao = colecao.filter(
            ee.Filter.listContains("transmitterReceiverPolarisation", pol)
        )
    if orbit_pass:
        colecao = colecao.filter(ee.Filter.eq("orbitProperties_pass", orbit_pass.upper()))
    return colecao


def serializar_imagem(image: ee.Image) -> dict:
    return {
        "id": image.id().getInfo(),
        "datetime": ee.Date(image.get("system:time_start")).format("YYYY-MM-dd'T'HH:mm:ss").getInfo(),
        "orbit_state": image.get("orbitProperties_pass").getInfo(),
        "relative_orbit": image.get("relativeOrbitNumber_start").getInfo(),
        "polarizations": image.get("transmitterReceiverPolarisation").getInfo(),
        "bands": image.bandNames().getInfo(),
    }


def pesquisar(area: dict, data_inicio: str, data_fim: str, max_items: int = 10, orbit_pass: str | None = None) -> list[dict]:
    inicializar_earth_engine(permitir_login_interativo=False)
    aoi = geojson_para_ee(area)
    col = buscar_colecao(aoi, data_inicio, data_fim, orbit_pass).sort("system:time_start")
    n = min(int(col.size().getInfo()), max_items)
    lst = col.toList(n)
    return [serializar_imagem(ee.Image(lst.get(i))) for i in range(n)]


def _write_download(response: requests.Response, output_path: Path) -> None:
    """Aceita retorno TIFF direto ou ZIP com TIFF do EE."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ctype = response.headers.get("content-type", "").lower()
    if "zip" in ctype or response.content[:2] == b"PK":
        zip_path = output_path.with_suffix(".zip")
        zip_path.write_bytes(response.content)
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith((".tif", ".tiff"))]
            if not names:
                raise RuntimeError("Earth Engine retornou ZIP sem GeoTIFF.")
            # filePerBand=False deve produzir um único tif multibanda.
            with zf.open(names[0]) as src, output_path.open("wb") as dst:
                dst.write(src.read())
        zip_path.unlink(missing_ok=True)
    else:
        output_path.write_bytes(response.content)


def baixar_melhor_imagem(
    area_busca: dict,
    area_exportacao: dict,
    data_inicio: str,
    data_fim: str,
    output_dir: str | Path,
    orbit_pass: str | None = None,
    preferir_mais_recente: bool = True,
) -> dict:
    """Baixa Sentinel-1 VV/VH em uma região de contexto.

    `area_busca` normalmente é a AOI original. `area_exportacao` normalmente é
    AOI + buffer/contexto, evitando mudar o contexto da U-Net antes da inferência.
    """
    inicializar_earth_engine(permitir_login_interativo=False)
    search_geom = geojson_para_ee(area_busca)
    export_geom = geojson_para_ee(area_exportacao)
    col = buscar_colecao(search_geom, data_inicio, data_fim, orbit_pass)
    total = int(col.size().getInfo())
    if total == 0:
        raise LookupError("Nenhuma imagem Sentinel-1 compatível foi encontrada no GEE.")

    col = col.sort("system:time_start", not preferir_mais_recente)
    image = ee.Image(col.first())
    meta = serializar_imagem(image)
    if not {"VV", "VH"}.issubset(set(meta["bands"])):
        raise RuntimeError(f"Cena sem VV/VH: {meta['bands']}")

    export = image.select(["VV", "VH"])
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    image_id = meta["id"].split("/")[-1]
    output_path = out_dir / f"S1_GEE_{image_id}_VV-VH.tif"

    url = export.getDownloadURL({
        "scale": S1_TARGET_SCALE,
        "region": area_exportacao,
        "format": "GEO_TIFF",
        "filePerBand": False,
    })
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    _write_download(response, output_path)

    with rasterio.open(output_path, "r+") as src:
        if src.count != 2:
            raise RuntimeError(f"GeoTIFF S1 deveria ter 2 bandas; recebeu {src.count}.")
        src.set_band_description(1, "VV")
        src.set_band_description(2, "VH")
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
        "bands_exported": ["VV", "VH"],
        **raster_meta,
    }


def baixar_primeira_imagem(area: dict, data_inicio: str, data_fim: str, output_dir: str | Path, orbit_pass: str | None = None) -> dict:
    """Compatibilidade com a API antiga."""
    return baixar_melhor_imagem(area, area, data_inicio, data_fim, output_dir, orbit_pass, preferir_mais_recente=False)
