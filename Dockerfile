FROM python:3.10-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app

FROM base AS api

COPY environment/requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt
COPY --chown=app:app src/api/ ./src/api/
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS dashboard

COPY environment/requirements-dashboard.txt .
RUN pip install --no-cache-dir -r requirements-dashboard.txt
COPY --chown=app:app src/dashboard/ ./src/dashboard/
USER 10001:10001
EXPOSE 8501
CMD ["streamlit", "run", "src/dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
