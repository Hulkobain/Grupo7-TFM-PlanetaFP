from datetime import date

from src.dashboard.filters import (
    DEMO_SHIPMENTS,
    demo_region_risk,
    filter_demo_shipments,
    reset_filter_state,
    summarize_demo_shipments,
)


def test_filters_shipments_by_date_risk_and_region() -> None:
    result = filter_demo_shipments(
        DEMO_SHIPMENTS,
        date(2026, 10, 1),
        date(2026, 10, 12),
        "Alto",
        "Latam",
    )

    assert [shipment["shipment_id"] for shipment in result] == ["ENV-1048"]


def test_summary_and_region_risk_use_filtered_shipments() -> None:
    shipments = filter_demo_shipments(
        DEMO_SHIPMENTS,
        date(2026, 10, 1),
        date(2026, 10, 20),
        "Alto",
        "Todas",
    )

    assert summarize_demo_shipments(shipments) == {
        "shipments": 2,
        "high_risk": 2,
        "average_probability": 0.7,
        "critical_regions": 2,
    }
    assert demo_region_risk(shipments) == {"Norte": 0.72, "Latam": 0.68}


def test_no_matches_return_empty_summary() -> None:
    shipments = filter_demo_shipments(
        DEMO_SHIPMENTS,
        date(2026, 10, 1),
        date(2026, 10, 20),
        "Bajo",
        "Norte",
    )

    assert shipments == []
    assert summarize_demo_shipments(shipments) == {
        "shipments": 0,
        "high_risk": 0,
        "average_probability": 0.0,
        "critical_regions": 0,
    }
    assert demo_region_risk(shipments) == {}


def test_reset_filter_state_restores_default_values() -> None:
    state = {
        "dashboard_filter_dates": (date(2026, 10, 5), date(2026, 10, 12)),
        "dashboard_filter_risk": "Alto",
        "dashboard_filter_region": "Latam",
    }

    reset_filter_state(state, date(2026, 10, 1), date(2026, 10, 20))

    assert state == {
        "dashboard_filter_dates": (date(2026, 10, 1), date(2026, 10, 20)),
        "dashboard_filter_risk": "Todos",
        "dashboard_filter_region": "Todas",
    }
