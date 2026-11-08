from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from typing import TypedDict


class DemoShipment(TypedDict):
    shipment_id: str
    order_date: date
    region: str
    risk: str
    probability: float
    status: str


DEMO_SHIPMENTS: tuple[DemoShipment, ...] = (
    {"shipment_id": "ENV-1024", "order_date": date(2026, 10, 1), "region": "Norte", "risk": "Alto", "probability": 0.72, "status": "Pendiente"},
    {"shipment_id": "ENV-1030", "order_date": date(2026, 10, 5), "region": "Sur", "risk": "Medio", "probability": 0.54, "status": "Monitoreado"},
    {"shipment_id": "ENV-1048", "order_date": date(2026, 10, 12), "region": "Latam", "risk": "Alto", "probability": 0.68, "status": "Prioridad"},
    {"shipment_id": "ENV-1051", "order_date": date(2026, 10, 20), "region": "Centro", "risk": "Bajo", "probability": 0.22, "status": "OK"},
)

DEMO_REGION_COORDINATES = {
    "Norte": (41.3851, 2.1734),
    "Centro": (40.4168, -3.7038),
    "Sur": (36.7194, -4.4200),
    "Latam": (-34.6037, -58.3816),
}


def filter_demo_shipments(
    shipments: Sequence[DemoShipment],
    start_date: date,
    end_date: date,
    risk: str,
    region: str,
) -> list[DemoShipment]:
    return [
        shipment
        for shipment in shipments
        if start_date <= shipment["order_date"] <= end_date
        and (risk == "Todos" or shipment["risk"] == risk)
        and (region == "Todas" or shipment["region"] == region)
    ]


def summarize_demo_shipments(
    shipments: Sequence[DemoShipment],
) -> dict[str, int | float]:
    if not shipments:
        return {
            "shipments": 0,
            "high_risk": 0,
            "average_probability": 0.0,
            "critical_regions": 0,
        }

    regional_probabilities: dict[str, list[float]] = defaultdict(list)
    for shipment in shipments:
        regional_probabilities[shipment["region"]].append(shipment["probability"])

    return {
        "shipments": len(shipments),
        "high_risk": sum(shipment["risk"] == "Alto" for shipment in shipments),
        "average_probability": sum(
            shipment["probability"] for shipment in shipments
        )
        / len(shipments),
        "critical_regions": sum(
            sum(probabilities) / len(probabilities) >= 0.6
            for probabilities in regional_probabilities.values()
        ),
    }


def demo_region_risk(shipments: Sequence[DemoShipment]) -> dict[str, float]:
    regional_probabilities: dict[str, list[float]] = defaultdict(list)
    for shipment in shipments:
        regional_probabilities[shipment["region"]].append(shipment["probability"])
    return {
        region: sum(probabilities) / len(probabilities)
        for region, probabilities in regional_probabilities.items()
    }


def demo_map_points(shipments: Sequence[DemoShipment]) -> list[dict[str, float]]:
    return [
        {
            "lat": DEMO_REGION_COORDINATES[shipment["region"]][0],
            "lon": DEMO_REGION_COORDINATES[shipment["region"]][1],
        }
        for shipment in shipments
        if shipment["region"] in DEMO_REGION_COORDINATES
    ]
