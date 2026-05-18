import { and, eq, inArray, isNull } from "drizzle-orm";
import { v4 as uuidv4 } from "uuid";
import type { DbClient } from "@/db/client";
import { getDb, requireInboxFolderId } from "@/db/client";
import * as schema from "@/db/schema";

type Tx = Parameters<Parameters<DbClient["transaction"]>[0]>[0];

async function findChildFolder(
  tx: Tx,
  parentId: string | null,
  name: string,
) {
  const trimmed = name.trim();
  const candidates = await tx
    .select()
    .from(schema.folders)
    .where(
      parentId === null
        ? isNull(schema.folders.parentId)
        : eq(schema.folders.parentId, parentId),
    );
  const lower = trimmed.toLowerCase();
  return candidates.find((f) => f.name.trim().toLowerCase() === lower);
}

async function detachFromInbox(tx: Tx, documentId: string, inboxId: string) {
  const rows = await tx
    .select()
    .from(schema.documentFolders)
    .where(eq(schema.documentFolders.documentId, documentId));
  const hasNonInbox = rows.some((r) => r.folderId !== inboxId);
  if (!hasNonInbox) return;

  await tx
    .delete(schema.documentFolders)
    .where(
      and(
        eq(schema.documentFolders.documentId, documentId),
        eq(schema.documentFolders.folderId, inboxId),
      ),
    );
}

export async function approveFolderProposals(proposalIds: string[]) {
  if (proposalIds.length === 0) return { approved: 0 };
  const db = getDb();
  const inboxId = await requireInboxFolderId();

  await db.transaction(async (tx) => {
    for (const proposalId of proposalIds) {
      const [p] = await tx
        .select()
        .from(schema.folderProposals)
        .where(eq(schema.folderProposals.id, proposalId))
        .limit(1);
      if (!p || p.status !== "pending") continue;

      let segments: string[];
      try {
        segments = JSON.parse(p.segmentsJson) as string[];
      } catch {
        continue;
      }
      if (!Array.isArray(segments) || segments.length === 0) continue;

      let parentId: string | null = p.parentFolderId;

      for (const seg of segments) {
        const trimmed = String(seg).trim();
        if (!trimmed) continue;

        const found = await findChildFolder(tx, parentId, trimmed);
        if (found) {
          parentId = found.id;
          continue;
        }

        const nid = uuidv4();
        await tx.insert(schema.folders).values({
          id: nid,
          parentId,
          name: trimmed,
          createdAt: new Date(),
        });
        parentId = nid;
      }

      const leafId = parentId;
      if (!leafId) continue;

      const pendings = await tx
        .select()
        .from(schema.pendingDocumentPlacements)
        .where(eq(schema.pendingDocumentPlacements.proposalId, proposalId));

      for (const row of pendings) {
        await tx
          .insert(schema.documentFolders)
          .values({ documentId: row.documentId, folderId: leafId })
          .onConflictDoNothing();
        await detachFromInbox(tx, row.documentId, inboxId);
        await tx
          .delete(schema.pendingDocumentPlacements)
          .where(eq(schema.pendingDocumentPlacements.id, row.id));
      }

      await tx
        .update(schema.folderProposals)
        .set({ status: "approved" })
        .where(eq(schema.folderProposals.id, proposalId));
    }
  });

  return { approved: proposalIds.length };
}

export async function rejectFolderProposals(proposalIds: string[]) {
  if (proposalIds.length === 0) return { rejected: 0 };
  const db = getDb();

  await db.transaction(async (tx) => {
    await tx
      .delete(schema.pendingDocumentPlacements)
      .where(inArray(schema.pendingDocumentPlacements.proposalId, proposalIds));

    await tx
      .update(schema.folderProposals)
      .set({ status: "rejected" })
      .where(inArray(schema.folderProposals.id, proposalIds));
  });

  return { rejected: proposalIds.length };
}
