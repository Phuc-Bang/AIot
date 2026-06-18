from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

_VISION_LOADED = client.get("/health").json().get("vision_model_loaded", False)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service_status"] == "ok"


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "service" in data
    assert "docs" in data
    assert "/health" in data["endpoints"]


def test_forecast():
    r = client.post("/forecast", json={"recent_values": [1, 2, 3, 4, 5], "horizon_minutes": 15})
    assert r.status_code == 200
    assert "predicted_value" in r.json()["model_output"]
    assert r.json()["model_output"]["predicted_value"] == 3.0


def test_forecast_empty():
    r = client.post("/forecast", json={"recent_values": [], "horizon_minutes": 15})
    assert r.status_code == 400


def test_anomaly_detection():
    r = client.post("/detect-anomaly", json={
        "current_value": 100.0,
        "recent_values": [10, 12, 11, 13, 10, 12, 11],
        "threshold_z": 2.0
    })
    assert r.status_code == 200
    data = r.json()
    assert "model_output" in data
    assert "event" in data
    assert data["model_output"]["is_anomaly"] is True


def test_anomaly_normal():
    r = client.post("/detect-anomaly", json={
        "current_value": 11.0,
        "recent_values": [10, 12, 11, 13, 10, 12, 11],
        "threshold_z": 2.0
    })
    assert r.status_code == 200
    assert r.json()["model_output"]["is_anomaly"] is False


def test_anomaly_not_enough_data():
    r = client.post("/detect-anomaly", json={
        "current_value": 100.0,
        "recent_values": [10],
        "threshold_z": 2.0
    })
    assert r.status_code == 200
    assert r.json()["model_output"]["is_anomaly"] is False
    assert r.json()["event"]["severity"] == "NORMAL"


def test_risk_prediction():
    r = client.post("/predict-risk", json={
        "predicted_value": 1300.0,
        "warning_threshold": 1000.0,
        "high_threshold": 1200.0
    })
    assert r.status_code == 200
    assert r.json()["decision"]["risk_level"] == "HIGH"


def test_risk_warning():
    r = client.post("/predict-risk", json={
        "predicted_value": 1100.0,
        "warning_threshold": 1000.0,
        "high_threshold": 1200.0
    })
    assert r.status_code == 200
    assert r.json()["decision"]["risk_level"] == "WARNING"


def test_risk_normal():
    r = client.post("/predict-risk", json={
        "predicted_value": 500.0,
        "warning_threshold": 1000.0,
        "high_threshold": 1200.0
    })
    assert r.status_code == 200
    assert r.json()["decision"]["risk_level"] == "NORMAL"


def test_vision_info():
    r = client.get("/vision/model-info")
    assert r.status_code == 200
    assert r.json()["task"] == "image_classification"


def test_vision_model_info():
    r = client.get("/model-info")
    assert r.status_code == 200
    assert "vision_model" in r.json()
    assert "sensor_models" in r.json()


def test_image_demo_page():
    r = client.get("/classify-image-demo")
    assert r.status_code == 200
    assert "Upload ảnh" in r.text
    assert "classify-image-annotated" in r.text
    assert "topKSlider" in r.text


def test_classify_image_no_file():
    r = client.post("/classify-image")
    assert r.status_code == 422


def test_classify_image_empty_file():
    r = client.post("/classify-image", files={"file": ("test.jpg", b"", "image/jpeg")})
    assert r.status_code in (400, 503)


def test_classify_image_not_an_image():
    r = client.post("/classify-image", files={"file": ("test.txt", b"not an image", "text/plain")})
    assert r.status_code in (400, 503)


def test_classify_image_oversize():
    huge = b"x" * (6 * 1024 * 1024)
    r = client.post("/classify-image", files={"file": ("huge.jpg", huge, "image/jpeg")})
    assert r.status_code in (413, 503)


def test_classify_image_annotated_no_file():
    r = client.post("/classify-image-annotated")
    assert r.status_code == 422


def test_health_reports_vision_status():
    r = client.get("/health")
    assert "vision_model_loaded" in r.json()
    assert isinstance(r.json()["vision_model_loaded"], bool)
