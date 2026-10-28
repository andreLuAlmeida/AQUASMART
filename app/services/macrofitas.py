"""Inferência de macrófitas em Sentinel-1 VV/VH.

Adaptado do script de inferência recebido: U-Net ResNet34, patches 128,
stride 64, blending por janela de Hann, classes 0=fundo, 1=água, 2=planta.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
import geopandas as gpd
from shapely.ops import unary_union
import torch
import torch.nn.functional as F

from app.services.visualization import gerar_saida_aoi_e_preview

from app.config import PATCH_SIZE, STRIDE, BATCH_SIZE, IN_CHANNELS, NUM_CLASSES, OUTPUT_DIR
from app.models.unet_s1 import build_unet_s1
from app.services.raster_utils import read_vv_vh


def _hann2d(h: int, w: int) -> np.ndarray:
    wy, wx = np.hanning(h), np.hanning(w)
    w2d = np.outer(wy, wx).astype(np.float32)
    return w2d / (w2d.max() + 1e-8)

WEIGHT_2D = _hann2d(PATCH_SIZE, PATCH_SIZE)[None, ...]


def _compute_pad(h: int, w: int, size: int, stride: int) -> tuple[int, int]:
    return ((-(h-size) % stride) % stride, (-(w-size) % stride) % stride)


def _sliding_window(arr: np.ndarray, size: int, stride: int, batch_size: int):
    _, h, w = arr.shape
    pad_h, pad_w = _compute_pad(h, w, size, stride)
    arr_pad = np.pad(arr, ((0,0),(0,pad_h),(0,pad_w)), mode="reflect")
    h2, w2 = arr_pad.shape[1:]
    patches, coords = [], []
    for i in range(0, h2-size+1, stride):
        for j in range(0, w2-size+1, stride):
            patches.append(arr_pad[:, i:i+size, j:j+size])
            coords.append((i,j))
            if len(patches) == batch_size:
                yield np.stack(patches), coords
                patches, coords = [], []
    if patches:
        yield np.stack(patches), coords


def _load_aoi_mask(src, aoi_path: str | Path) -> np.ndarray:
    gdf = gpd.read_file(aoi_path)
    if gdf.empty:
        raise ValueError("AOI vazia.")
    if gdf.crs is None:
        raise ValueError("AOI sem CRS definido.")
    if src.crs is None:
        raise ValueError("Raster sem CRS definido.")
    if gdf.crs != src.crs:
        gdf = gdf.to_crs(src.crs)
    try:
        geom = unary_union(list(gdf.geometry))
    except Exception:
        geom = gdf.unary_union
    mask = rasterize(
        [(geom, 1)], out_shape=(src.height, src.width), transform=src.transform,
        fill=0, dtype=np.uint8,
    ).astype(bool)
    if not mask.any():
        raise ValueError("A AOI não intersecta o raster após reprojeção.")
    return mask


def load_model(model_path: str | Path, device: torch.device):
    model = build_unet_s1(IN_CHANNELS, NUM_CLASSES).to(device)
    state = torch.load(model_path, map_location=device)
    if isinstance(state, dict) and "model_state_dict" in state:
        state = state["model_state_dict"]
    model.load_state_dict(state)
    model.eval()
    return model


def _save_classification(pred: np.ndarray, src_meta: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    meta = src_meta.copy()
    meta.update(count=1, dtype="uint8", nodata=0, compress="lzw")
    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(pred.astype(np.uint8), 1)
        dst.set_band_description(1, "class: 0=background,1=water,2=plant")


@torch.no_grad()
def inferir_macrofitas(
    imagem_path: str | Path,
    aoi_path: str | Path,
    modelo_path: str | Path,
    output_path: str | Path | None = None,
) -> dict:
    imagem_path, aoi_path, modelo_path = map(Path, (imagem_path, aoi_path, modelo_path))
    for p, nome in [(imagem_path, "imagem"), (aoi_path, "AOI"), (modelo_path, "modelo")]:
        if not p.exists():
            raise FileNotFoundError(f"{nome} não encontrado: {p}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(modelo_path, device)

    with rasterio.open(imagem_path) as src:
        img, band_indexes = read_vv_vh(src)
        transform, crs = src.transform, src.crs
        meta = src.meta.copy()
        aoi_mask = _load_aoi_mask(src, aoi_path)
        # Este cálculo só é área em m² quando o raster usa CRS projetado em metros.
        px_area = abs(transform.a * transform.e)

    _, h, w = img.shape
    pred_sum = np.zeros((NUM_CLASSES, h, w), dtype=np.float32)
    weight_sum = np.zeros((h, w), dtype=np.float32)

    for batch, coords in _sliding_window(img, PATCH_SIZE, STRIDE, BATCH_SIZE):
        x = torch.from_numpy(batch).to(device)
        logits = model(x)
        probs = F.softmax(logits, dim=1).float().cpu().numpy()
        probs *= WEIGHT_2D
        for k, (i, j) in enumerate(coords):
            i0, j0 = min(i, h-1), min(j, w-1)
            i1, j1 = min(i0+PATCH_SIZE, h), min(j0+PATCH_SIZE, w)
            hh, ww = i1-i0, j1-j0
            sub_aoi = aoi_mask[i0:i1, j0:j1]
            probs[k, 0, :hh, :ww][sub_aoi] = 0.0
            pred_sum[:, i0:i1, j0:j1] += probs[k, :, :hh, :ww]
            weight_sum[i0:i1, j0:j1] += WEIGHT_2D[0, :hh, :ww]

    avg_probs = pred_sum / np.maximum(weight_sum, 1e-6)
    pred = np.argmax(avg_probs, axis=0).astype(np.uint8)

    aoi_pixels = int(aoi_mask.sum())
    plant_pixels = int((pred == 2)[aoi_mask].sum())
    water_pixels = int((pred == 1)[aoi_mask].sum())
    plant_pct = plant_pixels / max(1, aoi_pixels) * 100.0
    plant_area_m2 = plant_pixels * px_area

    if output_path is None:
        output_path = OUTPUT_DIR / "classifications" / f"{imagem_path.stem}_macrofitas.tif"
    output_path = Path(output_path)
    _save_classification(pred, meta, output_path)

    output_aoi_path = (
        OUTPUT_DIR / "classifications"
        / f"{imagem_path.stem}_macrofitas_AOI.tif"
    )

    preview_path = (
        OUTPUT_DIR / "previews"
        / f"{imagem_path.stem}_macrofitas_preview.png"
    )

    visual_outputs = gerar_saida_aoi_e_preview(
        classification_path=output_path,
        aoi_path=aoi_path,
        output_aoi_path=output_aoi_path,
        preview_path=preview_path,
    )

    return {
        "status": "success",
        "image": str(imagem_path),
        "model": str(modelo_path),
        "aoi": str(aoi_path),
        "device": str(device),
        "input_band_indexes": list(band_indexes),
        "input_band_order": ["VV", "VH"],
        "classes": {"0": "background", "1": "water", "2": "plant"},
        "aoi_pixels": aoi_pixels,
        "water_pixels": water_pixels,
        "plant_pixels": plant_pixels,
        "plant_pct": float(plant_pct),
        "plant_area_m2": float(plant_area_m2),
        "pixel_area_m2": float(px_area),
        "crs": str(crs),
        "classification_path": str(output_path),
        "classification_aoi_path": visual_outputs["classification_aoi_path"],
        "preview_path": visual_outputs["preview_path"],
    }
