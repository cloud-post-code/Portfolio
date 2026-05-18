import { eq, isNull } from "drizzle-orm";
import { NextRequest } from "next/server";
import { z } from "zod";
import { v4 as uuidv4 } from "uuid";
import { assertAuthorized } from "@/lib/auth";
import { getDb } from "@/db/client";
import * as schema from "@/db/schema";

export const runtime = "nodejs";

const bodySchema = z.object({
  parentId: z.string().uuid().nullable(),
  name: z.string(),
});

export async function POST(req: NextRequest) {
  const denied = await assertAuthorized(req);
  if (denied) return denied;

  const json = await req.json().catch(() => null);
  const parsed = bodySchema.safeParse(json);
  if (!parsed.success) {
    return Response.json({ error: "Invalid body" }, { status: 400 });
  }

  const name = parsed.data.name.trim();
  if (!name) {
    return Response.json({ error: "Name required" }, { status: 400 });
  }
  if (name.length > 200) {
    return Response.json({ error: "Name too long" }, { status: 400 });
  }

  const db = getDb();

  if (parsed.data.parentId !== null) {
    const parent = await db
      .select({ id: schema.folders.id })
      .from(schema.folders)
      .where(eq(schema.folders.id, parsed.data.parentId))
      .limit(1);
    if (parent.length === 0) {
      return Response.json({ error: "Parent folder not found" }, { status: 404 });
    }
  }

  const siblingWhere =
    parsed.data.parentId === null
      ? isNull(schema.folders.parentId)
      : eq(schema.folders.parentId, parsed.data.parentId);

  const siblings = await db
    .select({ name: schema.folders.name })
    .from(schema.folders)
    .where(siblingWhere);

  const lower = name.toLowerCase();
  if (
    siblings.some((s) => s.name.trim().toLowerCase() === lower)
  ) {
    return Response.json(
      { error: "A folder with that name already exists here" },
      { status: 409 },
    );
  }

  const id = uuidv4();
  await db.insert(schema.folders).values({
    id,
    parentId: parsed.data.parentId,
    name,
    createdAt: new Date(),
  });

  return Response.json({ id, parentId: parsed.data.parentId, name });
}
