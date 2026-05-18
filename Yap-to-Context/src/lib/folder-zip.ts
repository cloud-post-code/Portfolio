import archiver from "archiver";
import { eq, inArray } from "drizzle-orm";
import { getDb } from "@/db/client";
import * as schema from "@/db/schema";

function descendantFolderIds(
  rootId: string,
  rows: { id: string; parentId: string | null }[],
): Set<string> {
  const ids = new Set<string>();
  function dfs(id: string) {
    ids.add(id);
    for (const f of rows) {
      if (f.parentId === id) dfs(f.id);
    }
  }
  dfs(rootId);
  return ids;
}

function safeBasename(title: string, id: string) {
  const base = title
    .trim()
    .replace(/[/\\?%*:|"<>]/g, "-")
    .replace(/\s+/g, "-")
    .slice(0, 80);
  const suffix = id.slice(0, 8);
  return `${base || "note"}-${suffix}.md`;
}

export async function zipFolderSubtree(folderId: string): Promise<Buffer> {
  const db = getDb();

  const folderExists = await db
    .select({ id: schema.folders.id })
    .from(schema.folders)
    .where(eq(schema.folders.id, folderId))
    .limit(1);
  if (folderExists.length === 0) {
    throw new Error("NOT_FOUND");
  }

  const folderRows = await db
    .select({ id: schema.folders.id, parentId: schema.folders.parentId })
    .from(schema.folders);

  const scope = descendantFolderIds(folderId, folderRows);

  const allLinks = await db
    .select({
      documentId: schema.documentFolders.documentId,
      folderId: schema.documentFolders.folderId,
    })
    .from(schema.documentFolders);

  const docLinksScoped = allLinks.filter((r) => scope.has(r.folderId));

  const docIds = [...new Set(docLinksScoped.map((r) => r.documentId))];

  const docs =
    docIds.length === 0
      ? []
      : await db
          .select()
          .from(schema.documents)
          .where(inArray(schema.documents.id, docIds));

  const archive = archiver("zip", { zlib: { level: 9 } });
  const chunks: Buffer[] = [];
  archive.on("data", (c: Buffer) => chunks.push(c));

  const done = new Promise<void>((resolve, reject) => {
    archive.on("end", () => resolve());
    archive.on("error", reject);
  });

  const used = new Set<string>();

  for (const doc of docs) {
    let name = safeBasename(doc.title, doc.id);
    let suffix = 1;
    while (used.has(name)) {
      name = safeBasename(`${doc.title}-${suffix}`, doc.id);
      suffix++;
    }
    used.add(name);

    const md = `# ${doc.title}\n\n${doc.body}\n`;
    archive.append(md, { name });
  }

  await archive.finalize();
  await done;

  return Buffer.concat(chunks);
}
