import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { productionLikeDeployment } from "@/lib/deploy-env";

/**
 * Edge-safe middleware: gate /api/* with a Bearer header matching AUTH_SECRET.
 * HTML routes pass through; the client checks `sessionStorage` and renders the
 * sign-in box when needed.
 */

function isPublicApi(pathname: string, method: string): boolean {
  if (pathname === "/api/auth/check" && method === "POST") return true;
  if (pathname === "/api/auth/status") return true;
  return false;
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

function timingSafeEqualString(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let x = 0;
  for (let i = 0; i < a.length; i++) x |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return x === 0;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (!pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  const secret = process.env.AUTH_SECRET?.trim();

  if (!secret) {
    if (productionLikeDeployment()) {
      return NextResponse.json(
        {
          error:
            "Server misconfigured: set AUTH_SECRET in Railway service variables.",
        },
        { status: 503 },
      );
    }
    return NextResponse.next();
  }

  if (isPublicApi(pathname, request.method)) {
    return NextResponse.next();
  }

  const token = readBearer(request);
  if (!token || !timingSafeEqualString(token, secret)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/api/:path*"],
};
