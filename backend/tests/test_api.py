import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "monday_integration" in data

def test_data_quality():
    response = client.get("/api/data-quality")
    assert response.status_code == 200
    data = response.json()
    assert "deals_board" in data
    assert "work_orders_board" in data

def test_tools_deals():
    response = client.get("/api/tools/deals?sector=Mining")
    assert response.status_code == 200
    data = response.json()
    assert data["matched_count"] > 0

def test_tools_work_orders():
    response = client.get("/api/tools/work-orders?sector=Mining")
    assert response.status_code == 200
    data = response.json()
    assert data["matched_count"] > 0

def test_tools_join():
    response = client.get("/api/tools/join")
    assert response.status_code == 200
    data = response.json()
    assert data["matched_deals_count"] > 0

def test_tools_leadership_update():
    response = client.get("/api/tools/leadership-update?scope=Mining")
    assert response.status_code == 200
    data = response.json()
    assert "headline_kpis" in data
    assert "markdown_export" in data

def test_chat_non_stream():
    response = client.post("/api/chat", json={"query": "How is our pipeline looking for energy sector?", "stream": False})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["reasoning_traces"]) > 0
    assert len(data["ui_cards"]) > 0
