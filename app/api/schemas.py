from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AgentRequest(BaseModel):
    message: str = Field(min_length=1)


class TestAnalysisRequest(BaseModel):
    image_index: int = Field(default=0, ge=0, le=1)


class AnalysisRequest(BaseModel):
    analysis_type: Literal["macrophytes", "water_quality"]
    source: Literal["auto", "gee", "copernicus"] = "auto"
    preferred_source: Literal["gee", "copernicus"] | None = None
    allow_fallback: bool = True
    start_date: str
    end_date: str
    aoi: dict
    orbit_pass: Literal["ASCENDING", "DESCENDING"] | None = None
    cloud_cover: float = Field(default=30, ge=0, le=100)
    parameters: list[Literal["chlorophyll_a", "turbidity_ntu", "secchi_cm", "pc_rfu"]] | None = None

    @model_validator(mode="after")
    def defaults_for_analysis(self):
        if self.analysis_type == "water_quality" and not self.parameters:
            self.parameters = ["chlorophyll_a", "turbidity_ntu", "secchi_cm", "pc_rfu"]
        return self
