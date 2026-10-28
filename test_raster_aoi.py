"""Teste rápido sem carregar a U-Net: verifica interseção AOI/raster e bandas."""
import rasterio
import geopandas as gpd
from app.config import DEFAULT_AOI, TEST_IMAGES
from app.services.raster_utils import read_vv_vh

for p in TEST_IMAGES:
    with rasterio.open(p) as src:
        arr, idx = read_vv_vh(src)
        gdf = gpd.read_file(DEFAULT_AOI).to_crs(src.crs)
        intersects = bool(gdf.intersects(gdf.geometry.unary_union.envelope).any())
        raster_bounds = src.bounds
        minx, miny, maxx, maxy = gdf.total_bounds
        overlap = not (maxx < raster_bounds.left or minx > raster_bounds.right or maxy < raster_bounds.bottom or miny > raster_bounds.top)
        print(p.name, "shape", arr.shape, "bands", idx, "AOI overlaps raster:", overlap)
