# Qurator backend — FastAPI + Qiskit. Serves the cached RunArtifact out of the box; runs the live
# probe → QAOA → apply pipeline when a Postgres+HypoPG database is reachable (see env vars).
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

# Install deps first (better layer caching), then the package.
COPY pyproject.toml ./
COPY qurator ./qurator
RUN uv pip install --system --no-cache -e ".[quantum]"

# Bundle the known-good demo artifact so /api/run works with no database attached.
COPY cache ./cache

ENV QURATOR_PG_HOST=db \
    QURATOR_PG_PORT=5432 \
    PYTHONUNBUFFERED=1

EXPOSE 8088
CMD ["uvicorn", "qurator.api:app", "--host", "0.0.0.0", "--port", "8088"]
