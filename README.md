# AQUASMART — demonstração integrada de geoprocessamento + agente

Entrega de demonstração preparada para conectar **aquisição de imagens Sentinel**, **processamento geoespacial**, **inferência de macrófitas com U-Net** e uma **camada de agente/tool**.

> Estado desta entrega: o fluxo Sentinel-1 está organizado para rodar de ponta a ponta com as duas imagens de teste fornecidas. A aquisição Copernicus/GEE permanece incluída como módulo separado. O agente atual usa roteamento determinístico para que a demonstração funcione sem chave de LLM; a fronteira de tools já está pronta para posteriormente ser substituída por function/tool calling de um LLM.

## 1. O que já está incluído

A entrega contém:

- checkpoint atual `model_best_unet2_s1_S1.pt`;
- duas imagens Sentinel-1 exportadas do Google Earth Engine;
- shapefile da lagoa REGAP;
- inferência U-Net adaptada para função reutilizável;
- seleção explícita das bandas **VV e VH**, nessa ordem;
- reprojeção automática da AOI para o CRS do raster;
- rasterização da AOI;
- inferência em patches `128 x 128`, `stride=64` e blending por janela de Hann;
- classes `0=fundo`, `1=água`, `2=planta`;
- cálculo de pixels, percentual e área de macrófitas dentro da AOI;
- geração de GeoTIFF classificado;
- FastAPI com Swagger;
- tool `analisar_macrofitas`;
- agente demonstrativo que escolhe entre listar cenas e executar a análise;
- código-base anterior de aquisição via **Copernicus Data Space** e **Google Earth Engine**;
- scripts originais recebidos em `docs/reference/` para rastreabilidade.

O colega informou que o modelo Sentinel-1 está sendo refeito, mas que a arquitetura continuará sendo U-Net e a troca será apenas dos pesos. Por isso o caminho do checkpoint está isolado em `app/config.py`: ao receber o novo `.pt`, basta substituir o arquivo atual, desde que a arquitetura/contrato realmente permaneça compatível.

---

## 2. Estrutura de pastas

```text
AQUASMART_entrega_2026-09-30/
|
|-- main.py                      # entrada da API FastAPI
|-- check_setup.py               # valida ambiente, arquivos, raster e checkpoint
|-- test_raster_aoi.py           # teste rápido de raster/AOI sem carregar U-Net
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- README.md
|
|-- app/
|   |-- config.py                # caminhos e hiperparâmetros centrais
|   |
|   |-- agents/
|   |   `-- aquasmart_agent.py   # orquestra tools da demo
|   |
|   |-- api/
|   |   |-- routes.py            # endpoints HTTP
|   |   `-- schemas.py           # schemas Pydantic
|   |
|   |-- models/
|   |   `-- unet_s1.py           # arquitetura U-Net ResNet34
|   |
|   |-- services/
|   |   |-- macrofitas.py        # núcleo da inferência S1
|   |   |-- raster_utils.py      # inspeção/seleção VV-VH
|   |   `-- demo_service.py      # serviço de alto nível usado por API/tool
|   |
|   `-- tools/
|       `-- macrofitas_tool.py    # ponte agente -> serviço
|
|-- acquisition/
|   |-- copernicus.py             # código-base CDSE/STAC
|   |-- config.py
|   |-- exemplo.area.geojson
|   `-- google_earth_engine/
|       |-- auth.py
|       |-- common.py
|       |-- config.py
|       |-- sentinel1_download.py
|       `-- sentinel2_download.py
|
|-- data/
|   |-- aoi/                      # shapefile completo da lagoa
|   `-- test/                     # duas cenas S1 fornecidas pelo grupo
|
|-- models/
|   `-- macrofitas/
|       `-- model_best_unet2_s1_S1.pt
|
|-- outputs/
|   |-- classifications/          # GeoTIFFs classificados gerados
|   `-- previews/                 # reservado para visualizações
|
`-- docs/
    |-- ARQUITETURA.md
    `-- reference/                # códigos originais recebidos
```

---

## 3. Fluxo de dados

### Pipeline Sentinel-1

```text
imagem Sentinel-1
        |
        v
validação de metadados
        |
        v
seleção explícita VV + VH
        |
        v
array [2, H, W]
        |
        +------------------------+
        |                        |
        v                        v
AOI vetorial               U-Net ResNet34
        |                        |
reprojeção p/ CRS raster        |
        |                        |
rasterização                    |
        |                        |
        +-----------+------------+
                    |
                    v
          sliding window 128x128
             stride 64
          blending de Hann
                    |
                    v
         mapa de classes por pixel
        0=fundo 1=água 2=planta
                    |
                    v
          métricas apenas na AOI
                    |
        +-----------+-----------+
        |           |           |
        v           v           v
 plant_pixels   plant_pct   plant_area_m2
                    |
                    v
            GeoTIFF classificado
```

### Por que VV/VH são selecionados explicitamente

As imagens de teste possuem 3 bandas: `VV`, `VH` e `angle`. O modelo Sentinel-1 foi treinado com **2 canais: VV e VH**. Em vez de simplesmente pegar as duas primeiras bandas sem verificar, `raster_utils.py` procura as descrições das bandas e lê explicitamente `VV` e `VH` nessa ordem.

Isso reduz o risco de uma imagem futura chegar com ordem diferente e ser enviada silenciosamente ao modelo de forma incorreta.

### AOI e CRS

A AOI da lagoa está em um CRS e os rasters podem estar em outro. Antes da criação da máscara, o código:

1. abre o shapefile com GeoPandas;
2. verifica se possui CRS;
3. reprojeta a AOI para `src.crs` do raster;
4. rasteriza o polígono usando `src.transform` e as dimensões da imagem;
5. valida se há interseção efetiva.

As métricas são calculadas **somente dentro dessa máscara**.

---

## 4. Workflow x agente

O processamento geoespacial não fica dentro do prompt do agente.

```text
Usuário
  |
  v
Agente AQUASMART
  |
  | escolhe capacidade
  v
Tool
  |
  v
Service Python
  |
  v
Raster + modelo + métricas
  |
  v
resultado estruturado
  |
  v
Agente / API apresenta resultado
```

A separação tem um objetivo simples:

- **agente:** decide qual capacidade deve ser usada;
- **tool:** contrato entre agente e código;
- **service:** executa regras determinísticas;
- **modelo:** faz a classificação;
- **API:** expõe as capacidades para outros sistemas.

### Agente incluído nesta entrega

Para evitar que a demonstração dependa de credenciais externas, `AquaSmartAgent` faz roteamento determinístico de duas intenções:

- listar cenas Sentinel-1 disponíveis;
- analisar macrófitas na primeira ou segunda cena.

Exemplos:

```text
Liste as imagens Sentinel-1 disponíveis.
Analise as macrófitas da primeira imagem.
Analise as macrófitas da segunda imagem.
```

O ponto importante para evolução é que o agente **não chama Rasterio/PyTorch diretamente**. Ele chama `analisar_macrofitas_tool()`. Portanto, em uma próxima etapa, o roteador determinístico pode ser substituído por um LLM com tool/function calling sem reescrever a inferência.

---

## 5. Como abrir no WSL

### 5.1 Copiar o ZIP para uma pasta conhecida

Se o arquivo estiver em `C:\Users\andre\Downloads`, no WSL:

```bash
cd ~
mkdir -p projetos
cd projetos
cp "/mnt/c/Users/andre/Downloads/AQUASMART_entrega_2026-09-30.zip" .
unzip AQUASMART_entrega_2026-09-30.zip
cd AQUASMART_entrega_2026-09-30
```

Para abrir no VS Code usando WSL:

```bash
code .
```

Se `code` não for reconhecido, abra o VS Code no Windows, instale a extensão **WSL** e use `WSL: Open Folder in WSL`.

---

## 6. Criar ambiente Python

Recomendado: Python 3.11 ou 3.12.

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

A instalação de `torch`, `geopandas`, `rasterio`, `geemap` e `segmentation-models-pytorch` pode demorar. Para a demonstração Sentinel-1, Earth Engine e Copernicus não precisam estar autenticados porque as duas imagens de teste já estão no ZIP.

Se o download de pacotes falhar por timeout:

```bash
pip install -r requirements.txt --resume-retries 10
```

---

## 7. Primeiro teste: validar a estrutura

Com `.venv` ativo:

```bash
python check_setup.py
```

Você deve ver informações parecidas com:

```text
Modelo: ... True
Primeira camada: (64, 2, 7, 7)
AOI CRS: ...
Cenas de teste: 2
bands: ['VV', 'VH', 'angle']
segmentation_models_pytorch: OK
```

O shape `(64, 2, 7, 7)` da primeira convolução é uma verificação útil de que o checkpoint espera dois canais.

Depois rode o teste que não executa a U-Net:

```bash
python test_raster_aoi.py
```

Ele verifica:

- leitura de VV/VH;
- shape `[2,H,W]`;
- interseção entre AOI e raster.

---

## 8. Testar a API

Inicie:

```bash
uvicorn main:app --reload
```

Acesse no navegador:

```text
http://127.0.0.1:8000/docs
```

### Endpoints

#### `GET /health`

Confirma que a API está online.

#### `GET /demo/scenes`

Inspeciona as duas imagens de teste e retorna metadados como bandas, CRS, resolução e dimensões.

#### `POST /demo/macrophytes`

Executa a inferência diretamente, sem passar pelo agente.

Primeira cena:

```json
{
  "image_index": 0
}
```

Segunda cena:

```json
{
  "image_index": 1
}
```

#### `POST /agent/run`

Executa a camada de agente.

```json
{
  "message": "Analise as macrófitas da primeira imagem"
}
```

ou:

```json
{
  "message": "Liste as imagens Sentinel-1 disponíveis"
}
```

---

## 9. Testar pelo terminal sem Swagger

Com a API rodando:

```bash
curl http://127.0.0.1:8000/health
```

Listar cenas:

```bash
curl http://127.0.0.1:8000/demo/scenes
```

Inferência direta:

```bash
curl -X POST "http://127.0.0.1:8000/demo/macrophytes" \
  -H "Content-Type: application/json" \
  -d '{"image_index":0}'
```

Agente:

```bash
curl -X POST "http://127.0.0.1:8000/agent/run" \
  -H "Content-Type: application/json" \
  -d '{"message":"Analise as macrofitas da primeira imagem"}'
```

---

## 10. O que acontece ao executar uma análise

Quando `POST /demo/macrophytes` ou a tool do agente é chamada:

1. `demo_service.py` seleciona uma das cenas de teste;
2. `macrofitas.py` abre raster, AOI e checkpoint;
3. `raster_utils.py` encontra VV/VH por nome;
4. AOI é reprojetada para o CRS do raster;
5. a AOI é transformada em máscara booleana;
6. a U-Net é criada com ResNet34, 2 canais e 3 classes;
7. pesos do `.pt` são carregados;
8. raster é dividido em patches 128 x 128;
9. patches são processados em lotes;
10. probabilidades sobrepostas são combinadas com janela de Hann;
11. classe de fundo é suprimida dentro da AOI, conforme o código de referência;
12. é feito `argmax` para obter a classe final de cada pixel;
13. métricas são calculadas somente dentro da AOI;
14. resultado classificado é salvo em `outputs/classifications/`;
15. um dicionário/JSON retorna os resultados para API/tool/agente.

Exemplo de retorno esperado estruturalmente:

```json
{
  "status": "success",
  "input_band_order": ["VV", "VH"],
  "classes": {
    "0": "background",
    "1": "water",
    "2": "plant"
  },
  "aoi_pixels": 1234,
  "water_pixels": 900,
  "plant_pixels": 334,
  "plant_pct": 27.06,
  "plant_area_m2": 33400.0,
  "crs": "EPSG:32723",
  "classification_path": "..."
}
```

Os números acima são apenas ilustrativos; os valores reais são produzidos pela execução local do modelo.

---

## 11. Rasters de teste incluídos

As duas imagens fornecidas pelo grupo são Sentinel-1 GRD exportadas pelo Google Earth Engine. Os arquivos incluídos têm:

```text
bandas: VV, VH, angle
resolução: 10 m
CRS: EPSG:32723
```

O pipeline usa apenas `VV` e `VH` na inferência.

O `angle` permanece no arquivo de origem, mas não é enviado à U-Net.

---

## 12. Aquisição Copernicus e Google Earth Engine

A pasta `acquisition/` preserva a prova de conceito anterior.

Ela contém:

- busca Sentinel-1/Sentinel-2 no Copernicus Data Space;
- autenticação CDSE;
- busca/download no Google Earth Engine;
- exportação multibanda GeoTIFF;
- configuração de bandas e AOI.

Nesta entrega, a inferência usa deliberadamente as imagens locais fornecidas pelo grupo. Isso isola a validação do modelo da autenticação/download remoto.

Próxima integração:

```text
agente
  -> tool de busca
  -> GEE ou Copernicus
  -> GeoTIFF padronizado
  -> analisar_macrofitas
```

### Configuração opcional do Earth Engine

```bash
cp .env.example .env
```

Preencha `EE_PROJECT_ID`.

Depois a autenticação pode ser validada usando o código da pasta `acquisition/google_earth_engine/`.

### Configuração opcional Copernicus

No `.env`:

```env
CDSE_USERNAME=...
CDSE_PASSWORD="..."
```

Nunca envie `.env` para o GitHub.

---

## 13. Trocar o modelo quando o novo checkpoint chegar

Se o novo modelo mantiver exatamente a mesma arquitetura:

```text
U-Net
encoder=resnet34
in_channels=2
classes=3
```

basta substituir:

```text
models/macrofitas/model_best_unet2_s1_S1.pt
```

pelo novo checkpoint, preservando o nome, ou alterar `DEFAULT_MODEL` em:

```text
app/config.py
```

Depois:

```bash
python check_setup.py
```

Se `model.load_state_dict()` apresentar incompatibilidade, então o novo arquivo não é apenas uma troca de pesos compatível e será necessário verificar a arquitetura usada no novo treinamento.

---

## 14. O que ainda NÃO está concluído nesta versão

Para apresentação, é importante distinguir o que funciona do que ainda é evolução:

- o agente atual não utiliza ainda um LLM externo; usa roteamento determinístico sobre as tools;
- aquisição remota GEE/CDSE está preservada, mas ainda não foi conectada automaticamente à tool de inferência nesta entrega;
- Sentinel-2/qualidade da água está apenas como código de referência, ainda não integrado à API/agente;
- não existe histórico persistente em banco;
- não existe frontend;
- não há validação científica dos resultados gerados pelo checkpoint atual nesta entrega;
- o grupo informou que um novo modelo Sentinel-1 está sendo treinado, portanto os resultados do checkpoint atual devem ser tratados como demonstração técnica até a substituição/validação.

---

## 15. Próximos passos recomendados

Ordem de implementação após a demonstração:

```text
1. validar resultado das duas cenas com o grupo
2. receber e trocar novo checkpoint Sentinel-1
3. conectar acquisition -> inferência
4. substituir roteador determinístico por LLM/tool calling
5. integrar Sentinel-2 e os quatro modelos .pkl
6. criar comparação temporal
7. persistir análises/metadados
8. criar frontend/mapa interativo
```

---

## 16. Roteiro curto para apresentação

Uma demonstração de 2 a 4 minutos pode seguir esta sequência:

1. mostrar a árvore de pastas;
2. explicar que o agente não processa raster: ele chama uma tool;
3. abrir `/docs`;
4. chamar `GET /demo/scenes` e mostrar `VV`, `VH`, `angle`, CRS e resolução;
5. chamar `POST /agent/run` com `Analise as macrófitas da primeira imagem`;
6. mostrar que a tool chama o pipeline;
7. mostrar JSON com `%` e área de macrófitas;
8. mostrar o arquivo gerado em `outputs/classifications/`;
9. explicar que as imagens vieram do GEE e que o próximo passo é fazer a própria tool adquirir a cena automaticamente;
10. explicar que o novo checkpoint pode ser trocado sem alterar o restante da estrutura, se a arquitetura for mantida.

A mensagem central da demonstração é:

> **o agente orquestra; o código geoespacial prepara os dados; a U-Net classifica; as métricas voltam de forma estruturada.**
