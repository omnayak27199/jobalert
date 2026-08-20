FROM node:20-alpine AS builder

WORKDIR /app

# Copy lockfile + npm retry settings before source (better layer cache).
COPY package*.json .npmrc ./
RUN --mount=type=cache,target=/root/.npm \
    set -e; \
    for attempt in 1 2 3 4 5; do \
      echo "npm ci attempt ${attempt}/5..."; \
      npm ci --no-audit --no-fund && exit 0; \
      echo "npm ci failed (network?), waiting 20s before retry..."; \
      sleep 20; \
    done; \
    echo "npm ci failed after 5 attempts"; \
    exit 1

COPY . .

ARG API_URL=http://backend:8000
ENV API_URL=$API_URL

RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV API_URL=http://backend:8000

CMD ["node", "server.js"]
