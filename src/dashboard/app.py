import os
from datetime import date

import streamlit as st

from src.dashboard.api_client import (
    check_api_health,
    create_demo_shipment_payload,
    predict_shipment,
)
from src.dashboard.filters import (
    DEMO_SHIPMENTS,
    demo_map_points,
    demo_region_risk,
    filter_demo_shipments,
    summarize_demo_shipments,
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
RISK_LEVELS = ["Todos", "Alto", "Medio", "Bajo"]


st.set_page_config(
    page_title="Torre de Control | Smart Supply Chain Risk AI",
    page_icon="🚚",
    layout="wide",
)

with st.sidebar:
    st.header("Filtros")
    min_date = min(shipment["order_date"] for shipment in DEMO_SHIPMENTS)
    max_date = max(shipment["order_date"] for shipment in DEMO_SHIPMENTS)
    selected_dates = st.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    selected_risk = st.selectbox("Nivel de riesgo", RISK_LEVELS)
    region_options = [
        "Todas",
        *sorted({shipment["region"] for shipment in DEMO_SHIPMENTS}),
    ]
    selected_region = st.selectbox("Región", region_options)

if isinstance(selected_dates, (tuple, list)):
    start_date = selected_dates[0] if selected_dates and selected_dates[0] else min_date
    end_date = (
        selected_dates[1]
        if len(selected_dates) > 1 and selected_dates[1]
        else selected_dates[0]
        if selected_dates and selected_dates[0]
        else max_date
    )
else:
    start_date = end_date = selected_dates

filtered_shipments = filter_demo_shipments(
    DEMO_SHIPMENTS,
    start_date,
    end_date,
    selected_risk,
    selected_region,
)
summary = summarize_demo_shipments(filtered_shipments)
region_risk = demo_region_risk(filtered_shipments)
map_points = demo_map_points(filtered_shipments)

st.title("Torre de Control")
st.caption("Smart Supply Chain Risk AI · Monitorización del riesgo logístico")
st.info(
    "Los filtros se aplican a los envíos de ejemplo; el dashboard aún no consulta "
    "un histórico real de la API."
)

health = check_api_health(API_BASE_URL)
if health.available:
    st.success(health.detail)
else:
    st.error(health.detail)

st.subheader("Resumen ejecutivo")
kpis = st.columns(4)
for column, label, value, help_text in zip(
    kpis,
    (
        "Envíos de ejemplo",
        "En riesgo alto",
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
    if map_points:
        st.map(map_points)
    else:
        st.info("No hay envíos de ejemplo para los filtros seleccionados.")
    st.caption("Ubicaciones orientativas de ejemplo, no geolocalización real.")

with risk_column:
    st.markdown("#### Riesgo por región")
    if region_risk:
        st.bar_chart(region_risk)
    else:
        st.info("No hay datos para mostrar con los filtros seleccionados.")
    st.caption("Probabilidad media de los envíos de ejemplo filtrados por región.")

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
if filtered_shipments:
    st.table(
        [
            {
                "ID": shipment["shipment_id"],
                "Fecha": shipment["order_date"].isoformat(),
                "Región": shipment["region"],
                "Riesgo": shipment["risk"],
                "Probabilidad": f"{shipment['probability']:.2f}",
                "Estado": shipment["status"],
            }
            for shipment in filtered_shipments
        ]
    )
else:
    st.info("No hay envíos de ejemplo que coincidan con los filtros seleccionados.")
st.caption(
    "Los controles de fecha, riesgo y región filtran esta tabla, los indicadores y los gráficos."
)
