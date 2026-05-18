import { hasAuthSecret } from "@/lib/auth";
import { hasOpenAiApiKey } from "@/lib/env";

export const runtime = "nodejs";

export async function GET() {
  return Response.json({
    secretConfigured: hasAuthSecret(),
    openAiConfigured: hasOpenAiApiKey(),
  });
}
