# Arquitetura do MVP

```text
React
  ↓
FastAPI / Jobs
  ↓
AquaSmartAgent
  ├─ AOIAgent
  ├─ AcquisitionAgent
  │    ├─ GEE adapter
  │    └─ Copernicus STAC adapter + fallback
  ├─ MacrophytesAgent → U-Net S1
  └─ WaterQualityAgent → modelos S2
  ↓
GeoTIFF + PNG + métricas + metadados
```

## Contrato de aquisição

Todo adaptador de fonte deve devolver pelo menos:

- `source`;
- `source_label`;
- `arquivo`;
- `datetime`;
- metadados da cena;
- `source_attempts` após o roteamento.

Essa separação permite trocar a fonte sem alterar o código dos modelos.

## Fallback

`source=auto` usa `AUTO_SOURCE_ORDER` do `.env`. Também é possível informar uma fonte preferida. Erros ficam registrados em `source_attempts`, dando rastreabilidade ao pesquisador.
