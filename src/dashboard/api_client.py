import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ApiHealth:
    available: bool
    detail: str


@dataclass(frozen=True)
class ApiPrediction:
    available: bool
    detail: str
    data: dict[str, Any] | None = None


def check_api_health(base_url: str, timeout: float = 3) -> ApiHealth:
    endpoint = f"{base_url.rstrip('/')}/health"

    try:
        with urlopen(endpoint, timeout=timeout) as response:
            if response.status != 200:
                return ApiHealth(False, f"La API respondió con HTTP {response.status}.")
            payload = json.loads(response.read())
    except HTTPError as exc:
        if exc.code == 503:
            try:
                body = exc.read().decode("utf-8")
                detail = json.loads(body).get("detail", "")
                if detail:
                    if "model" in detail.lower():
                        return ApiHealth(False, "El modelo de predicción no está disponible (503).")
                    return ApiHealth(False, f"La API no está disponible (503): {detail}")
            except Exception:
                pass
            return ApiHealth(False, "El modelo de predicción no está disponible (503).")
        return ApiHealth(False, f"La API respondió con HTTP {exc.code}.")
    except TimeoutError:
        return ApiHealth(False, "Tiempo de espera agotado al conectar con la API.")
    except URLError as exc:
        reason = exc.reason
        if isinstance(reason, TimeoutError):
            return ApiHealth(False, "Tiempo de espera agotado al conectar con la API.")
        return ApiHealth(False, f"No se pudo conectar con la API ({reason}).")
    except OSError as exc:
        if isinstance(exc, TimeoutError) or "timed out" in str(exc).lower():
            return ApiHealth(False, "Tiempo de espera agotado al conectar con la API.")
        return ApiHealth(False, f"No se pudo conectar con la API ({exc}).")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return ApiHealth(False, "La API devolvió una respuesta de salud no válida.")

    if not isinstance(payload, dict) or payload.get("status") != "ok":
        return ApiHealth(False, "La API devolvió un estado de salud no válido.")

    return ApiHealth(True, "API FastAPI disponible.")


def predict_shipment(base_url: str, shipment: dict[str, Any], timeout: float = 10) -> ApiPrediction:
    endpoint = f"{base_url.rstrip('/')}/predict"
    data = json.dumps(shipment).encode("utf-8")
    request = Request(endpoint, data=data, method="POST")
    request.add_header("Content-Type", "application/json")

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read())
    except HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
            detail_json = json.loads(body)
            detail = detail_json.get("detail", "")
        except Exception:
            detail = ""
        if exc.code == 503:
            if detail and "model" in str(detail).lower():
                return ApiPrediction(False, "El modelo de predicción no está disponible (503).")
            if detail:
                return ApiPrediction(False, f"Servicio no disponible (503): {detail}")
            return ApiPrediction(False, "El modelo de predicción no está disponible (503).")
        if detail:
            return ApiPrediction(False, detail)
        return ApiPrediction(False, f"La API respondió con HTTP {exc.code}.")
    except TimeoutError:
        return ApiPrediction(False, "Tiempo de espera agotado al obtener la predicción.")
    except URLError as exc:
        reason = exc.reason
        if isinstance(reason, TimeoutError):
            return ApiPrediction(False, "Tiempo de espera agotado al obtener la predicción.")
        return ApiPrediction(False, f"No se pudo conectar con la API ({reason}).")
    except OSError as exc:
        if isinstance(exc, TimeoutError) or "timed out" in str(exc).lower():
            return ApiPrediction(False, "Tiempo de espera agotado al obtener la predicción.")
        return ApiPrediction(False, f"No se pudo conectar con la API ({exc}).")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return ApiPrediction(False, "La API devolvió una respuesta de predicción no válida.")

    if not isinstance(payload, dict):
        return ApiPrediction(False, "La API devolvió una respuesta de predicción no válida.")

    return ApiPrediction(True, "Predicción obtenida correctamente.", payload)


def generate_demo_prediction(shipment: dict[str, Any]) -> dict[str, Any]:
    total_quantity = sum(
        int(item.get("order_item_quantity", 0)) for item in shipment.get("order_items", [])
    )
    total_price = sum(
        float(item.get("product_price", 0)) * int(item.get("order_item_quantity", 0))
        for item in shipment.get("order_items", [])
    )
    discount_rate = sum(
        float(item.get("order_item_discount", 0)) for item in shipment.get("order_items", [])
    )
    region = shipment.get("order_region", "Norte")
    market = shipment.get("market", "Europe")

    score = 0.2
    score += min(0.35, total_quantity * 0.03)
    score += min(0.25, total_price / 5000.0 * 0.08)
    score += min(0.15, discount_rate / 100.0)
    if region in {"Sur", "Latam"}:
        score += 0.12
    if market in {"Europe", "North America"}:
        score += 0.05

    probability = min(0.96, max(0.09, round(score, 3)))
    risk_level = "Alto" if probability >= 0.65 else "Medio" if probability >= 0.4 else "Bajo"

    return {
        "delay_risk": risk_level != "Bajo",
        "delay_probability": probability,
        "risk_level": risk_level,
        "status": "demo_preview",
        "message": "Vista local de prueba del frontend. Conecta el backend cuando exista el modelo real.",
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def create_demo_shipment_payload() -> dict[str, Any]:
    return {
        "order_date": "2026-10-15T10:00:00",
        "shipping_mode": "Air",
        "customer_segment": "Corporate",
        "market": "Europe",
        "order_region": "Norte",
        "order_items": [
            {
                "product_category_id": 12,
                "product_price": 65.5,
                "order_item_quantity": 2,
                "order_item_discount": 5.0,
            },
            {
                "product_category_id": 18,
                "product_price": 90.0,
                "order_item_quantity": 1,
                "order_item_discount": 8.0,
            },
        ],
    }
