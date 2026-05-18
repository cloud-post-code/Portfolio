import { getDb } from "@/db/client";
import * as schema from "@/db/schema";

export type FolderTreeNode = {
  id: string;
  name: string;
  parentId: string | null;
  docCount: number;
  children: FolderTreeNode[];
};

export async function buildFolderTree(): Promise<FolderTreeNode[]> {
  const db = getDb();

  const folders = await db
    .select({
      id: schema.folders.id,
      parentId: schema.folders.parentId,
      name: schema.folders.name,
    })
    .from(schema.folders);

  const directCounts = new Map<string, number>();
  const junctionRows = await db
    .select({ folderId: schema.documentFolders.folderId })
    .from(schema.documentFolders);
  for (const row of junctionRows) {
    directCounts.set(row.folderId, (directCounts.get(row.folderId) ?? 0) + 1);
  }

  function subtreeDocTotal(folderId: string): number {
    let sum = directCounts.get(folderId) ?? 0;
    const kids = folders.filter((f) => f.parentId === folderId);
    for (const k of kids) {
      sum += subtreeDocTotal(k.id);
    }
    return sum;
  }

  function build(parentId: string | null): FolderTreeNode[] {
    const kids = folders.filter((f) => f.parentId === parentId);
    kids.sort((a, b) => a.name.localeCompare(b.name));
    return kids.map((k) => ({
      id: k.id,
      name: k.name,
      parentId: k.parentId,
      docCount: subtreeDocTotal(k.id),
      children: build(k.id),
    }));
  }

  return build(null);
}
