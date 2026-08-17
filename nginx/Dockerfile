# =============================================================================
# Builds the combined React app (user site + admin panel under /admin) and
# serves it via nginx, which also reverse-proxies API/WebSocket traffic.
# =============================================================================

# ---- Stage 1: build ---------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# package-lock.json is committed for reproducible installs.
COPY Frontend/app/package.json Frontend/app/package-lock.json ./
RUN npm ci

COPY Frontend/app/ ./

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ---- Stage 2: nginx runtime -------------------------------------------------
FROM nginx:1.27-alpine

RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
