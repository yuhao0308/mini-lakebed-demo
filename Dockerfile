# ── Stage 1: Build ──
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files first for better layer caching
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

# Copy source
COPY frontend/ ./

# Accept backend URL at build time (Vite bakes env vars into the bundle)
# Set this in Railway: Settings → Variables → VITE_API_BASE_URL=https://your-tunnel.example.com
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ── Stage 2: Serve ──
FROM node:20-alpine AS production

WORKDIR /app

RUN npm install -g serve@14

COPY --from=build /app/dist ./dist

EXPOSE ${PORT:-3000}

# Railway sets PORT automatically
CMD ["sh", "-c", "serve dist -s -l tcp://0.0.0.0:${PORT:-3000}"]
