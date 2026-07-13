FROM node:22-alpine

WORKDIR /app/frontend

COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml /app/frontend/
COPY frontend/apps/studio-app/package.json /app/frontend/apps/studio-app/
COPY frontend/apps/public-site/package.json /app/frontend/apps/public-site/
COPY frontend/packages/builder/package.json /app/frontend/packages/builder/
COPY frontend/packages/schema/package.json /app/frontend/packages/schema/
COPY frontend/packages/site-shell/package.json /app/frontend/packages/site-shell/
COPY frontend/packages/styles/package.json /app/frontend/packages/styles/
COPY frontend/packages/ui/package.json /app/frontend/packages/ui/

RUN corepack enable && pnpm install --frozen-lockfile

COPY frontend /app/frontend

CMD ["pnpm", "--filter", "@flowform/studio-app", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
