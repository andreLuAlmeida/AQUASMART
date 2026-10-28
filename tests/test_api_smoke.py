from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_capabilities():
    r = client.get('/api/capabilities')
    assert r.status_code == 200
    data = r.json()
    assert any(x['id'] == 'macrophytes' for x in data['analysis_types'])
    assert any(x['id'] == 'water_quality' for x in data['analysis_types'])
