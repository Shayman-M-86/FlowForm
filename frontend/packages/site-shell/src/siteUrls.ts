/**
 * Cross-app URL resolution between the Public Site and Studio.
 *
 * Deployed hosts follow one convention: Studio lives on `studio.<public host>`
 * (flow-form.com.au ↔ studio.flow-form.com.au, staging.flow-form.com.au ↔
 * studio.staging.flow-form.com.au). Deriving the sibling origin from the
 * current hostname means one static build works in every environment without
 * extra build-time config. Local dev uses the fixed dev-server ports.
 *
 * When the two apps don't share that convention (e.g. production public site
 * paired with staging Studio), set the sibling origin explicitly at build time:
 *   - public-site: PUBLIC_STUDIO_URL     (e.g. https://studio.staging.flow-form.com.au)
 *   - studio-app:  VITE_PUBLIC_SITE_URL  (e.g. https://flow-form.com.au)
 * Overrides are ignored on local hosts so a shared .env can't break local dev.
 */

export const PUBLIC_SITE_FALLBACK_ORIGIN = "https://flow-form.com.au";
export const STUDIO_FALLBACK_ORIGIN = "https://studio.flow-form.com.au";

const DEV_PUBLIC_SITE_PORT = "4321";
const DEV_STUDIO_PORT = "5174";
const STUDIO_HOST_PREFIX = "studio.";

/** Studio query param that skips the landing page and goes straight to Auth0. */
export const STUDIO_AUTH_PARAM = "auth";
export type StudioAuthIntent = "login" | "signup";

type LocationLike = Pick<Location, "protocol" | "hostname" | "port">;

// Static property access so Vite/Astro can inline the values at build time.
const buildEnv = (import.meta as unknown as { env?: Record<string, string | undefined> }).env;
const STUDIO_URL_OVERRIDE = normaliseOrigin(buildEnv?.PUBLIC_STUDIO_URL);
const PUBLIC_SITE_URL_OVERRIDE = normaliseOrigin(buildEnv?.VITE_PUBLIC_SITE_URL);

function normaliseOrigin(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed.replace(/\/+$/, "") : null;
}

function isLocalHost(hostname: string): boolean {
  return (
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "0.0.0.0" ||
    /^\d{1,3}(\.\d{1,3}){3}$/.test(hostname)
  );
}

function currentLocation(): LocationLike | null {
  return typeof window === "undefined" ? null : window.location;
}

export function resolveStudioOrigin(location: LocationLike | null = currentLocation()): string {
  if (!location) return STUDIO_URL_OVERRIDE ?? STUDIO_FALLBACK_ORIGIN;
  const { protocol, hostname } = location;
  // Auth0 SPA SDK only runs on https or `localhost`; a plain-http LAN/WSL IP
  // origin throws at startup, so local Studio links always use localhost.
  if (isLocalHost(hostname)) return `${protocol}//localhost:${DEV_STUDIO_PORT}`;
  if (STUDIO_URL_OVERRIDE) return STUDIO_URL_OVERRIDE;
  if (hostname.startsWith(STUDIO_HOST_PREFIX)) return `${protocol}//${hostname}`;
  const bareHost = hostname.replace(/^www\./, "");
  return `${protocol}//${STUDIO_HOST_PREFIX}${bareHost}`;
}

export function resolvePublicSiteOrigin(location: LocationLike | null = currentLocation()): string {
  if (!location) return PUBLIC_SITE_URL_OVERRIDE ?? PUBLIC_SITE_FALLBACK_ORIGIN;
  const { protocol, hostname } = location;
  if (isLocalHost(hostname)) return `${protocol}//${hostname}:${DEV_PUBLIC_SITE_PORT}`;
  if (PUBLIC_SITE_URL_OVERRIDE) return PUBLIC_SITE_URL_OVERRIDE;
  if (!hostname.startsWith(STUDIO_HOST_PREFIX)) return `${protocol}//${hostname}`;
  return `${protocol}//${hostname.slice(STUDIO_HOST_PREFIX.length)}`;
}

export function studioUrl(intent?: StudioAuthIntent, location?: LocationLike | null): string {
  const origin = resolveStudioOrigin(location);
  return intent ? `${origin}/?${STUDIO_AUTH_PARAM}=${intent}` : `${origin}/`;
}

export function publicSiteUrl(path = "/", location?: LocationLike | null): string {
  return `${resolvePublicSiteOrigin(location)}${path.startsWith("/") ? path : `/${path}`}`;
}
