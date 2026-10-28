"""Verificação rápida do MVP AQUASMART."""
from pathlib import Path
import importlib.util

from app.config import DEFAULT_AOI, DEFAULT_MODEL, WATER_QUALITY_MODELS

print('=== AQUASMART MVP CHECK ===')
print('AOI padrão:', DEFAULT_AOI, DEFAULT_AOI.exists())
print('Modelo S1:', DEFAULT_MODEL, DEFAULT_MODEL.exists())
for name, path in WATER_QUALITY_MODELS.items():
    print(f'Modelo S2 {name}:', path.exists(), path)
print('earthengine-api:', bool(importlib.util.find_spec('ee')))
print('segmentation_models_pytorch:', bool(importlib.util.find_spec('segmentation_models_pytorch')))
print('cubist:', bool(importlib.util.find_spec('cubist')))
print('FastAPI:', bool(importlib.util.find_spec('fastapi')))
print('Frontend package.json:', Path('frontend/package.json').exists())
