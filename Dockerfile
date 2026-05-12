FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[notifications]"

COPY . .

RUN mkdir -p /data

EXPOSE 8400
CMD ["python", "-m", "observatory.cli", "serve"]
