import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "LinkDrip"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_landing_page(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "LinkDrip" in response.text
    assert "Short Links" in response.text
