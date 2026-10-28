"""Configurações específicas do Google Earth Engine."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Raiz do projeto: .../busca_api_copernicus_e_google_earth
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

# Projeto Google Cloud habilitado para Google Earth Engine.
EE_PROJECT_ID = os.getenv("EE_PROJECT_ID")

# Valores usados quando os scripts são executados diretamente pelo terminal.
# Na API, datas e área chegam na própria requisição e substituem esses valores.
START_DATE = os.getenv("GEE_START_DATE", "2025-01-01")
END_DATE = os.getenv("GEE_END_DATE", "2025-02-01")
MAX_IMAGES = int(os.getenv("GEE_MAX_IMAGES", "1"))

# AOI padrão apenas para os scripts de teste executados diretamente.
AOI_COORDINATES = [[
    [-44.13685443383252, -20.043856862850852],
    [-44.08140780907666, -20.043856862850852],
    [-44.08140780907666, -19.99676073687553],
    [-44.13685443383252, -19.99676073687553],
    [-44.13685443383252, -20.043856862850852],
]]

# Saídas do Earth Engine.
SENTINEL1_OUTPUT_DIR = BASE_DIR / "outputs" / "sentinel1"
SENTINEL2_OUTPUT_DIR = BASE_DIR / "outputs" / "sentinel2"

# Sentinel-1.
S1_COLLECTION = "COPERNICUS/S1_GRD"
S1_TARGET_SCALE = 10
S1_INSTRUMENT_MODE = "IW"
S1_ORBIT_PASS = None
S1_REQUIRED_POLARIZATIONS = ["VV", "VH"]
S1_BAND_ORDER = ["VV", "VH", "HH", "HV", "angle"]

# Sentinel-2.
S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
S2_TARGET_SCALE = 10
S2_BAND_ORDER = [
    "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8",
    "B8A", "B9", "B11", "B12", "SCL", "QA10", "QA20", "QA60",
]
S2_BANDS_10M = {"B2", "B3", "B4", "B8"}
S2_BANDS_20M = {"B5", "B6", "B7", "B8A", "B11", "B12"}
S2_BANDS_60M = {"B1", "B9"}
S2_QA_BANDS = {"SCL", "QA10", "QA20", "QA60"}
