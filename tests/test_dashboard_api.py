from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from src.dashboard.api_client import (
    check_api_health,
    create_demo_shipment_payload,
    generate_demo_prediction,
)


class HealthHandler(BaseHTTPRequestHandler):
    status_code = 200
    response_body = b'{"status":"ok"}'

    def do_GET(self) -> None:
        self.send_response(self.status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.response_body)

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def health_server():
    HealthHandler.status_code = 200
    HealthHandler.response_body = b'{"status":"ok"}'
    server = HTTPServer(("127.0.0.1", 0), HealthHandler)
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
    HealthHandler.status_code = 503

    result = check_api_health(health_server)

    assert not result.available
    assert "HTTP 503" in result.detail


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
