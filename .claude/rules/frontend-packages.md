---
paths: frontend/packages/**/*.{ts,tsx}
---

# Shared packages rules

These packages are consumed by both `studio-app` and `public-site` — changes here affect both apps.

- `@flowform/ui` — shared component library; keep components generic and app-agnostic
- `@flowform/styles` — design tokens and Tailwind config; changes ripple across all apps
- `@flowform/site-shell` — SiteHeader and nav constants
- `@flowform/builder` — survey/question builder

Avoid importing from app-level code (`studio-app`, `public-site`) — packages must not depend on apps.
