"""Orquestrador principal do AQUASMART.

Não depende de um LLM: as decisões são determinísticas e auditáveis. A camada
foi desenhada como agente→tool para permitir function calling posteriormente
sem alterar os serviços geoespaciais/modelos.
"""
from __future__ import annotations

from typing import Callable

from app.agents.aoi_agent import AOIAgent
from app.agents.acquisition_agent import AcquisitionAgent
from app.agents.macrophytes_agent import MacrophytesAgent
from app.agents.water_quality_agent import WaterQualityAgent
from app.services.result_utils import enrich_output_urls


class AquaSmartAgent:
    name = "AQUASMART Orchestrator"

    def __init__(self):
        self.aoi_agent = AOIAgent()
        self.acquisition_agent = AcquisitionAgent()
        self.macrophytes_agent = MacrophytesAgent()
        self.water_quality_agent = WaterQualityAgent()

    def analyze(self, request: dict, progress: Callable[[str, str, int], None] | None = None) -> dict:
        def emit(stage: str, message: str, pct: int):
            if progress:
                progress(stage, message, pct)

        analysis_type = request["analysis_type"]
        emit("aoi", "Validando área de estudo...", 10)
        prepared_aoi = self.aoi_agent.prepare(request["aoi"])

        emit("acquisition", "Buscando imagem de satélite...", 20)
        acquisition = self.acquisition_agent.acquire(
            analysis_type=analysis_type,
            area=prepared_aoi["geometry"],
            start_date=request["start_date"],
            end_date=request["end_date"],
            source=request.get("source", "auto"),
            preferred_source=request.get("preferred_source"),
            allow_fallback=request.get("allow_fallback", True),
            orbit_pass=request.get("orbit_pass"),
            cloud_cover=request.get("cloud_cover", 30),
            progress=lambda s, m: emit(s, m, 35),
        )

        emit("inference", "Executando modelo de inteligência artificial...", 55)
        if analysis_type == "macrophytes":
            analysis = self.macrophytes_agent.analyze(acquisition["arquivo"], prepared_aoi["path"])
        elif analysis_type == "water_quality":
            analysis = self.water_quality_agent.analyze(
                acquisition["arquivo"], prepared_aoi["path"], request.get("parameters")
            )
        else:
            raise ValueError("analysis_type deve ser macrophytes ou water_quality.")

        emit("outputs", "Preparando mapas, métricas e downloads...", 90)
        response = {
            "status": "success",
            "agent": self.name,
            "analysis_type": analysis_type,
            "aoi": prepared_aoi["summary"],
            "acquisition": acquisition,
            "analysis": analysis,
        }
        emit("done", "Análise concluída.", 100)
        return enrich_output_urls(response)

    def run(self, message: str) -> dict:
        """Mantém o endpoint textual legado para demonstração de tool routing."""
        from app.tools.macrofitas_tool import analisar_macrofitas_tool, listar_cenas_tool
        text = message.lower().strip()
        if any(k in text for k in ["listar", "cenas", "imagens", "disponíveis", "disponiveis"]):
            return {"status": "success", "agent": self.name, "selected_tool": "listar_cenas", "tool_result": listar_cenas_tool()}
        if any(k in text for k in ["macrófit", "macrofit", "planta", "cobertura"]):
            idx = 1 if any(k in text for k in ["segunda", "imagem 2", "cena 2"]) else 0
            return {"status": "success", "agent": self.name, "selected_tool": "analisar_macrofitas", "tool_result": analisar_macrofitas_tool(idx)}
        return {
            "status": "needs_clarification",
            "agent": self.name,
            "message": "Use a interface estruturada para novas análises ou peça para listar/analisar cenas de teste.",
        }
