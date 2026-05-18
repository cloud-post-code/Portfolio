import { eq } from "drizzle-orm";
import { getDb } from "@/db/client";
import * as schema from "@/db/schema";

export const runtime = "nodejs";

export async function GET() {
  const db = getDb();

  const proposals = await db
    .select()
    .from(schema.folderProposals)
    .where(eq(schema.folderProposals.status, "pending"));

  proposals.sort(
    (a, b) =>
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );

  const enriched = await Promise.all(
    proposals.map(async (p) => {
      let segments: string[] = [];
      try {
        segments = JSON.parse(p.segmentsJson) as string[];
      } catch {
        segments = [];
      }

      const parent = p.parentFolderId
        ? (
            await db
              .select({ name: schema.folders.name })
              .from(schema.folders)
              .where(eq(schema.folders.id, p.parentFolderId))
              .limit(1)
          )[0]
        : null;

      const pendingDocs = await db
        .select({ documentId: schema.pendingDocumentPlacements.documentId })
        .from(schema.pendingDocumentPlacements)
        .where(eq(schema.pendingDocumentPlacements.proposalId, p.id));

      return {
        ...p,
        segments,
        parentName: parent?.name ?? null,
        pendingDocumentCount: pendingDocs.length,
      };
    }),
  );

  return Response.json({ proposals: enriched });
}
