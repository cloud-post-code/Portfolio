/**
 * Deployment helpers for Railway and similar hosts.
 */

export function productionLikeDeployment(): boolean {
  return (
    process.env.NODE_ENV === "production" ||
    !!process.env.RAILWAY_ENVIRONMENT ||
    !!process.env.RAILWAY_PROJECT_ID
  );
}

/**
 * Fail fast at boot if a production-like deployment is missing the single
 * sign-in secret. Local dev is allowed to run without one (middleware lets
 * /api/* through and the home page won't try to sign in).
 */
export function assertAuthSecretInProduction(): void {
  if (!productionLikeDeployment()) return;
  const v = process.env.AUTH_SECRET?.trim();
  if (v) return;
  throw new Error(
    "AUTH_SECRET is not set. Add it as a Railway service variable and redeploy.",
  );
}
