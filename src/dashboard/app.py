import os
from datetime import date

import streamlit as st

from src.dashboard.api_client import (
    check_api_health,
    create_demo_shipment_payload,
    predict_shipment,
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
RISK_LEVELS = ["Todos", "Alto", "Medio", "Bajo"]
REGION_OPTIONS = ["Todas", "Norte", "Centro", "Sur", "Europa", "Latam"]


def build_demo_summary() -> dict[str, int | float | str]:
    return {
        "shipments": 1_284,
        "high_risk": 186,
        "average_probability": 0.41,
        "critical_regions": 3,
    }


def build_demo_region_risk() -> dict[str, float]:
    return {"Norte": 0.62, "Centro": 0.48, "Sur": 0.71, "Europa": 0.35, "Latam": 0.69}


def build_demo_points() -> list[dict[str, float]]:
    return [
        {"lat": 41.3851, "lon": 2.1734},
        {"lat": 40.4168, "lon": -3.7038},
        {"lat": 36.7194, "lon": -4.4200},
        {"lat": 39.4699, "lon": -0.3763},
        {"lat": -34.6037, "lon": -58.3816},
    ]


def build_demo_shipments() -> list[dict[str, str]]:
    return [
        {"ID": "ENV-1024", "Región": "Norte", "Riesgo": "Alto", "Probabilidad": "0.72", "Estado": "Pendiente"},
        {"ID": "ENV-1030", "Región": "Sur", "Riesgo": "Medio", "Probabilidad": "0.54", "Estado": "Monitoreado"},
        {"ID": "ENV-1048", "Región": "Latam", "Riesgo": "Alto", "Probabilidad": "0.68", "Estado": "Prioridad"},
        {"ID": "ENV-1051", "Región": "Centro", "Riesgo": "Bajo", "Probabilidad": "0.22", "Estado": "OK"},
    ]


st.set_page_config(
    page_title="Torre de Control | Smart Supply Chain Risk AI",
    page_icon="🚚",
    layout="wide",
)

with st.sidebar:
    st.header("Filtros")
    st.date_input("Rango de fechas", value=(date(2026, 10, 1), date(2026, 10, 20)))
    st.selectbox("Nivel de riesgo", RISK_LEVELS)
    st.selectbox("Región", REGION_OPTIONS)
    st.button("Actualizar datos", use_container_width=True)

st.title("Torre de Control")
st.caption("Smart Supply Chain Risk AI · Monitorización del riesgo logístico")

health = check_api_health(API_BASE_URL)
if health.available:
    st.success(health.detail)
else:
    st.error(health.detail)

summary = build_demo_summary()
region_risk = build_demo_region_risk()
recent_shipments = build_demo_shipments()

st.subheader("Resumen ejecutivo")
kpis = st.columns(4)
for column, label, value, help_text in zip(
    kpis,
    (
        "Envíos monitorizados",
        "Riesgo alto",
        "Probabilidad media",
        "Regiones críticas",
    ),
    (
        f"{summary['shipments']}",
        f"{summary['high_risk']}",
        f"{summary['average_probability']:.2f}",
        f"{summary['critical_regions']}",
    ),
    (
        "Total de envíos actualmente bajo seguimiento en la torre de control.",
        "Número de envíos con riesgo alto según el último conjunto de predicciones.",
        "Probabilidad media estimada de retraso frente a SLA.",
        "Número de regiones con riesgo acumulado por encima del umbral.",
    ),
):
    column.metric(label, value, help=help_text)

st.subheader("Estado de la plataforma")
status_columns = st.columns(3)
with status_columns[0]:
    st.markdown("#### API")
    st.info("Disponibilidad: " + ("OK" if health.available else "Sin datos"))
with status_columns[1]:
    st.markdown("#### Modelo ML")
    st.success("Artefacto cargado en la API (XGBoost).")
with status_columns[2]:
    st.markdown("#### Datos")
    st.info("El formulario usa el contrato /predict de la API.")

st.subheader("Análisis de riesgo")
map_column, risk_column = st.columns(2)

with map_column:
    st.markdown("#### Mapa de riesgo")
    st.map(build_demo_points())
    st.caption("Puntos de ejemplo para el mapa. Se conectará con geolocalización real cuando el backend lo publique.")

with risk_column:
    st.markdown("#### Riesgo por región")
    st.bar_chart(region_risk)
    st.caption("Agregación regional de ejemplo. El contrato real llega con los endpoints del backend.")

st.subheader("Prueba rápida del contrato de predicción")
shipment_payload = create_demo_shipment_payload()
with st.form("demo_prediction_form"):
    st.write("Formulario de prueba para el contrato actual de suministro")
    order_date = st.date_input("Fecha del pedido", value=date.today())
    shipping_mode = st.selectbox("Modo de envío", ["First Class", "Same Day", "Second Class", "Standard Class"])
    customer_segment = st.selectbox("Segmento", ["Consumer", "Corporate", "Home Office"])
    market = st.selectbox("Mercado", ["Africa", "Europe", "LATAM", "Pacific Asia", "USCA"])
    order_region = st.selectbox(
        "Región",
        [
            "Canada",
            "Caribbean",
            "Central Africa",
            "Central America",
            "Central Asia",
            "East Africa",
            "East of USA",
            "Eastern Asia",
            "Eastern Europe",
            "North Africa",
            "Northern Europe",
            "Oceania",
            "South America",
            "South Asia",
            "South of  USA",
            "Southeast Asia",
            "Southern Africa",
            "Southern Europe",
            "US Center",
            "West Africa",
            "West Asia",
            "West of USA",
            "Western Europe",
        ],
    )
    item_count = st.slider("Nº de líneas de pedido", min_value=1, max_value=5, value=2)

    items = []
    for index in range(item_count):
        st.markdown(f"### Línea {index + 1}")
        item = {
            "product_category_id": st.number_input(
                f"Category id {index + 1}",
                min_value=1,
                max_value=100,
                value=shipment_payload["order_items"][index % len(shipment_payload["order_items"])]["product_category_id"],
                key=f"category_{index}",
            ),
            "product_price": st.number_input(
                f"Precio línea {index + 1}",
                min_value=1.0,
                max_value=500.0,
                value=shipment_payload["order_items"][index % len(shipment_payload["order_items"])]["product_price"],
                key=f"price_{index}",
            ),
            "order_item_quantity": st.number_input(
                f"Cantidad línea {index + 1}",
                min_value=1,
                max_value=20,
                value=shipment_payload["order_items"][index % len(shipment_payload["order_items"])]["order_item_quantity"],
                key=f"qty_{index}",
            ),
            "order_item_discount": st.number_input(
                f"Descuento línea {index + 1}",
                min_value=0.0,
                max_value=100.0,
                value=shipment_payload["order_items"][index % len(shipment_payload["order_items"])]["order_item_discount"],
                key=f"discount_{index}",
            ),
        }
        items.append(item)

    submitted = st.form_submit_button("Simular predicción")
    if submitted:
        payload = {
            "order_date": f"{order_date.isoformat()}T10:00:00",
            "shipping_mode": shipping_mode,
            "customer_segment": customer_segment,
            "market": market,
            "order_region": order_region,
            "order_items": items,
        }
        prediction = predict_shipment(API_BASE_URL, payload)
        st.subheader("Resultado de la simulación")
        if not prediction.available or prediction.data is None:
            st.error(prediction.detail)
        else:
            data = prediction.data
            st.metric("Probabilidad de retraso", f"{data['delay_probability']:.2%}")
            risk_label = "Alto" if data.get("delay_risk") else "Bajo"
            st.info(f"Nivel: {risk_label} · Umbral: {data['threshold']:.2f} · {data['interpretation']}")

st.subheader("Envíos recientes")
st.table(recent_shipments)
st.caption(
    "Los datos actuales son de ejemplo para preparar el dashboard. Cuando el backend publique el endpoint real, "
    "se sustituirá por consultas definitivas."
)
