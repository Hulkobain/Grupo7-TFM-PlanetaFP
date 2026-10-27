from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from src.dashboard.api_client import (
    check_api_health,
    create_demo_shipment_payload,
    generate_demo_prediction,
    predict_shipment,
)


class ApiHandler(BaseHTTPRequestHandler):
    status_code = 200
    response_body = b'{"status":"ok"}'
    method = "GET"

    def do_GET(self) -> None:
        if self.path.endswith("/health") or self.path == "/":
            self.send_response(self.status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(self.response_body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        self.send_response(getattr(self.server, "post_status_code", 200))
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        body = getattr(self.server, "post_response_body", b'{"delay_risk": false, "delay_probability": 0.1, "threshold": 0.5}')
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


HealthHandler = ApiHandler


@pytest.fixture
def health_server():
    ApiHandler.status_code = 200
    ApiHandler.response_body = b'{"status":"ok"}'
    server = HTTPServer(("127.0.0.1", 0), ApiHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_check_api_health_accepts_a_healthy_api(health_server: str) -> None:
    result = check_api_health(health_server)

    assert result.available
    assert result.detail == "API FastAPI disponible."


def test_check_api_health_reports_an_unhealthy_status(health_server: str) -> None:
    HealthHandler.response_body = b'{"status":"starting"}'

    result = check_api_health(health_server)

    assert not result.available
    assert "estado de salud no válido" in result.detail


def test_check_api_health_reports_invalid_json(health_server: str) -> None:
    HealthHandler.response_body = b"not-json"

    result = check_api_health(health_server)

    assert not result.available
    assert "respuesta de salud no válida" in result.detail


def test_check_api_health_reports_http_errors(health_server: str) -> None:
    ApiHandler.status_code = 503
    ApiHandler.response_body = b'{"detail": "Prediction model is not configured."}'

    result = check_api_health(health_server)

    assert not result.available
    assert "503" in result.detail


def test_check_api_health_uses_the_health_endpoint(health_server: str) -> None:
    result = check_api_health(f"{health_server}/")

    assert result.available

def test_generate_demo_prediction_returns_summary_payload() -> None:
    payload = create_demo_shipment_payload()

    result = generate_demo_prediction(payload)

    assert result["status"] == "demo_preview"
    assert 0.0 <= result["delay_probability"] <= 1.0
    assert result["risk_level"] in {"Bajo", "Medio", "Alto"}
    assert "timestamp" in result


def test_predict_shipment_handles_timeout_error(monkeypatch) -> None:
    from src.dashboard import api_client
    from urllib.error import URLError

    def fake_urlopen(*args, **kwargs):
        raise TimeoutError('timed out')

    monkeypatch.setattr(api_client, 'urlopen', fake_urlopen)
    result = predict_shipment('http://example.com', {})
    assert not result.available
    assert 'tiempo' in result.detail.lower()


def test_predict_shipment_handles_503_without_model(monkeypatch) -> None:
    from src.dashboard import api_client
    from urllib.error import HTTPError
    from io import BytesIO

    def fake_urlopen(*args, **kwargs):
        raise HTTPError(
            'http://example.com/predict',
            503,
            'Service Unavailable',
            {'Content-Type': 'application/json'},
            BytesIO(b'{"detail": "Prediction model is not configured."}'),
        )

    monkeypatch.setattr(api_client, 'urlopen', fake_urlopen)
    result = predict_shipment('http://example.com', {})
    assert not result.available
    assert '503' in result.detail or 'modelo' in result.detail.lower()
