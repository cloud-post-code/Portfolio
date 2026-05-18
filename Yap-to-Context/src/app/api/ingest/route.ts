import path from "path";
import fs from "fs";
import { eq, inArray } from "drizzle-orm";
import { v4 as uuidv4 } from "uuid";
import { NextRequest } from "next/server";
import { z } from "zod";
import { assertAuthorized } from "@/lib/auth";
import { getAudioStoragePath } from "@/lib/env";
import { getDb } from "@/db/client";
import * as schema from "@/db/schema";
import { summarizeTranscript, transcribeAudioFile } from "@/lib/openai-extract";
import { saveTranscriptSummaryDocument } from "@/lib/process-ingest";

export const runtime = "nodejs";

const uuidSchema = z.string().uuid();

function parseFolderIds(form: FormData): { ok: true; ids: string[] } | { ok: false; error: string } {
  const raw = form.getAll("folderIds");
  const ids: string[] = [];
  for (const v of raw) {
    if (typeof v !== "string") continue;
    const t = v.trim();
    if (!t) continue;
    const parsed = uuidSchema.safeParse(t);
    if (!parsed.success) {
      return { ok: false, error: "Invalid folderIds (expected UUIDs)" };
    }
    ids.push(parsed.data);
  }
  const unique = [...new Set(ids)];
  if (unique.length === 0) {
    return { ok: false, error: "Select at least one destination folder" };
  }
  return { ok: true, ids: unique };
}

export async function POST(req: NextRequest) {
  const denied = await assertAuthorized(req);
  if (denied) return denied;

  const form = await req.formData();
  const folderParse = parseFolderIds(form);
  if (!folderParse.ok) {
    return Response.json({ error: folderParse.error }, { status: 400 });
  }
  const targetFolderIds = folderParse.ids;

  const audio = form.get("audio");
  const textField = form.get("text");

  const db = getDb();

  const existingFolders = await db
    .select({ id: schema.folders.id })
    .from(schema.folders)
    .where(inArray(schema.folders.id, targetFolderIds));
  if (existingFolders.length !== targetFolderIds.length) {
    return Response.json(
      { error: "One or more selected folders do not exist" },
      { status: 400 },
    );
  }
  const transcriptId = uuidv4();

  try {
    let transcriptText = "";

    if (audio instanceof File && audio.size > 0) {
      const buf = Buffer.from(await audio.arrayBuffer());
      const orig = audio.name || "recording.webm";
      const ext = path.extname(orig) || ".webm";
      const base = `${uuidv4()}${ext}`;
      const dir = getAudioStoragePath();
      fs.mkdirSync(dir, { recursive: true });
      const abs = path.join(dir, base);
      fs.writeFileSync(abs, buf);
      const audioRelpath = path.relative(process.cwd(), abs);

      await db.insert(schema.transcripts).values({
        id: transcriptId,
        audioRelpath,
        text: null,
        status: "pending",
        createdAt: new Date(),
      });

      transcriptText = await transcribeAudioFile({ buffer: buf, filename: orig });

      await db
        .update(schema.transcripts)
        .set({ text: transcriptText, status: "transcribed" })
        .where(eq(schema.transcripts.id, transcriptId));
    } else if (typeof textField === "string" && textField.trim().length > 0) {
      transcriptText = textField.trim();

      await db.insert(schema.transcripts).values({
        id: transcriptId,
        audioRelpath: "",
        text: transcriptText,
        status: "transcribed",
        createdAt: new Date(),
      });
    } else {
      return Response.json(
        { error: "Provide multipart field `audio` (file) or `text` (string)." },
        { status: 400 },
      );
    }

    const jobId = uuidv4();
    await db.insert(schema.ingestJobs).values({
      id: jobId,
      transcriptId,
      model: "gpt-4o-mini",
      rawLlmJson: null,
      status: "processing",
      createdAt: new Date(),
    });

    const payload = await summarizeTranscript({
      transcript: transcriptText,
    });

    await db
      .update(schema.ingestJobs)
      .set({
        rawLlmJson: JSON.stringify(payload),
        status: "completed",
      })
      .where(eq(schema.ingestJobs.id, jobId));

    await saveTranscriptSummaryDocument({
      transcriptId,
      transcriptText,
      payload,
      targetFolderIds,
    });

    await db
      .update(schema.transcripts)
      .set({ status: "processed" })
      .where(eq(schema.transcripts.id, transcriptId));

    return Response.json({
      transcriptId,
      transcript: transcriptText,
      documentsCreated: 1,
    });
  } catch (e) {
    try {
      await db
        .update(schema.transcripts)
        .set({ status: "error" })
        .where(eq(schema.transcripts.id, transcriptId));
    } catch {
      /* row may not exist */
    }

    const message = e instanceof Error ? e.message : "Ingest failed";
    return Response.json({ error: message }, { status: 500 });
  }
}
