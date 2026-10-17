import os
from urllib.error import URLError
from urllib.request import urlopen

import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="Smart Supply Chain Risk AI", page_icon="🚚")
st.title("Smart Supply Chain Risk AI")
st.caption("Torre de Control Inteligente de Logística y Cadena de Suministro")

try:
    with urlopen(f"{API_BASE_URL}/health", timeout=3) as response:
        if response.status == 200:
            st.success("API FastAPI disponible")
        else:
            st.error(f"La API respondió con HTTP {response.status}")
except URLError as exc:
    st.error(f"No se pudo conectar con la API ({API_BASE_URL}): {exc.reason}")

st.info("Panel inicial de integración. Los indicadores y vistas de riesgo están pendientes.")
