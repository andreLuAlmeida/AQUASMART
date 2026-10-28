import rasterio
import numpy as np
import pandas as pd
import joblib

# =======================================================
# 1. CONFIGURAÇÕES INICIAIS
# =======================================================
# Caminhos dos arquivos
IMAGE_PATH = r"C:\caminho\imagem_sentinel2_empilhada.tif"
MODEL_PATH = r"C:\caminho\modelo_producao_Senti_chl_a.pkl"
OUTPUT_PATH = r"C:\caminho\mapa_clorofila_predito.tif"

# Nome exato das bandas na ordem em que estão no seu TIF empilhado
SENSOR_BANDS = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A']

# Mapeamento do Sentinel (Igual ao do treinamento)
BAND_MAPPING = {
    'BLUE': 'B2',
    'GREEN': 'B3',
    'RED': 'B4',
    'RE1': 'B5',
    'RE2': 'B6',
    'NIR': 'B8' # Ou B8A, dependendo de como você treinou
}

# Limiares das Máscaras
NDWI_THRESHOLD = 0.0  # Pixels acima de 0 são considerados água
NDVI_THRESHOLD = 0.2  # Pixels abaixo de 0.2 são considerados água sem vegetação densa


# =======================================================
# 2. FUNÇÃO DE CÁLCULO DE ÍNDICES (Cópia exata do Treino)
# =======================================================
def calculate_spectral_indices(df, b_map):
    df = df.copy()
    epsilon = 1e-8
    
    B, G, R = df[b_map['BLUE']], df[b_map['GREEN']], df[b_map['RED']]
    RE1, RE2, NIR = df[b_map['RE1']], df[b_map['RE2']], df[b_map['NIR']]

    # Índices Estruturais e Básicos
    df['GREEN_BLUE'] = G / (B + epsilon)
    df['GREEN_RED'] = G / (R + epsilon)
    df['NIR_RED'] = NIR / (R + epsilon)
    df['GB1'] = G / (B + epsilon)
    df['GR'] = G / (R + epsilon)
    df['NDWI'] = (G - NIR) / (G + NIR + epsilon)
    df['NDVI'] = (NIR - R) / (NIR + R + epsilon)
    df['GNDVI'] = (NIR - G) / (NIR + G + epsilon)
    df['BNDVI'] = (NIR - B) / (NIR + B + epsilon)
    df['CVI'] = (NIR * R) / (G**2 + epsilon)
    df['CI_green'] = (NIR / (G + epsilon)) - 1
    df['NDTI'] = (R - G) / (R + G + epsilon)
    df['SABI'] = (NIR - R) / (B + G + epsilon)
    df['KIVU'] = (B - R) / (G + epsilon)
    df['B3B1'] = (R - B) / (R + B + epsilon)
    df['R2_B'] = (R**2) / (B + epsilon)

    # Índices Red-Edge
    df['NDCI'] = (RE1 - R) / (RE1 + R + epsilon)
    df['NDRE'] = (NIR - RE2) / (NIR + RE2 + epsilon)
    df['CI_rededge'] = (NIR / (RE2 + epsilon)) - 1
    df['2BDA_2'] = RE1 / (R + epsilon)
    df['3BDA_MOD'] = (1 / (R + epsilon)) - (1 / (RE1 + epsilon))
    df['3BDA_1'] = df['3BDA_MOD'] * NIR
    df['MCI'] = RE1 - (R + (RE2 - R) * ((705 - 665) / (740 - 665)))
    
    # Modelo Empírico Logarítmico
    df['Kab1_Rrs'] = 1.67 - 3.94 * np.log(B.clip(lower=epsilon)) + 3.78 * np.log(G.clip(lower=epsilon))
    
    new_indices = [
        'GREEN_BLUE', 'GREEN_RED', 'NIR_RED', 'GB1', 'GR', 'NDWI', 'NDVI', 'GNDVI', 
        'BNDVI', 'CVI', 'CI_green', 'NDTI', 'SABI', 'KIVU', 'B3B1', 'R2_B', 
        'NDCI', 'NDRE', 'CI_rededge', '2BDA_2', '3BDA_MOD', '3BDA_1', 'MCI', 'Kab1_Rrs'
    ]
    return df, new_indices

# =======================================================
# 3. LEITURA, MÁSCARAS E PREDIÇÃO
# =======================================================
print("Lendo a imagem do satélite...")
with rasterio.open(IMAGE_PATH) as src:
    meta = src.meta
    # Lê a imagem como um array (Bandas, Linhas, Colunas)
    image_array = src.read()
    
    # Verifica se o TIF tem o número de bandas esperado
    if image_array.shape[0] != len(SENSOR_BANDS):
        raise ValueError(f"O TIF possui {image_array.shape[0]} bandas, mas o script espera {len(SENSOR_BANDS)}.")

# Achatar a imagem para formato tabular (DataFrame)
n_bands, rows, cols = image_array.shape
image_flattened = image_array.reshape(n_bands, -1).T
df_image = pd.DataFrame(image_flattened, columns=SENSOR_BANDS)

# Filtro 1: Remover NoData (Pixels escuros ou bordas)
valid_data_mask = (df_image > 0).all(axis=1)

# Filtro 2: Máscaras de Água (NDWI) e Vegetação (NDVI)
print("Aplicando máscaras de água e macrófitas...")
G_arr = df_image[BAND_MAPPING['GREEN']]
R_arr = df_image[BAND_MAPPING['RED']]
NIR_arr = df_image[BAND_MAPPING['NIR']]

NDWI = (G_arr - NIR_arr) / (G_arr + NIR_arr + 1e-8)
NDVI = (NIR_arr - R_arr) / (NIR_arr + R_arr + 1e-8)

water_mask = (NDWI > NDWI_THRESHOLD) & (NDVI < NDVI_THRESHOLD)

# Combinar todas as máscaras
final_mask = valid_data_mask & water_mask

# Separar apenas os pixels que são puramente água
df_water = df_image[final_mask].copy()
print(f"Pixels válidos de água encontrados: {len(df_water)} de {len(df_image)}")

if len(df_water) == 0:
    print("Nenhum pixel de água encontrado. Ajuste os limiares de NDWI/NDVI.")
else:
    # Calcular índices APENAS para os pixels de água
    print("Calculando índices espectrais...")
    df_water, INDICES_LIST = calculate_spectral_indices(df_water, BAND_MAPPING)
    df_water.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_water.fillna(0, inplace=True) # Prevenção de quebra

    ALL_FEATURES = SENSOR_BANDS + INDICES_LIST

    # Fazer a Predição
    print("Carregando o modelo e realizando predições...")
    model = joblib.load(MODEL_PATH)
    predicoes = model.predict(df_water[ALL_FEATURES])

    # =======================================================
    # 4. RECONSTRUÇÃO DO MAPA E SALVAMENTO
    # =======================================================
    print("Gerando o mapa final...")
    
    # Criar um array vazio (cheio de NaNs) com o tamanho total da imagem original
    mapa_predito_1d = np.full(rows * cols, np.nan)
    
    # Injetar os valores preditos exatamente onde a máscara final é Verdadeira
    mapa_predito_1d[final_mask] = predicoes
    
    # Remontar para formato 2D (Linhas, Colunas)
    mapa_predito_2d = mapa_predito_1d.reshape(rows, cols)

    # Atualizar metadados para salvar um arquivo com apenas 1 banda (o parâmetro predito)
    meta.update(
        count=1,
        dtype=rasterio.float32,
        nodata=np.nan
    )

    # Salvar o arquivo TIFF
    with rasterio.open(OUTPUT_PATH, 'w', **meta) as dst:
        dst.write(mapa_predito_2d.astype(rasterio.float32), 1)

    print(f"✅ Sucesso! Mapa salvo em: {OUTPUT_PATH}")