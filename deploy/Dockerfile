FROM node:20-bookworm-slim AS webapp-build

WORKDIR /app/webapp

COPY webapp/package.json webapp/package-lock.json* ./
RUN npm ci

COPY webapp/ ./
RUN npm run build


WORKDIR /app
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim


RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY coach.py repcli.py log.py obs_client.py shared.py ./
COPY src ./src
COPY config.yml ./config.yml
COPY templates ./templates
COPY --from=webapp-build /app/webapp/dist ./webapp/dist

RUN uv sync --no-dev
RUN mkdir -p logs obs

EXPOSE 8765

CMD ["uv", "run", "python", "-m", "src.api"]