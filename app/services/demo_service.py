"""Serviço de alto nível usado pela API e pelo agente."""
from pathlib import Path
from app.config import DEFAULT_AOI, DEFAULT_MODEL, TEST_IMAGES, ROOT_DIR
from app.services.macrofitas import inferir_macrofitas
from app.services.raster_utils import inspect_raster


def listar_cenas_teste() -> list[dict]:
    return [inspect_raster(p) for p in TEST_IMAGES]


def analisar_cena_teste(image_index: int = 0) -> dict:
    if not TEST_IMAGES:
        raise FileNotFoundError("Nenhuma cena de teste encontrada em data/test.")
    if image_index < 0 or image_index >= len(TEST_IMAGES):
        raise IndexError(f"image_index inválido. Disponíveis: 0..{len(TEST_IMAGES)-1}")
    image = TEST_IMAGES[image_index]
    out = ROOT_DIR / "outputs" / "classifications" / f"{image.stem}_macrofitas.tif"
    return inferir_macrofitas(image, DEFAULT_AOI, DEFAULT_MODEL, out)
