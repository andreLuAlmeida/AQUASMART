# Arquitetura resumida

```text
Usuário
  |
  v
AQUASMART Agent
  |
  | escolhe uma tool
  v
analisar_macrofitas_tool
  |
  v
serviço de análise
  |
  +--> raster Sentinel-1 -> seleciona VV/VH
  +--> AOI -> reprojeta/rasteriza
  +--> checkpoint -> U-Net ResNet34
  |
  v
sliding window 128x128 / stride 64 / Hann blending
  |
  v
classes 0=fundo, 1=água, 2=planta
  |
  v
métricas dentro da AOI + GeoTIFF classificado
  |
  v
resultado estruturado -> agente
```

A fronteira `tool -> serviço` é deliberada: processamento geoespacial e inferência são determinísticos; o agente apenas decide qual capacidade chamar e apresenta o resultado.
