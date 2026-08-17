# =============================================================================
# Builds the single combined React app (user site + admin panel under /admin)
# and serves it via nginx, which also reverse-proxies API/WebSocket traffic
# to the backend.
# =============================================================================

# ---- Stage 1: build ----------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app
# No package-lock.json yet since this is a newly merged app — run `npm install`
# once locally in Frontend/app to generate one, then switch this to
# `npm ci` for reproducible builds.
COPY Frontend/app/package.json ./
RUN npm install
COPY Frontend/app/ ./
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# ---- Stage 2: nginx runtime ----------------------------------------------
FROM nginx:1.27-alpine

RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
