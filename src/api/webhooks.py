import asyncio
import os
from collections.abc import Mapping

import httpx

DEFAULT_MAX_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = {408, 429}
WEBHOOK_TIMEOUT_SECONDS = 5.0


def _get_max_attempts() -> int:
    value = os.getenv("WEBHOOK_MAX_ATTEMPTS", str(DEFAULT_MAX_ATTEMPTS))
    try:
        attempts = int(value)
    except ValueError as exc:
        raise ValueError("WEBHOOK_MAX_ATTEMPTS must be a positive integer.") from exc
    if attempts < 1:
        raise ValueError("WEBHOOK_MAX_ATTEMPTS must be a positive integer.")
    return attempts


async def send_high_risk_alert(
    prediction: Mapping[str, object],
    client: httpx.AsyncClient,
) -> None:
    if prediction.get("Risk_Level") != "Alto":
        return

    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("WEBHOOK_URL must be configured for high-risk alerts.")

    max_attempts = _get_max_attempts()
    for attempt in range(1, max_attempts + 1):
        try:
            response = await client.post(
                webhook_url,
                json=dict(prediction),
                timeout=WEBHOOK_TIMEOUT_SECONDS,
            )
        except httpx.TransportError:
            if attempt == max_attempts:
                raise
        else:
            if (
                response.status_code not in RETRYABLE_STATUS_CODES
                and response.status_code < 500
            ):
                response.raise_for_status()
                return
            if attempt == max_attempts:
                response.raise_for_status()

        await asyncio.sleep(min(0.25 * (2 ** (attempt - 1)), 2.0))
