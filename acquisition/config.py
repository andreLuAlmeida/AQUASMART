"""Configurações gerais da integração com o Copernicus Data Space.

Este módulo concentra URLs e credenciais da fonte Copernicus. As credenciais
são lidas do arquivo ``.env`` para que não fiquem escritas no código-fonte.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Diretório raiz do projeto. Usar caminho absoluto evita problemas quando a
# aplicação é iniciada a partir de outro diretório.
BASE_DIR = Path(__file__).resolve().parents[1]

# Carrega explicitamente o .env localizado na raiz do projeto.
load_dotenv(BASE_DIR / ".env")

# Catálogo STAC do Copernicus Data Space Ecosystem (CDSE).
STAC_URL = "https://stac.dataspace.copernicus.eu/v1/"

# Endpoint usado para obter um token de acesso ao download de produtos.
TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/"
    "auth/realms/CDSE/protocol/openid-connect/token"
)

# Credenciais do usuário CDSE. Elas só são necessárias para download do
# produto completo. A consulta STAC em si pode ser feita sem essas variáveis.
CDSE_USERNAME = os.getenv("CDSE_USERNAME")
CDSE_PASSWORD = os.getenv("CDSE_PASSWORD")

# Diretório onde os produtos completos baixados via Copernicus são salvos.
COPERNICUS_DOWNLOAD_DIR = BASE_DIR / "data" / "acquired" / "copernicus"
