from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, status

from .inference import InferenceService, load_inference_service
from .schemas import HealthResponse, IngestResponse, PredictionResponse, ShipmentFeatures


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.inference_service = load_inference_service()
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


def _predict(
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
    return inference_service.predict(shipment.model_dump(mode="python"))


@app.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    tags=["shipments"],
)
def ingest_shipment(
    shipment: ShipmentFeatures,
    request: Request,
) -> IngestResponse:
    prediction = _predict(shipment, request)
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
def predict_shipment(
    shipment: ShipmentFeatures,
    request: Request,
) -> PredictionResponse:
    return _predict(shipment, request)
