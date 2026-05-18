import { eq } from "drizzle-orm";
import { getDb } from "@/db/client";
import * as schema from "@/db/schema";

export const runtime = "nodejs";

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id: folderId } = await ctx.params;
  const db = getDb();

  const rows = await db
    .select({
      id: schema.documents.id,
      title: schema.documents.title,
      createdAt: schema.documents.createdAt,
    })
    .from(schema.documents)
    .innerJoin(
      schema.documentFolders,
      eq(schema.documentFolders.documentId, schema.documents.id),
    )
    .where(eq(schema.documentFolders.folderId, folderId));

  rows.sort(
    (a, b) =>
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );

  return Response.json({ documents: rows });
}
