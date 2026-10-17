# Smart Supply Chain Risk AI

Torre de Control Inteligente de Logística y Cadena de Suministro B2B.

## Objetivo

Desarrollar un sistema que prediga el riesgo de retraso de un envío desde la creación del pedido. La solución ayudará a los ERP/WMS y a los gestores de tráfico a actuar antes del despacho mediante una API y un dashboard.

## Miembros

- Adrián Matemalas Manzanaro
- Raúl Romero Montoro
- Raúl Rincón Ortiz

## Organización del repositorio

- `docs/`: entregables y documentación.
- `data/`: datos de apoyo del proyecto.
- `environment/`: configuración para reproducir el entorno.
- `src/`: código de datos, modelo, API y dashboard.

El equipo trabaja con GitFlow: las tareas se desarrollan en ramas `feature/<tarea>`, se revisan mediante PR hacia `develop` y las entregas se integran en `main` con su correspondiente *tag*.

## Arquitectura resumida

![Arquitectura](docs/arquitectura.png)

## Estructura

```text
Grupo7-TFM-PlanetaFP/
├── data/
├── docs/
├── environment/
├── src/
│   ├── api/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── webhooks.py
│   └── dashboard/
│       └── app.py
├── tests/
├── Dockerfile
├── docker-compose.yml
├── README.md
└── .gitignore
```

## API de ingesta y predicción

La API FastAPI expone:

- `GET /health`: comprobación de disponibilidad del servicio.
- `POST /ingest`: valida un envío y devuelve sus datos normalizados. Esta primera
  versión no persiste ni reenvía los registros.
- `POST /predict`: valida el mismo contrato de entrada que `/ingest`. Devuelve
  `503 Service Unavailable` hasta que se configure el artefacto del modelo; no
  genera predicciones simuladas.

El contrato inicial contiene solo atributos disponibles al crear el pedido y
excluye identificadores personales y variables de resultado que podrían causar
fuga de información. Es un contrato inicial y deberá alinearse con las features
finales del pipeline de entrenamiento.

### Contrato frente a DataCo

El dataset se obtiene de
[DataCo SMART SUPPLY CHAIN FOR BIG DATA ANALYSIS](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis).
La API se ha contrastado con `DataCoSupplyChainDataset.csv` (53 columnas,
180.519 filas y 65.752 pedidos distintos). Cada fila representa un artículo de
pedido; los pedidos tienen entre uno y cinco artículos en este dataset. Por eso,
la API recibe atributos comunes del pedido y una lista `order_items`. El CSV no
se incluye en el repositorio.

| Campo de API | Columna de DataCo |
| --- | --- |
| `order_date` | `order date (DateOrders)`; la API requiere fecha ISO 8601 |
| `shipping_mode` | `Shipping Mode` |
| `customer_segment` | `Customer Segment` |
| `market` | `Market` |
| `order_region` | `Order Region` |
| `order_items[].product_category_id` | `Product Category Id` |
| `order_items[].product_price` | `Order Item Product Price` |
| `order_items[].order_item_quantity` | `Order Item Quantity` |
| `order_items[].order_item_discount` | `Order Item Discount` |

La etiqueta objetivo es `Late_delivery_risk`, pero no se acepta como dato de
entrada. También se excluyen del contrato las variables posteriores al envío
(por ejemplo, `Days for shipping (real)`, `Delivery Status` y
`shipping date (DateOrders)`), además de datos personales y vinculables como
`Customer Email`, `Customer Fname`, `Customer Lname`, `Customer Password`,
`Customer Street`, `Customer Zipcode`, `Customer Id` y `Order Customer Id`.
El CSV crudo no se debe subir al repositorio; su ruta local está protegida en
`.gitignore`. En DataCo las filas de un mismo pedido comparten la etiqueta
`Late_delivery_risk`; el pipeline de ML debe confirmar si entrenará por artículo
o agregará las features por pedido antes de conectar el modelo a `/predict`.

### Alertas por webhook

El módulo `src.api.webhooks` ofrece `send_high_risk_alert`, que envía por HTTP
POST el JSON de la predicción cuando `Risk_Level` es `"Alto"`. La URL se
configura con `WEBHOOK_URL`; `WEBHOOK_MAX_ATTEMPTS` permite ajustar el número
de intentos (por defecto, 3). Se reintentan fallos de transporte y respuestas
transitorias HTTP 408, 429 y 5xx; otros errores HTTP se notifican al llamador.
El envío está desacoplado de `/predict` hasta que el modelo esté integrado y se
acuerde el contrato final de su respuesta.

Para ejecutar localmente desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r environment\requirements.txt
uvicorn src.api.main:app --reload
```

La documentación interactiva está disponible en `http://127.0.0.1:8000/docs`.
Para ejecutar las pruebas: `python -m pytest`.
Para ejecutar el panel localmente, instala también
`environment\requirements-dashboard.txt` y usa
`streamlit run src\dashboard\app.py`.

### Ejecución con Docker

Docker Compose levanta la API y el panel Streamlit inicial. El panel comprueba
la disponibilidad de la API mediante la red interna de Compose; los datos
crudos y las pruebas se excluyen del contexto de construcción.

```powershell
docker compose up --build
```

La API queda disponible en `http://localhost:8000` y el dashboard en
`http://localhost:8501`. Compose espera a que la API supere su healthcheck antes
de iniciar el panel. Los puertos del host se pueden cambiar con las variables
`API_PORT` y `DASHBOARD_PORT`.

El Dockerfile define objetivos de construcción independientes (`api` y
`dashboard`) sobre `python:3.10-slim`. El dashboard actual es un punto de
integración mínimo para TASK-09; la interfaz funcional se completará con el
equipo de Frontend/BI.
