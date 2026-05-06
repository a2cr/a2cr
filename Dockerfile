FROM node:22-slim AS web-build

WORKDIR /app/web
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_A2CR_API_BASE
ARG VITE_A2CR_SERVICE_URL
COPY web/package*.json ./
RUN npm ci
COPY web ./
RUN VITE_SUPABASE_URL="$VITE_SUPABASE_URL" \
    VITE_SUPABASE_ANON_KEY="$VITE_SUPABASE_ANON_KEY" \
    VITE_A2CR_API_BASE="$VITE_A2CR_API_BASE" \
    VITE_A2CR_SERVICE_URL="$VITE_A2CR_SERVICE_URL" \
    npm run build

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=web-build /app/web/dist ./web/dist

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
