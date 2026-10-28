"""Agente especializado em qualidade da água."""
from app.tools.water_quality_tool import analyze_water_quality_tool


class WaterQualityAgent:
    name = "Water Quality Agent"

    def analyze(self, image_path, aoi_path, parameters=None):
        return analyze_water_quality_tool(image_path, aoi_path, parameters)
