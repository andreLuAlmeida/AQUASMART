"""Valida arquivos, raster, AOI e checkpoint sem precisar executar inferência."""
from pathlib import Path
import sys
import torch
import geopandas as gpd
from app.config import DEFAULT_AOI, DEFAULT_MODEL, TEST_IMAGES
from app.services.raster_utils import inspect_raster

ok = True
print("=== AQUASMART setup check ===")
print("Python:", sys.version.split()[0])
print("Torch:", torch.__version__, "CUDA:", torch.cuda.is_available())

print("\nModelo:", DEFAULT_MODEL, DEFAULT_MODEL.exists())
if DEFAULT_MODEL.exists():
    obj = torch.load(DEFAULT_MODEL, map_location="cpu")
    state = obj.get("model_state_dict", obj) if isinstance(obj, dict) else obj
    print("Checkpoint tipo:", type(obj).__name__, "parâmetros:", len(state))
    if "encoder.conv1.weight" in state:
        print("Primeira camada:", tuple(state["encoder.conv1.weight"].shape), "(esperado: 64,2,7,7)")

print("\nAOI:", DEFAULT_AOI, DEFAULT_AOI.exists())
if DEFAULT_AOI.exists():
    gdf = gpd.read_file(DEFAULT_AOI)
    print("AOI CRS:", gdf.crs, "geometrias:", len(gdf), "bounds:", list(gdf.total_bounds))

print("\nCenas de teste:", len(TEST_IMAGES))
for p in TEST_IMAGES:
    info = inspect_raster(p)
    print("-", Path(p).name)
    print("  bands:", info["descriptions"], "crs:", info["crs"], "res:", info["resolution"], "shape:", (info["height"], info["width"]))
    if info["descriptions"][:2] != ["VV", "VH"]:
        ok = False
        print("  ERRO: primeiras bandas não são VV/VH")

try:
    import segmentation_models_pytorch as smp  # noqa
    print("\nsegmentation_models_pytorch: OK")
except Exception as exc:
    ok = False
    print("\nsegmentation_models_pytorch: AUSENTE -> pip install -r requirements.txt")

print("\nResultado estrutural:", "OK" if ok else "ATENÇÃO: ver mensagens acima")
