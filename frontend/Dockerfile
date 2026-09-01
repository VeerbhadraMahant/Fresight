# FreightSight dashboard — build, then serve as static files via nginx.
FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Empty API base -> the app calls same-origin /api, which nginx proxies to the
# backend. Only set this if the API is on a different origin (needs CORS):
#   docker build --build-arg VITE_API_BASE=https://api.example.com .
ARG VITE_API_BASE=""
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

FROM nginx:1.27-alpine AS serve
# nginx renders templates through envsubst on startup
ENV API_UPSTREAM=backend:8000
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
