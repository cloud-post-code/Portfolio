import fs from "fs/promises";
import { eq } from "drizzle-orm";
import { NextRequest } from "next/server";
import { assertAuthorized } from "@/lib/auth";
import { getDb } from "@/db/client";
import * as schema from "@/db/schema";
import { resolveTranscriptAudioAbs } from "@/lib/transcript-audio-path";

export const runtime = "nodejs";

export async function DELETE(
  req: NextRequest,
  ctx: { params: Promise<{ id: string }> },
) {
  const denied = await assertAuthorized(req);
  if (denied) return denied;

  const { id } = await ctx.params;
  const db = getDb();

  const [row] = await db
    .select()
    .from(schema.transcripts)
    .where(eq(schema.transcripts.id, id))
    .limit(1);

  if (!row) {
    return Response.json({ error: "Transcript not found" }, { status: 404 });
  }

  const relpath = row.audioRelpath?.trim() ?? "";
  if (!relpath) {
    return Response.json({ error: "No audio file on this transcript" }, { status: 404 });
  }

  const abs = resolveTranscriptAudioAbs(relpath);
  if (!abs) {
    return Response.json(
      { error: "Stored path is outside the audio storage directory; not deleted." },
      { status: 400 },
    );
  }

  try {
    await fs.unlink(abs);
  } catch (e) {
    const code = e && typeof e === "object" && "code" in e ? (e as NodeJS.ErrnoException).code : "";
    if (code !== "ENOENT") throw e;
  }

  await db
    .update(schema.transcripts)
    .set({ audioRelpath: "" })
    .where(eq(schema.transcripts.id, id));

  return Response.json({ ok: true });
}
