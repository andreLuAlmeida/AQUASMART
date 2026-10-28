from app.services.aoi_service import bbox_para_geojson, validar_geojson_aoi


def test_bbox_is_valid_polygon():
    geo = bbox_para_geojson(-44.2, -20.1, -44.0, -19.9)
    out = validar_geojson_aoi(geo)
    assert out["type"] == "Polygon"


def test_invalid_aoi_rejected():
    try:
        validar_geojson_aoi({"type": "Point", "coordinates": [0, 0]})
        assert False
    except ValueError:
        assert True
