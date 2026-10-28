"""Tools de macrófitas."""
from app.config import DEFAULT_MODEL
from app.services.demo_service import analisar_cena_teste, listar_cenas_teste
from app.services.macrofitas import inferir_macrofitas

TOOL_DEFINITION = {
    "name": "analyze_macrophytes",
    "description": "Executa U-Net Sentinel-1 VV/VH e calcula cobertura de macrófitas dentro da AOI.",
}


def analyze_macrophytes_tool(image_path, aoi_path, output_path=None):
    return inferir_macrofitas(image_path, aoi_path, DEFAULT_MODEL, output_path)

# Compatibilidade da demo antiga.
def analisar_macrofitas_tool(image_index=0):
    return analisar_cena_teste(image_index)


def listar_cenas_tool():
    return listar_cenas_teste()
