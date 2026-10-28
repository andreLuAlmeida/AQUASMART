# AQUASMART MVP

Interface de validação para aquisição automática de imagens, inferência e geração de produtos geoespaciais.

## 1. Ambiente Python

Use o ambiente que já executa a U-Net. Instale as dependências faltantes sem reinstalar PyTorch se seu ambiente CPU já estiver pronto:

```bash
python -m pip install fastapi 'uvicorn[standard]' pydantic python-dotenv \
  rasterio geopandas shapely pandas matplotlib tqdm pystac-client requests \
  earthengine-api joblib 'scikit-learn>=1.9' cubist
```

Garanta também `segmentation-models-pytorch` no ambiente da U-Net.

## 2. Configuração

```bash
cp .env.example .env
```

Preencha `EE_PROJECT_ID` e, se desejar testar CDSE, `CDSE_USERNAME` e `CDSE_PASSWORD`.

## 3. Backend

```bash
uvicorn main:app --reload
```

Swagger: `http://127.0.0.1:8000/docs`.

## 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Interface: `http://127.0.0.1:5173`.

## 5. Testes

```bash
pytest -q tests
python check_mvp.py
```

Veja `docs/00_MVP_IMPLEMENTADO.md` para o escopo e limitações atuais.
