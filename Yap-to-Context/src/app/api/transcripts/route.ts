import { desc, ne } from "drizzle-orm";
import { NextRequest } from "next/server";
import path from "path";
import { assertAuthorized } from "@/lib/auth";
import { getDb } from "@/db/client";
import * as schema from "@/db/schema";

export const runtime = "nodejs";

export async function GET(req: NextRequest) {
  const denied = await assertAuthorized(req);
  if (denied) return denied;

  const db = getDb();
  const rows = await db
    .select({
      id: schema.transcripts.id,
      audioRelpath: schema.transcripts.audioRelpath,
      createdAt: schema.transcripts.createdAt,
      status: schema.transcripts.status,
    })
    .from(schema.transcripts)
    .where(ne(schema.transcripts.audioRelpath, ""))
    .orderBy(desc(schema.transcripts.createdAt))
    .limit(200);

  const items = rows.map((r) => ({
    id: r.id,
    filename: path.basename(r.audioRelpath) || r.audioRelpath,
    createdAt: r.createdAt.toISOString(),
    status: r.status,
  }));

  return Response.json({ items });
}
