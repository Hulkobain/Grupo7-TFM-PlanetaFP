from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

import httpx
from fastapi import FastAPI, HTTPException, Request, status

from .inference import InferenceService, load_inference_service
from .schemas import HealthResponse, IngestResponse, PredictionResponse, ShipmentFeatures
from .webhooks import is_webhook_configured, send_high_risk_alert

logger = logging.getLogger(__name__)


def create_webhook_client() -> httpx.AsyncClient:
    return httpx.AsyncClient()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.inference_service = load_inference_service()
    async with create_webhook_client() as webhook_client:
        app.state.webhook_client = webhook_client
        yield


app = FastAPI(
    title="Smart Supply Chain Risk AI API",
    description="API de validación e inferencia de riesgo de retraso de envíos.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


async def _predict(
    shipment: ShipmentFeatures,
    request: Request,
) -> PredictionResponse:
    inference_service: InferenceService | None = getattr(
        request.app.state,
        "inference_service",
        None,
    )
    if inference_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction model is not configured.",
        )
    prediction = inference_service.predict(shipment.model_dump(mode="python"))
    if prediction.delay_risk and is_webhook_configured():
        webhook_client: httpx.AsyncClient = request.app.state.webhook_client
        try:
            await send_high_risk_alert(
                shipment.model_dump(mode="json"),
                prediction.model_dump(mode="json"),
                webhook_client,
            )
        except (httpx.HTTPError, ValueError):
            logger.exception(
                "Could not deliver preventive high-risk webhook; returning prediction"
            )
    return prediction


@app.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    tags=["shipments"],
)
async def ingest_shipment(
    shipment: ShipmentFeatures,
    request: Request,
) -> IngestResponse:
    prediction = await _predict(shipment, request)
    return IngestResponse(
        status="processed",
        shipment=shipment,
        prediction=prediction,
    )


@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["predictions"],
)
async def predict_shipment(
    shipment: ShipmentFeatures,
    request: Request,
) -> PredictionResponse:
    return await _predict(shipment, request)
