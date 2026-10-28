"""Agente de aquisição e fallback de fontes."""
from app.tools.acquisition_tool import acquire_satellite_image_tool


class AcquisitionAgent:
    name = "Acquisition Agent"

    def acquire(self, **kwargs):
        return acquire_satellite_image_tool(**kwargs)
