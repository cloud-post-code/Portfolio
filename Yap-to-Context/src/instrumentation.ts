import type * as Bootstrap from "@/db/bootstrap";
import { assertAuthSecretInProduction } from "@/lib/deploy-env";

export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;

  /* webpackIgnore: instrumentation build cannot bundle Node builtins; `npm run build` emits `.next/server/db/bootstrap.cjs` (scripts/build-bootstrap-bundle.mjs). */
  const { runMigrations, seedRootFolders } = (await import(
    /* webpackIgnore: true */
    "./db/bootstrap.cjs" as string
  )) as typeof Bootstrap;
  await runMigrations();
  await seedRootFolders();
  assertAuthSecretInProduction();
}
