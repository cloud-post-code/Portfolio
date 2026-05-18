import { v4 as uuidv4 } from "uuid";
import { getDb } from "@/db/client";
import * as schema from "@/db/schema";
import type { TranscriptSummaryPayload } from "@/lib/openai-extract";

export async function saveTranscriptSummaryDocument(input: {
  transcriptId: string;
  transcriptText: string;
  payload: TranscriptSummaryPayload;
  targetFolderIds: string[];
}) {
  const db = getDb();
  const folderIds = [...new Set(input.targetFolderIds)];

  const summary = input.payload.summary.trim();
  const transcript = input.transcriptText.trim();
  const body = [
    summary,
    "",
    "---",
    "",
    "## Full transcript",
    "",
    transcript,
  ].join("\n");

  await db.transaction(async (tx) => {
    const docId = uuidv4();
    await tx.insert(schema.documents).values({
      id: docId,
      title: "Summary",
      body,
      sourceTranscriptId: input.transcriptId,
      createdAt: new Date(),
    });

    for (const fid of folderIds) {
      await tx
        .insert(schema.documentFolders)
        .values({ documentId: docId, folderId: fid })
        .onConflictDoNothing();
    }
  });
}
