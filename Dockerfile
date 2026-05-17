FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc gfortran libgeos-dev libproj-dev proj-data \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml ./
COPY src/ ./src/

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir .

# ── runtime image ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-c1v5 libproj25 proj-data \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

RUN useradd -u 1000 -m lutgen
USER lutgen

ENTRYPOINT ["python", "-m", "lutgen"]
