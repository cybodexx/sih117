FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --offline || npm install
COPY . .
# Browser API base. "" = same-origin → the Next rewrite proxies /api/* to the
# API container (the only egress surface in airgapped mode). Set to
# http://localhost:8000 for a direct-host dev image.
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Install nginx for API proxying (air-gapped mode requires same-origin /api/*)
RUN apk add --no-cache nginx

COPY nginx.conf /etc/nginx/nginx.conf

# Start nginx (port 3000) and Next.js (port 3001) via a simple script
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'PORT=3001 node server.js > /app/nextjs.log 2>&1 &' >> /app/start.sh && \
    echo 'nginx -g "daemon off;"' >> /app/start.sh && \
    chmod +x /app/start.sh

EXPOSE 3000
CMD ["/app/start.sh"]