import { timingSafeEqual } from "crypto";
import type { NextRequest } from "next/server";

/** The single sign-in password (Railway env var). Throws if missing/empty. */
export function getAuthSecret(): string {
  const v = process.env.AUTH_SECRET?.trim();
  if (!v) {
    throw new Error(
      "AUTH_SECRET is not set. Add it as a Railway service variable (or in .env locally).",
    );
  }
  return v;
}

export function hasAuthSecret(): boolean {
  return !!process.env.AUTH_SECRET?.trim();
}

function timingSafeStringEq(a: string, b: string): boolean {
  const ba = Buffer.from(a);
  const bb = Buffer.from(b);
  if (ba.length !== bb.length) return false;
  try {
    return timingSafeEqual(ba, bb);
  } catch {
    return false;
  }
}

function readBearer(req: NextRequest): string | null {
  const direct = req.headers.get("x-api-key")?.trim();
  if (direct) return direct;
  const auth = req.headers.get("authorization");
  if (auth && auth.startsWith("Bearer ")) {
    const t = auth.slice(7).trim();
    return t || null;
  }
  return null;
}

/**
 * Server-side guard for API routes.
 * Returns a 401 `Response` to short-circuit the handler, or `null` when authorized.
 */
export async function assertAuthorized(
  req: NextRequest,
): Promise<Response | null> {
  let secret: string;
  try {
    secret = getAuthSecret();
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Server not configured";
    return Response.json({ error: msg }, { status: 503 });
  }

  const token = readBearer(req);
  if (!token || !timingSafeStringEq(token, secret)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  return null;
}
