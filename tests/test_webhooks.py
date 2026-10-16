import asyncio

import httpx
import pytest

from src.api.webhooks import send_high_risk_alert


def test_sends_high_risk_prediction_to_configured_webhook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEBHOOK_URL", "https://example.test/alerts")
    prediction = {"Risk_Level": "Alto", "Late_Risk_Probability": 0.92}
    requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handle_request)
        ) as client:
            await send_high_risk_alert(prediction, client)

    asyncio.run(run())

    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert str(requests[0].url) == "https://example.test/alerts"
    assert requests[0].read() == b'{"Risk_Level":"Alto","Late_Risk_Probability":0.92}'


def test_does_not_send_alert_for_non_high_risk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handle_request)
        ) as client:
            await send_high_risk_alert({"Risk_Level": "Medio"}, client)

    asyncio.run(run())

    assert requests == []


def test_retries_transient_server_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEBHOOK_URL", "https://example.test/alerts")
    monkeypatch.setenv("WEBHOOK_MAX_ATTEMPTS", "3")
    responses = iter([503, 503, 204])
    requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(next(responses))

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handle_request)
        ) as client:
            await send_high_risk_alert({"Risk_Level": "Alto"}, client)

    asyncio.run(run())

    assert len(requests) == 3


def test_does_not_retry_non_transient_client_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEBHOOK_URL", "https://example.test/alerts")
    requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(400)

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handle_request)
        ) as client:
            await send_high_risk_alert({"Risk_Level": "Alto"}, client)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(run())

    assert len(requests) == 1


def test_requires_webhook_url_for_high_risk_predictions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WEBHOOK_URL", raising=False)

    async def run() -> None:
        async with httpx.AsyncClient() as client:
            await send_high_risk_alert({"Risk_Level": "Alto"}, client)

    with pytest.raises(RuntimeError, match="WEBHOOK_URL"):
        asyncio.run(run())


def test_rejects_invalid_retry_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEBHOOK_URL", "https://example.test/alerts")
    monkeypatch.setenv("WEBHOOK_MAX_ATTEMPTS", "0")

    async def run() -> None:
        async with httpx.AsyncClient() as client:
            await send_high_risk_alert({"Risk_Level": "Alto"}, client)

    with pytest.raises(ValueError, match="WEBHOOK_MAX_ATTEMPTS"):
        asyncio.run(run())
