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
- `data/`: datos del proyecto, separados en `raw/` (crudos) y `cleaned/` (limpios, generados); ambos directorios se ignoran por git.
- `environment/`: configuración para reproducir el entorno.
- `src/`: código de datos, modelo, API y dashboard.

El equipo trabaja con GitFlow: las tareas se desarrollan en ramas `feature/<tarea>`, se revisan mediante PR hacia `develop` y las entregas se integran en `main` con su correspondiente *tag*.

## Arquitectura resumida

![Arquitectura](docs/arquitectura.png)

## Estructura

```text
Grupo7-TFM-PlanetaFP/
├── data/
│   ├── raw/        # datos crudos, p. ej. DataCoSupplyChainDataset.csv (gitignored)
│   └── cleaned/    # datos limpios generados por el pipeline (gitignored)
├── docs/
├── environment/
├── src/
│   ├── api/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── webhooks.py
│   ├── dashboard/
│   │   └── app.py
│   ├── data/
│   │   └── clean.py
│   └── ml/
│       ├── config.yaml
│       ├── config.py
│       ├── model.py
│       ├── evaluate.py
│       ├── pipeline.py
│       ├── compare.py
│       └── train.py
├── tests/
├── environment/
│   ├── requirements.txt
│   ├── requirements-api.txt
│   ├── requirements-dashboard.txt
│   └── requirements-ml.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## API de ingesta y predicción

La API FastAPI expone:

- `GET /health`: comprobación de disponibilidad del servicio.
- `POST /ingest`: valida un envío, lo transforma con las features del modelo y
  devuelve los datos normalizados junto con la predicción. No persiste los
  registros.
- `POST /predict`: valida el mismo contrato y devuelve la predicción real del
  modelo. Ambos endpoints responden `503 Service Unavailable` si el artefacto
  no está configurado; no generan predicciones simuladas.

La respuesta indica `delay_risk` como aviso preventivo cuando la probabilidad
alcanza el umbral (0,5 por ahora); no confirma que el pedido vaya a retrasarse.
También devuelve la probabilidad y el umbral aplicado. El equipo revisará el
equilibrio entre falsas alarmas y retrasos no detectados antes de cambiarlo.

El contrato inicial contiene solo atributos disponibles al crear el pedido y
excluye identificadores personales y variables de resultado que podrían causar
fuga de información. La API transforma estos campos al mismo conjunto de
features del modelo antes de ejecutar la inferencia.

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
`Late_delivery_risk`; el modelo actual entrena y predice a nivel de pedido.

### Alertas por webhook

El módulo `src.api.webhooks` ofrece `send_high_risk_alert`, que envía por HTTP
POST el JSON de la predicción cuando `Risk_Level` es `"Alto"`. La URL se
configura con `WEBHOOK_URL`; `WEBHOOK_MAX_ATTEMPTS` permite ajustar el número
de intentos (por defecto, 3). Se reintentan fallos de transporte y respuestas
transitorias HTTP 408, 429 y 5xx; otros errores HTTP se notifican al llamador.
El envío de alertas sigue desacoplado de `/ingest` y `/predict`; falta acordar
el contrato de las alertas antes de activar ese flujo.

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
`dashboard`) sobre `python:3.10-slim`. El dashboard actual es la base de la Torre de Control: comprueba la salud de
la API y reserva las vistas de indicadores operativos, riesgo regional y envíos
recientes. Muestra estados vacíos explícitos en lugar de inventar predicciones.
La API ya ofrece inferencia de riesgo por envío. Todavía no ofrece un histórico,
agregados ni coordenadas para alimentar las vistas de mapa e indicadores; estas
se conectarán cuando estén disponibles los datos y contratos correspondientes.

## Entrenamiento del modelo (XGBoost) y comparación con LightGBM

El código de entrenamiento vive en `src/ml`, separado de la API y del panel
porque tiene un ciclo de vida distinto (entrenamiento *offline* por lotes, no
desplegable). La imagen de API instala únicamente las dependencias de inferencia
(NumPy, pandas y XGBoost), no las herramientas de entrenamiento y descarga de
datos. Los objetivos de construcción del Dockerfile (`api`, `dashboard`) siguen
siendo independientes.

`src/data` limpia y agrega el CSV de DataCo a nivel de pedido. `src/ml` carga el
fichero resultante, entrena y guarda el artefacto.

**Contrato de entrada:** un fichero Parquet a nivel de pedido con una columna
por feature (incluido `order_timestamp`, segundos Unix para ordenar
temporalmente) y la columna `Late_delivery_risk` (0/1). Su ruta se define en
`config.yaml` (`data.cleaned_path`, por defecto `data/cleaned/orders.parquet`).

Los datos se organizan en `data/raw/` (ficheros fuente, como el CSV de Kaggle)
y `data/cleaned/` (salida del pipeline de datos, regenerable). Ambos directorios
están ignorados por git y solo se conservan sus `.gitkeep`.

Objetivo: predecir la probabilidad de retraso de un envío. El modelo principal
es `XGBClassifier` con `objective: binary:logistic`, que produce
`P(retraso) ∈ [0,1]`. El porcentaje de riesgo es `100 × P`, que es lo que
`/predict` expondrá como `delay_probability` (`delay_risk` se deriva con el
umbral `model.threshold`, por defecto 0.5). LightGBM se mantiene como modelo
alternativo de comparación, no como artefacto desplegado.

### Preparación de DataCo

El fichero de entrenamiento es `data/raw/DataCoSupplyChainDataset.csv`.
`DescriptionDataCoSupplyChain.csv` sirve como diccionario de datos y
`tokenized_access_logs.csv` es una fuente distinta, no utilizada para predecir
retrasos de pedidos. Instala `environment/requirements-ml.txt` (incluye la
  librería `kagglehub`) y descarga los tres CSV desde la raíz:


```bash
python -m src.data.download
```

No se requieren credenciales de Kaggle para descargar el dataset. Si lo necesitas
para recursos privados, configura `KAGGLE_API_TOKEN` o `kaggle.json`.
Usa `--output` para cambiar el destino (por defecto `data/raw/`) y
`--force` para volver a descargarlos.

`python -m src.data.clean` y `python -m src.ml.train --raw-data ...` descargan
automáticamente los CSV que falten antes de limpiar; añade `--no-download` para
desactivar esa descarga. Para regenerar solo el Parquet:

```powershell
python -m src.data.clean
```

Esto genera el Parquet configurado. Para limpiar y entrenar en un solo paso:

```powershell
python -m src.ml.train --raw-data data/raw/DataCoSupplyChainDataset.csv
```

La limpieza valida la etiqueta y los atributos compartidos por pedido, agrega
las líneas a una fila por `Order Id` y guarda el Parquet definido en
`src/ml/config.yaml`. Solo conserva señales disponibles al crear el pedido:
timestamp y componentes derivados de la fecha, modo de envío, segmento, mercado,
región y agregados de sus artículos. Excluye identificadores, datos personales y
variables posteriores al envío. Se puede cambiar la entrada o salida con
`--input` y `--output`.

El entrenamiento ordena los pedidos cronológicamente y reserva los segmentos
más recientes para validación (`validation_size`) y prueba final (`test_size`),
ambos configurables en `config.yaml`. Solo el segmento de validación se usa
para *early stopping*; las métricas se calculan una vez sobre el segmento de
prueba, que no participa en el entrenamiento.
Si ya existe un Parquet generado con la versión anterior de la limpieza,
regénéralo con `python -m src.data.clean` antes de entrenar para incluir
`order_timestamp`.

`src.data.clean.build_shipment_features` aplica la misma agregación y
codificación al payload de un pedido, alineando las columnas con la lista de
features del artefacto. Las categorías no vistas se codifican como cero en las
columnas categóricas aprendidas. La API carga el modelo nativo de XGBoost y su
metadata al arrancar; `MODEL_ARTIFACT_DIR` permite cambiar el directorio, cuyo
valor predeterminado es `src/ml/artifacts`.

Estructura:

```text
src/ml/
├── config.yaml     # cleaned_path, hiperparámetros, split, umbral, rutas
├── config.py       # carga de config.yaml
├── model.py        # XGBClassifier y LGBMClassifier: build/train
├── evaluate.py     # métricas y conversión probabilidad → porcentaje
├── pipeline.py     # load limpio → split → train → evaluate → save
├── compare.py      # XGBoost vs LightGBM sobre el mismo split
└── train.py        # punto de entrada CLI
```

Para entrenar directamente desde un fichero ya limpio:

```bash
pip install -r environment/requirements-ml.txt
python -m src.ml.train
```

Los artefactos se guardan en `src/ml/artifacts/` (ignorado por git):

- `delay_risk_xgb.json`: modelo en formato nativo de XGBoost, portable entre
  versiones. Se carga con `xgb.XGBClassifier().load_model(...)`.
- `delay_risk_xgb.joblib`: el `XGBClassifier` completo serializado con joblib,
  listo para usar desde Python/sklearn con `joblib.load(...)`.
- `model_metadata.json`: features, métricas, umbral, parámetros y nombres de los
  ficheros del modelo.

Cuando se integre el modelo en `/predict`, se carga desde ese directorio.

### Comparación con LightGBM

`src/ml/compare.py` entrena un `LGBMClassifier` alternativo y lo compara con
XGBoost sobre el mismo split temporal, el mismo `seed` y una capacidad
equivalente (`max_depth: 6` / `num_leaves: 63`, mismo presupuesto de árboles,
`learning_rate`, `subsample`, `colsample_bytree` y `reg_lambda`). Ambos usan
solo el segmento de validación para *early stopping* y se evalúan una única vez
sobre el segmento de prueba.

```bash
python -m src.ml.compare
```

El comando guarda `src/ml/artifacts/model_comparison.json` con las métricas de
cada modelo, sus hiperparámetros, el tiempo de entrenamiento/predicción y un
veredicto. La decisión se configura en `config.yaml`:

- `comparison.primary_metric` (`roc_auc` por defecto).
- `comparison.min_improvement`: margen mínimo que debe superar LightGBM para
  reemplazar a XGBoost (por defecto `0.005`). Así se evita cambiar de modelo
  por diferencias que puedan ser ruido.

El campeón es XGBoost y el retador LightGBM. Se mantiene XGBoost salvo que
LightGBM mejore la métrica principal al menos en `min_improvement`; el campo
`verdict.reason` del informe deja constancia de la comparación y del tiempo de
entrenamiento de cada alternativa.

FastAPI carga `delay_risk_xgb.json` y `model_metadata.json` desde ese directorio.
Si falta alguno, la API puede arrancar y `/health` seguirá comprobando el
servicio, pero `/ingest` y `/predict` responderán `503` hasta disponer de ambos.
Docker monta `src/ml/artifacts/` en solo lectura; puedes indicar otra carpeta
local con `MODEL_ARTIFACT_HOST_DIR`. Entrena o copia el artefacto a esa ruta
antes de ejecutar `docker compose up --build`.
