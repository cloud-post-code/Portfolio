import { zipFolderSubtree } from "@/lib/folder-zip";

export const runtime = "nodejs";

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;

  try {
    const buf = await zipFolderSubtree(id);
    return new Response(new Uint8Array(buf), {
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="folder-${id.slice(0, 8)}.zip"`,
      },
    });
  } catch (e) {
    if (e instanceof Error && e.message === "NOT_FOUND") {
      return Response.json({ error: "Folder not found" }, { status: 404 });
    }
    throw e;
  }
}
