# AQUASMART — MVP implementado

## Escopo

O MVP possui frontend React/Vite e backend FastAPI. O frontend permite selecionar macrófitas (Sentinel-1) ou qualidade da água (Sentinel-2), período, origem de dados e AOI.

## AOI suportada

- desenho de polígono no mapa;
- desenho de retângulo;
- bounding box por coordenadas;
- GeoJSON/JSON;
- KML;
- Shapefile compactado em ZIP;
- AOI cadastrada (Lagoa REGAP).

## Agentes

- `AquaSmartAgent`: orquestrador;
- `AOIAgent`: valida e materializa a AOI;
- `AcquisitionAgent`: seleciona a fonte e aplica fallback;
- `MacrophytesAgent`: executa a U-Net Sentinel-1;
- `WaterQualityAgent`: executa os modelos Sentinel-2.

Os agentes chamam `tools`, e os `tools` chamam serviços determinísticos. Não há dependência de LLM para o MVP.

## Fontes de dados

### Google Earth Engine

Implementado de ponta a ponta para Sentinel-1 e Sentinel-2.

### Copernicus Data Space

A busca STAC está implementada. O sistema detecta cenas no CDSE, mas não envia um produto SAFE bruto diretamente aos modelos, pois isso não seria equivalente aos rasters usados na validação. Em modo automático/preferencial, a tentativa é registrada e o fluxo pode fazer fallback para GEE.

Quando o adaptador SAFE/COG/Sentinel Hub for homologado, ele deve implementar o mesmo contrato de saída de `acquisition_service.py`.

## Modelos

### Sentinel-1

U-Net ResNet34, entrada VV/VH, classes fundo/água/macrófitas, patches 128 e stride 64.

### Sentinel-2

Oito bandas (`B2,B3,B4,B5,B6,B7,B8,B8A`) em reflectância 0..1, seguidas pelos índices espectrais do script de referência. O serviço executa os quatro modelos disponíveis, isolando falhas por parâmetro.

## API principal

- `GET /api/health`
- `GET /api/capabilities`
- `GET /api/aoi/default`
- `POST /api/jobs`
- `GET /api/jobs/{id}`
- `POST /api/analysis` (síncrono, útil para debug)
- `POST /api/agent/run` (legado/demonstração de roteamento textual)

## Desenvolvimento

Backend:

```bash
uvicorn main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Acesse `http://localhost:5173`.
