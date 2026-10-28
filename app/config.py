"""Configuração central do AQUASMART MVP."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "outputs"
MODEL_DIR = ROOT_DIR / "models"
TEMP_DIR = DATA_DIR / "runtime"

DEFAULT_MODEL = MODEL_DIR / "macrofitas" / "model_best_unet2_s1_S1.pt"
DEFAULT_AOI = DATA_DIR / "aoi" / "lagoa_regap_vetorizado2025.shp"
TEST_IMAGES = sorted((DATA_DIR / "test").glob("*.tif"))

WATER_QUALITY_MODELS = {
    "chlorophyll_a": MODEL_DIR / "water_quality" / "modelo_pred_Senti_chl_a.pkl",
    "turbidity_ntu": MODEL_DIR / "water_quality" / "modelo_pred_Senti_turb_ntu.pkl",
    "secchi_cm": MODEL_DIR / "water_quality" / "modelo_pred_Senti_secchi_cm.pkl",
    "pc_rfu": MODEL_DIR / "water_quality" / "modelo_pred_Senti_pc_rfu.pkl",
}

WATER_QUALITY_LABELS = {
    "chlorophyll_a": "Clorofila-a",
    "turbidity_ntu": "Turbidez",
    "secchi_cm": "Transparência Secchi",
    "pc_rfu": "PC/RFU",
}

PATCH_SIZE = 128
STRIDE = 64
BATCH_SIZE = int(os.getenv("AQUASMART_BATCH_SIZE", "8"))
IN_CHANNELS = 2
NUM_CLASSES = 3

# Contexto espacial é importante para a U-Net S1. A AOI é expandida antes da
# aquisição, mas as métricas continuam sendo calculadas somente na AOI original.
S1_CONTEXT_BUFFER_M = float(os.getenv("S1_CONTEXT_BUFFER_M", "2000"))

# A fonte automática prioriza o GEE enquanto o adaptador de normalização de
# produtos SAFE do Copernicus não estiver homologado para os modelos atuais.
# Pode ser alterado no .env: AUTO_SOURCE_ORDER=copernicus,gee
AUTO_SOURCE_ORDER = [
    x.strip().lower()
    for x in os.getenv("AUTO_SOURCE_ORDER", "gee,copernicus").split(",")
    if x.strip()
]

for _path in [OUTPUT_DIR, TEMP_DIR]:
    _path.mkdir(parents=True, exist_ok=True)
