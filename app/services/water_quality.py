"""Inferência dos modelos Sentinel-2 de qualidade da água."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize

from app.config import OUTPUT_DIR, WATER_QUALITY_LABELS, WATER_QUALITY_MODELS

SENSOR_BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A"]
MODEL_BASE_FEATURES = [
    "B2-490", "B3-560", "B4-665", "B5-705",
    "B6-740", "B7-783", "B8-842", "B8A-865",
]
BAND_MAPPING = {"BLUE": "B2-490", "GREEN": "B3-560", "RED": "B4-665", "RE1": "B5-705", "RE2": "B6-740", "NIR": "B8-842"}
NDWI_THRESHOLD = 0.0
NDVI_THRESHOLD = 0.2


def calculate_spectral_indices(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    df = df.copy()
    eps = 1e-8
    B, G, R = df[BAND_MAPPING["BLUE"]], df[BAND_MAPPING["GREEN"]], df[BAND_MAPPING["RED"]]
    RE1, RE2, NIR = df[BAND_MAPPING["RE1"]], df[BAND_MAPPING["RE2"]], df[BAND_MAPPING["NIR"]]
    df["GREEN_BLUE"] = G / (B + eps)
    df["GREEN_RED"] = G / (R + eps)
    df["NIR_RED"] = NIR / (R + eps)
    df["GB1"] = G / (B + eps)
    df["GR"] = G / (R + eps)
    df["NDWI"] = (G - NIR) / (G + NIR + eps)
    df["NDVI"] = (NIR - R) / (NIR + R + eps)
    df["GNDVI"] = (NIR - G) / (NIR + G + eps)
    df["BNDVI"] = (NIR - B) / (NIR + B + eps)
    df["CVI"] = (NIR * R) / (G**2 + eps)
    df["CI_green"] = (NIR / (G + eps)) - 1
    df["NDTI"] = (R - G) / (R + G + eps)
    df["SABI"] = (NIR - R) / (B + G + eps)
    df["KIVU"] = (B - R) / (G + eps)
    df["B3B1"] = (R - B) / (R + B + eps)
    df["R2_B"] = (R**2) / (B + eps)
    df["NDCI"] = (RE1 - R) / (RE1 + R + eps)
    df["NDRE"] = (NIR - RE2) / (NIR + RE2 + eps)
    df["CI_rededge"] = (NIR / (RE2 + eps)) - 1
    df["2BDA_2"] = RE1 / (R + eps)
    df["3BDA_MOD"] = (1 / (R + eps)) - (1 / (RE1 + eps))
    df["3BDA_1"] = df["3BDA_MOD"] * NIR
    df["MCI"] = RE1 - (R + (RE2 - R) * ((705 - 665) / (740 - 665)))
    df["Kab1_Rrs"] = 1.67 - 3.94 * np.log(B.clip(lower=eps)) + 3.78 * np.log(G.clip(lower=eps))
    indices = [
        "GREEN_BLUE", "GREEN_RED", "NIR_RED", "GB1", "GR", "NDWI", "NDVI", "GNDVI",
        "BNDVI", "CVI", "CI_green", "NDTI", "SABI", "KIVU", "B3B1", "R2_B",
        "NDCI", "NDRE", "CI_rededge", "2BDA_2", "3BDA_MOD", "3BDA_1", "MCI", "Kab1_Rrs",
    ]
    return df, indices


def _aoi_mask(src, aoi_path: Path) -> np.ndarray:
    gdf = gpd.read_file(aoi_path)
    if gdf.crs != src.crs:
        gdf = gdf.to_crs(src.crs)
    geom = gdf.geometry.union_all() if hasattr(gdf.geometry, "union_all") else gdf.geometry.unary_union
    return rasterize([(geom, 1)], out_shape=(src.height, src.width), transform=src.transform, fill=0, dtype="uint8").astype(bool)


def _preview_map(data: np.ndarray, bounds, label: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 7))
    masked = np.ma.masked_invalid(data)
    im = ax.imshow(masked, extent=[bounds.left, bounds.right, bounds.bottom, bounds.top], origin="upper")
    fig.colorbar(im, ax=ax, label=label)
    ax.set_title(f"AQUASMART — {label}")
    ax.set_xlabel("Coordenada X")
    ax.set_ylabel("Coordenada Y")
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def inferir_qualidade_agua(
    imagem_path: str | Path,
    aoi_path: str | Path,
    parametros: list[str] | None = None,
) -> dict:
    image_path = Path(imagem_path)
    aoi_path = Path(aoi_path)
    if not image_path.exists():
        raise FileNotFoundError(image_path)
    params = parametros or list(WATER_QUALITY_MODELS.keys())

    with rasterio.open(image_path) as src:
        descriptions = list(src.descriptions)
        # Preferir descrições das bandas; fallback para ordem esperada.
        band_indices = []
        for band in SENSOR_BANDS:
            if band in descriptions:
                band_indices.append(descriptions.index(band) + 1)
            else:
                band_indices = list(range(1, 9))
                break
        arr = src.read(band_indices).astype(np.float32)
        meta = src.meta.copy()
        bounds = src.bounds
        aoi_mask = _aoi_mask(src, aoi_path)

    if arr.shape[0] != 8:
        raise ValueError(f"São necessárias 8 bandas S2; raster possui {arr.shape[0]} selecionadas.")

    rows, cols = arr.shape[1:]
    flat = arr.reshape(8, -1).T
    df = pd.DataFrame(flat, columns=MODEL_BASE_FEATURES)
    valid = np.isfinite(flat).all(axis=1) & (flat > 0).all(axis=1)
    G, R, NIR = df["B3-560"], df["B4-665"], df["B8-842"]
    ndwi = (G - NIR) / (G + NIR + 1e-8)
    ndvi = (NIR - R) / (NIR + R + 1e-8)
    water = (ndwi > NDWI_THRESHOLD) & (ndvi < NDVI_THRESHOLD)
    final_mask = valid & water.to_numpy() & aoi_mask.reshape(-1)

    if int(final_mask.sum()) == 0:
        raise ValueError("Nenhum pixel de água válido foi encontrado dentro da AOI.")

    water_df = df.loc[final_mask].copy()
    water_df, indices = calculate_spectral_indices(water_df)
    water_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    water_df.fillna(0, inplace=True)
    expected_features = MODEL_BASE_FEATURES + indices

    results: dict[str, dict] = {}
    errors: dict[str, str] = {}
    out_dir = OUTPUT_DIR / "water_quality"
    out_dir.mkdir(parents=True, exist_ok=True)

    for param in params:
        model_path = WATER_QUALITY_MODELS.get(param)
        if model_path is None:
            errors[param] = "Parâmetro desconhecido."
            continue
        if not model_path.exists():
            errors[param] = f"Modelo não encontrado: {model_path}"
            continue
        try:
            model = joblib.load(model_path)
            names = list(getattr(model, "feature_names_in_", expected_features))
            missing = [c for c in names if c not in water_df.columns]
            if missing:
                raise ValueError(f"Features ausentes: {missing}")
            pred = np.asarray(model.predict(water_df[names]), dtype=np.float32)
            full = np.full(rows * cols, np.nan, dtype=np.float32)
            full[final_mask] = pred
            raster = full.reshape(rows, cols)

            out_tif = out_dir / f"{image_path.stem}_{param}.tif"
            out_png = out_dir / f"{image_path.stem}_{param}.png"
            out_meta = meta.copy()
            out_meta.update(count=1, dtype="float32", nodata=np.nan, compress="lzw")
            with rasterio.open(out_tif, "w", **out_meta) as dst:
                dst.write(raster, 1)
                dst.set_band_description(1, WATER_QUALITY_LABELS.get(param, param))
            _preview_map(raster, bounds, WATER_QUALITY_LABELS.get(param, param), out_png)

            results[param] = {
                "label": WATER_QUALITY_LABELS.get(param, param),
                "valid_pixels": int(pred.size),
                "mean": float(np.nanmean(pred)),
                "median": float(np.nanmedian(pred)),
                "min": float(np.nanmin(pred)),
                "max": float(np.nanmax(pred)),
                "raster_path": str(out_tif),
                "preview_path": str(out_png),
            }
        except Exception as exc:
            errors[param] = f"{type(exc).__name__}: {exc}"

    if not results:
        raise RuntimeError(f"Nenhum modelo de qualidade da água pôde ser executado. Erros: {errors}")

    return {
        "status": "success",
        "image": str(image_path),
        "aoi": str(aoi_path),
        "water_pixels": int(final_mask.sum()),
        "parameters": results,
        "parameter_errors": errors,
        "feature_count": len(expected_features),
        "reflectance_expected_range": "0..1",
    }
