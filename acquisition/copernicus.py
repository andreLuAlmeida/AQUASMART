"""Funções de consulta e download no Copernicus Data Space Ecosystem.

A consulta é feita pelo catálogo STAC. O download do produto completo usa o
asset ``Product`` retornado pelo catálogo e autenticação do CDSE.
"""

from pathlib import Path

import requests
from pystac_client import Client

from acquisition.config import (
    CDSE_PASSWORD,
    CDSE_USERNAME,
    COPERNICUS_DOWNLOAD_DIR,
    STAC_URL,
    TOKEN_URL,
)


def obter_token() -> str:
    """Obtém um token de acesso do Copernicus Data Space.

    O token só é necessário na etapa de download do produto completo.
    """
    if not CDSE_USERNAME or not CDSE_PASSWORD:
        raise RuntimeError(
            "CDSE_USERNAME e CDSE_PASSWORD não foram configurados no .env."
        )

    dados = {
        "client_id": "cdse-public",
        "grant_type": "password",
        "username": CDSE_USERNAME,
        "password": CDSE_PASSWORD,
    }

    resposta = requests.post(TOKEN_URL, data=dados, timeout=30)
    resposta.raise_for_status()

    token = resposta.json().get("access_token")
    if not token:
        raise RuntimeError("O CDSE não retornou access_token.")

    return token


def conectar_catalogo() -> Client:
    """Abre uma conexão com o catálogo STAC do CDSE."""
    return Client.open(STAC_URL)


def buscar_sentinel2(
    catalog: Client,
    area: dict,
    data_inicio: str,
    data_fim: str,
    cobertura_nuvens: float = 30,
    max_items: int = 10,
):
    """Busca produtos Sentinel-2 L2A que intersectam a área informada."""
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        intersects=area,
        datetime=f"{data_inicio}/{data_fim}",
        query={"eo:cloud_cover": {"lte": cobertura_nuvens}},
        max_items=max_items,
    )
    return list(search.items())


def buscar_sentinel1(
    catalog: Client,
    area: dict,
    data_inicio: str,
    data_fim: str,
    max_items: int = 10,
):
    """Busca produtos Sentinel-1 GRD que intersectam a área informada."""
    search = catalog.search(
        collections=["sentinel-1-grd"],
        intersects=area,
        datetime=f"{data_inicio}/{data_fim}",
        max_items=max_items,
    )
    return list(search.items())


def serializar_sentinel2(item) -> dict:
    """Converte um STAC Item Sentinel-2 em um dicionário serializável."""
    return {
        "id": item.id,
        "collection": item.collection_id,
        "datetime": item.properties.get("datetime"),
        "cloud_cover": item.properties.get("eo:cloud_cover"),
        "assets": {nome: asset.href for nome, asset in item.assets.items()},
    }


def serializar_sentinel1(item) -> dict:
    """Converte um STAC Item Sentinel-1 em um dicionário serializável."""
    return {
        "id": item.id,
        "collection": item.collection_id,
        "datetime": item.properties.get("datetime"),
        "instrument_mode": item.properties.get("sar:instrument_mode"),
        "orbit_state": item.properties.get("sat:orbit_state"),
        "polarizations": item.properties.get("sar:polarizations"),
        "assets": {nome: asset.href for nome, asset in item.assets.items()},
    }


def obter_url_produto(item) -> str:
    """Retorna a URL do asset ``Product`` de um STAC Item."""
    asset = item.assets.get("Product")
    if asset is None:
        raise ValueError(f"O item {item.id} não possui o asset 'Product'.")
    return asset.href


def baixar_produto(item, token: str, pasta_destino=None) -> str:
    """Baixa o produto completo do CDSE em modo streaming.

    O arquivo é salvo como ZIP porque o asset Product representa o pacote
    completo disponibilizado pelo CDSE.
    """
    url = obter_url_produto(item)
    pasta = Path(pasta_destino or COPERNICUS_DOWNLOAD_DIR)
    pasta.mkdir(parents=True, exist_ok=True)

    caminho_saida = pasta / f"{item.id}.zip"
    headers = {"Authorization": f"Bearer {token}"}

    with requests.get(
        url,
        headers=headers,
        stream=True,
        timeout=300,
        allow_redirects=True,
    ) as resposta:
        resposta.raise_for_status()

        with caminho_saida.open("wb") as arquivo:
            for bloco in resposta.iter_content(chunk_size=1024 * 1024):
                if bloco:
                    arquivo.write(bloco)

    return str(caminho_saida)
