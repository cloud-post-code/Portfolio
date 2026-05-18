import fs from "fs";
import { sql } from "drizzle-orm";
import { NextRequest } from "next/server";
import { assertAuthorized } from "@/lib/auth";
import { seedRootFolders } from "@/db/bootstrap";
import { getDb } from "@/db/client";
import * as schema from "@/db/schema";
import { resolveTranscriptAudioAbs } from "@/lib/transcript-audio-path";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const denied = await assertAuthorized(req);
  if (denied) return denied;

  const db = getDb();

  const rows = await db
    .select({ audioRelpath: schema.transcripts.audioRelpath })
    .from(schema.transcripts);

  for (const r of rows) {
    const abs = resolveTranscriptAudioAbs(r.audioRelpath ?? "");
    if (!abs) continue;
    try {
      fs.unlinkSync(abs);
    } catch {
      /* missing file or permission — continue */
    }
  }

  await db.execute(
    sql.raw(
      "TRUNCATE TABLE pending_document_placements, document_folders, documents, ingest_jobs, folder_proposals, transcripts, folders CASCADE",
    ),
  );

  await seedRootFolders();

  return Response.json({ ok: true });
}
