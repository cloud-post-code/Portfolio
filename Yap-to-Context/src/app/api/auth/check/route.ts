import { timingSafeEqual } from "crypto";
import { NextRequest } from "next/server";
import { z } from "zod";
import { getAuthSecret } from "@/lib/auth";

export const runtime = "nodejs";

const bodySchema = z.object({
  secret: z.string().min(1),
});

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

export async function POST(req: NextRequest) {
  const json = await req.json().catch(() => null);
  const parsed = bodySchema.safeParse(json);
  if (!parsed.success) {
    return Response.json({ error: "Invalid body" }, { status: 400 });
  }

  let expected: string;
  try {
    expected = getAuthSecret();
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Server not configured";
    return Response.json({ error: msg }, { status: 503 });
  }

  if (!timingSafeStringEq(parsed.data.secret.trim(), expected)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  return Response.json({ ok: true });
}
