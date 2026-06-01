// frontend/apps/studio-app/src/auth/redirect.ts
export function getAuthReturnTo(): string {
  const returnTo = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  return returnTo || "/";
}
