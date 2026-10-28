# Resumo da implementação gerada

## Novos blocos

- frontend React/Vite;
- AOI por mapa, retângulo, coordenadas, GeoJSON, KML, Shapefile ZIP e AOI cadastrada;
- jobs assíncronos simples com progresso/polling;
- agente orquestrador e quatro agentes especializados;
- roteador de aquisição com tentativa/fallback;
- GEE Sentinel-1 com contexto espacial para U-Net;
- GEE Sentinel-2 com 8 bandas e escala de reflectância;
- serviço de qualidade da água com os quatro modelos enviados;
- outputs e URLs para GeoTIFF/PNG;
- testes de API/AOI e smoke test S1;
- documentação inicial e scripts de execução.

## Decisão sobre Copernicus

O STAC do CDSE foi mantido e integrado ao roteador. O produto Copernicus bruto não é enviado diretamente aos modelos, pois o Sentinel-1 validado usa a representação do GEE e os modelos Sentinel-2 esperam um raster padronizado. Enquanto o adaptador de normalização CDSE não for homologado, a tentativa Copernicus é registrada e o fluxo pode cair para GEE.

## Arquivos de modelo

- `models/macrofitas/model_best_unet2_s1_S1.pt`
- `models/water_quality/modelo_pred_Senti_chl_a.pkl`
- `models/water_quality/modelo_pred_Senti_turb_ntu.pkl`
- `models/water_quality/modelo_pred_Senti_secchi_cm.pkl`
- `models/water_quality/modelo_pred_Senti_pc_rfu.pkl`
