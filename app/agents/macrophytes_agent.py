"""Agente especializado em macrófitas."""
from app.tools.macrofitas_tool import analyze_macrophytes_tool


class MacrophytesAgent:
    name = "Macrophytes Agent"

    def analyze(self, image_path, aoi_path):
        return analyze_macrophytes_tool(image_path, aoi_path)
