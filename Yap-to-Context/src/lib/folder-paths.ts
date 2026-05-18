import { getDb } from "@/db/client";
import * as schema from "@/db/schema";

export type FolderRow = {
  id: string;
  parentId: string | null;
  name: string;
};

export async function loadAllFolders(): Promise<FolderRow[]> {
  const db = getDb();
  return db
    .select({
      id: schema.folders.id,
      parentId: schema.folders.parentId,
      name: schema.folders.name,
    })
    .from(schema.folders);
}

export function buildFolderPathManifest(rows: FolderRow[]): string {
  const byParent = new Map<string | null, FolderRow[]>();
  for (const r of rows) {
    const k = r.parentId;
    const arr = byParent.get(k) ?? [];
    arr.push(r);
    byParent.set(k, arr);
  }
  for (const arr of byParent.values()) {
    arr.sort((a, b) => a.name.localeCompare(b.name));
  }

  const lines: string[] = [];

  function dfs(parentId: string | null, parts: string[]) {
    const kids = byParent.get(parentId) ?? [];
    for (const k of kids) {
      const next = [...parts, k.name];
      lines.push(next.join("/"));
      dfs(k.id, next);
    }
  }

  dfs(null, []);
  return lines.slice(0, 400).join("\n");
}

export type ResolvePathResult =
  | { kind: "resolved"; leafFolderId: string }
  | {
      kind: "proposal";
      parentFolderId: string | null;
      segmentsToCreate: string[];
    };

export function resolveFolderPath(
  rows: FolderRow[],
  segments: string[],
): ResolvePathResult {
  const normalized = segments.map((s) => s.trim()).filter(Boolean);
  if (normalized.length === 0) {
    return { kind: "proposal", parentFolderId: null, segmentsToCreate: [] };
  }

  function childByName(parentId: string | null, seg: string) {
    const lower = seg.toLowerCase();
    return rows.find(
      (r) =>
        r.parentId === parentId && r.name.trim().toLowerCase() === lower,
    );
  }

  let currentParentId: string | null = null;
  for (let i = 0; i < normalized.length; i++) {
    const seg = normalized[i];
    const hit = childByName(currentParentId, seg);
    if (!hit) {
      return {
        kind: "proposal",
        parentFolderId: currentParentId,
        segmentsToCreate: normalized.slice(i),
      };
    }
    currentParentId = hit.id;
  }

  return { kind: "resolved", leafFolderId: currentParentId! };
}
