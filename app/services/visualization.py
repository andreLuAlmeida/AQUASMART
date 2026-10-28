from pathlib import Path

import geopandas as gpd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import ListedColormap
from rasterio.features import rasterize


def gerar_saida_aoi_e_preview(
    classification_path: str | Path,
    aoi_path: str | Path,
    output_aoi_path: str | Path,
    preview_path: str | Path,
) -> dict:
    """
    Gera:
    1. GeoTIFF classificado apenas dentro da AOI.
    2. PNG de preview com água, macrófitas e contorno da AOI.

    Classes:
        0 = background
        1 = water
        2 = plant
    """

    classification_path = Path(classification_path)
    aoi_path = Path(aoi_path)
    output_aoi_path = Path(output_aoi_path)
    preview_path = Path(preview_path)

    output_aoi_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.parent.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # 1. Abrir raster classificado
    # --------------------------------------------------
    with rasterio.open(classification_path) as src:
        pred = src.read(1)
        meta = src.meta.copy()
        raster_crs = src.crs
        transform = src.transform
        height = src.height
        width = src.width
        bounds = src.bounds

    # --------------------------------------------------
    # 2. Abrir AOI e reprojetar para o CRS do raster
    # --------------------------------------------------
    gdf = gpd.read_file(aoi_path)

    if gdf.empty:
        raise ValueError("AOI vazia.")

    if gdf.crs is None:
        raise ValueError("AOI não possui CRS.")

    if raster_crs is None:
        raise ValueError("Raster não possui CRS.")

    if gdf.crs != raster_crs:
        gdf = gdf.to_crs(raster_crs)

    # Em versões atuais do GeoPandas
    try:
        geom = gdf.geometry.union_all()
    except AttributeError:
        geom = gdf.geometry.unary_union

    # --------------------------------------------------
    # 3. Rasterizar AOI
    # --------------------------------------------------
    aoi_mask = rasterize(
        [(geom, 1)],
        out_shape=(height, width),
        transform=transform,
        fill=0,
        dtype=np.uint8,
    ).astype(bool)

    if not aoi_mask.any():
        raise ValueError("AOI não intersecta o raster.")

    # --------------------------------------------------
    # 4. Criar raster apenas dentro da AOI
    # --------------------------------------------------
    # 255 será NoData.
    pred_aoi = np.full(pred.shape, 255, dtype=np.uint8)
    pred_aoi[aoi_mask] = pred[aoi_mask]

    meta.update(
        count=1,
        dtype="uint8",
        nodata=255,
        compress="lzw",
    )

    with rasterio.open(output_aoi_path, "w", **meta) as dst:
        dst.write(pred_aoi, 1)
        dst.set_band_description(
            1,
            "class: 1=water,2=plant; outside AOI=nodata"
        )

    # --------------------------------------------------
    # 5. Preparar imagem para preview
    # --------------------------------------------------
    # Fora da AOI ficará mascarado/transparente.
    display = np.ma.masked_where(~aoi_mask, pred)

    # 0, 1, 2
    # Fundo, água, macrófitas
    cmap = ListedColormap([
        "white",
        "blue",
        "limegreen",
    ])

    # --------------------------------------------------
    # 6. Gerar PNG
    # --------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 10))

    ax.imshow(
        display,
        cmap=cmap,
        vmin=0,
        vmax=2,
        extent=[
            bounds.left,
            bounds.right,
            bounds.bottom,
            bounds.top,
        ],
        origin="upper",
    )

    # Contorno da lagoa.
    gdf.boundary.plot(
        ax=ax,
        edgecolor="black",
        linewidth=2,
    )

    ax.set_title("Classificação de macrófitas — Sentinel-1")
    ax.set_xlabel("Coordenada X")
    ax.set_ylabel("Coordenada Y")

    # Legenda manual
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="blue", label="Água"),
        Patch(facecolor="limegreen", label="Macrófitas"),
    ]

    ax.legend(
        handles=legend_elements,
        loc="upper right",
    )

    plt.tight_layout()
    plt.savefig(
        preview_path,
        dpi=180,
        bbox_inches="tight",
        transparent=False,
    )
    plt.close(fig)

    return {
        "classification_aoi_path": str(output_aoi_path),
        "preview_path": str(preview_path),
    }