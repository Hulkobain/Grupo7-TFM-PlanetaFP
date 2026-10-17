from fastapi import FastAPI, HTTPException, status

from .schemas import HealthResponse, IngestResponse, PredictionResponse, ShipmentFeatures

app = FastAPI(
    title="Smart Supply Chain Risk AI API",
    description="API de validación e inferencia de riesgo de retraso de envíos.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    tags=["shipments"],
)
def ingest_shipment(shipment: ShipmentFeatures) -> IngestResponse:
    return IngestResponse(status="validated", shipment=shipment)


@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["predictions"],
)
def predict_shipment(_: ShipmentFeatures) -> PredictionResponse:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Prediction model is not configured.",
    )
