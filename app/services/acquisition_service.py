"""Roteamento e fallback de fontes de aquisição."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.config import AUTO_SOURCE_ORDER, DATA_DIR, S1_CONTEXT_BUFFER_M
from app.services.aoi_service import criar_regiao_contexto


class SourceUnavailable(RuntimeError):
    pass


class SourceNotNormalized(RuntimeError):
    pass


def _gee(analysis_type: str, area: dict, start_date: str, end_date: str, orbit_pass: str | None, cloud_cover: float) -> dict:
    if analysis_type == "macrophytes":
        from acquisition.google_earth_engine.sentinel1_download import baixar_melhor_imagem
        export_area = criar_regiao_contexto(area, S1_CONTEXT_BUFFER_M)
        return baixar_melhor_imagem(
            area_busca=area,
            area_exportacao=export_area,
            data_inicio=start_date,
            data_fim=end_date,
            output_dir=DATA_DIR / "acquired" / "gee" / "sentinel1",
            orbit_pass=orbit_pass,
        )
    if analysis_type == "water_quality":
        from acquisition.google_earth_engine.sentinel2_download import baixar_melhor_imagem
        return baixar_melhor_imagem(
            area=area,
            data_inicio=start_date,
            data_fim=end_date,
            output_dir=DATA_DIR / "acquired" / "gee" / "sentinel2",
            cobertura_nuvens=cloud_cover,
        )
    raise ValueError(f"Tipo de análise inválido: {analysis_type}")


def _copernicus_discovery(analysis_type: str, area: dict, start_date: str, end_date: str, cloud_cover: float) -> dict:
    """Valida disponibilidade no CDSE.

    O catálogo funciona, mas os modelos atuais exigem rasters normalizados como
    os do GEE. Baixar o SAFE bruto e inferir diretamente seria tecnicamente
    incorreto. Por isso este adaptador sinaliza a necessidade de normalização,
    permitindo fallback seguro para GEE no modo automático/preferencial.
    """
    from acquisition.copernicus import conectar_catalogo, buscar_sentinel1, buscar_sentinel2
    catalog = conectar_catalogo()
    if analysis_type == "macrophytes":
        items = buscar_sentinel1(catalog, area, start_date, end_date, max_items=5)
    else:
        items = buscar_sentinel2(catalog, area, start_date, end_date, cobertura_nuvens=cloud_cover, max_items=5)
    if not items:
        raise SourceUnavailable("Copernicus Data Space não encontrou cenas compatíveis.")
    raise SourceNotNormalized(
        f"Copernicus encontrou {len(items)} cena(s), mas o adaptador SAFE→raster normalizado ainda não foi homologado para os modelos atuais."
    )


def adquirir(
    analysis_type: str,
    area: dict,
    start_date: str,
    end_date: str,
    source: str = "auto",
    preferred_source: str | None = None,
    allow_fallback: bool = True,
    orbit_pass: str | None = None,
    cloud_cover: float = 30,
    progress: Callable[[str, str], None] | None = None,
) -> dict:
    source = source.lower()
    attempts: list[dict] = []

    if source == "auto":
        order = list(AUTO_SOURCE_ORDER)
    elif source in {"gee", "copernicus"}:
        order = [source]
        if allow_fallback:
            order += [x for x in ["gee", "copernicus"] if x not in order]
    else:
        raise ValueError("source deve ser auto, gee ou copernicus.")

    if preferred_source in {"gee", "copernicus"} and preferred_source in order:
        order.remove(preferred_source)
        order.insert(0, preferred_source)

    for current in order:
        try:
            if progress:
                progress("acquisition", f"Tentando aquisição via {'Google Earth Engine' if current == 'gee' else 'Copernicus Data Space'}...")
            if current == "gee":
                result = _gee(analysis_type, area, start_date, end_date, orbit_pass, cloud_cover)
            else:
                result = _copernicus_discovery(analysis_type, area, start_date, end_date, cloud_cover)
            attempts.append({"source": current, "status": "success"})
            result["source_attempts"] = attempts
            return result
        except Exception as exc:
            attempts.append({"source": current, "status": "failed", "error": f"{type(exc).__name__}: {exc}"})
            if progress:
                progress("acquisition", f"Falha em {current}: {exc}")
            if not allow_fallback and source != "auto":
                raise

    raise RuntimeError(f"Nenhuma fonte conseguiu fornecer dado compatível. Tentativas: {attempts}")
