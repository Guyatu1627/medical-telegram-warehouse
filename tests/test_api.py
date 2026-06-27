from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Medical Telegram Warehouse API"}

def test_health_check_offline():
    response = client.get("/health")
    assert response.status_code == 200
    # Because db is not up in tests environment, this should report unhealthy
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database_connected"] is False
