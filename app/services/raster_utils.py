"""Validação e inspeção de rasters Sentinel-1."""
from pathlib import Path
import rasterio

EXPECTED_S1_BANDS = ("VV", "VH")


def inspect_raster(path: str | Path) -> dict:
    path = Path(path)
    with rasterio.open(path) as src:
        return {
            "path": str(path),
            "count": src.count,
            "width": src.width,
            "height": src.height,
            "crs": str(src.crs),
            "resolution": [abs(src.res[0]), abs(src.res[1])],
            "dtype": list(src.dtypes),
            "descriptions": list(src.descriptions),
            "bounds": [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top],
        }


def read_vv_vh(src) -> tuple:
    """Retorna VV/VH explicitamente nessa ordem e informa índices utilizados."""
    descriptions = [d.upper() if d else None for d in src.descriptions]
    try:
        vv_idx = descriptions.index("VV") + 1
        vh_idx = descriptions.index("VH") + 1
    except ValueError as exc:
        raise ValueError(
            f"Raster sem descrições VV/VH reconhecíveis. Bandas: {src.descriptions}"
        ) from exc
    return src.read([vv_idx, vh_idx]).astype("float32"), (vv_idx, vh_idx)
