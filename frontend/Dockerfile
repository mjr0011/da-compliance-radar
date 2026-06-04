FROM node:20-alpine

# Alpine already ships a non-root `node` user (uid 1000). We reuse it
# rather than creating a custom one — keeps the image small.

WORKDIR /app

# --- Deps cached in their own layer ---
COPY --chown=node:node package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

# --- Source ---
COPY --chown=node:node . .

USER node

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

# Default to dev server; docker-compose.staging.yml overrides with
# `npm run build && npm start` for the production image.
CMD ["npm", "run", "dev"]
