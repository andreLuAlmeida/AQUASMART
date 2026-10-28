import importlib.util
import pytest

from app.config import DEFAULT_AOI, DEFAULT_MODEL, TEST_IMAGES
from app.services.macrofitas import inferir_macrofitas


@pytest.mark.skipif(importlib.util.find_spec('segmentation_models_pytorch') is None, reason='dependência opcional de inferência S1 não instalada no ambiente de teste')
def test_s1_inference_smoke(tmp_path):
    if not TEST_IMAGES or not DEFAULT_MODEL.exists():
        pytest.skip('dados/modelo de teste ausentes')
    result = inferir_macrofitas(TEST_IMAGES[0], DEFAULT_AOI, DEFAULT_MODEL, tmp_path / 'pred.tif')
    assert result['status'] == 'success'
    assert 0 <= result['plant_pct'] <= 100
    assert result['aoi_pixels'] > 0
