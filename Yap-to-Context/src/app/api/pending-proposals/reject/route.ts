import { NextRequest } from "next/server";
import { z } from "zod";
import { assertAuthorized } from "@/lib/auth";
import { rejectFolderProposals } from "@/lib/folder-proposals";

export const runtime = "nodejs";

const bodySchema = z.object({
  ids: z.array(z.string().uuid()).min(1),
});

export async function POST(req: NextRequest) {
  const denied = await assertAuthorized(req);
  if (denied) return denied;

  const json = await req.json().catch(() => null);
  const parsed = bodySchema.safeParse(json);
  if (!parsed.success) {
    return Response.json({ error: "Invalid body" }, { status: 400 });
  }

  await rejectFolderProposals(parsed.data.ids);
  return Response.json({ ok: true });
}
