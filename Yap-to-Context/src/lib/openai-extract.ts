import OpenAI from "openai";
import { z } from "zod";
import { transcriptSummaryJsonSchema } from "@/lib/extraction-json-schema";
import { getOpenAiApiKey } from "@/lib/env";

const summaryPayloadSchema = z.object({
  summary: z.string(),
});

export type TranscriptSummaryPayload = z.infer<typeof summaryPayloadSchema>;

export { transcriptSummaryJsonSchema } from "@/lib/extraction-json-schema";

export async function transcribeAudioFile(input: {
  buffer: Buffer;
  filename: string;
}): Promise<string> {
  const openai = new OpenAI({ apiKey: getOpenAiApiKey() });
  const file = await OpenAI.toFile(input.buffer, input.filename);
  const result = await openai.audio.transcriptions.create({
    file,
    model: "whisper-1",
  });
  return result.text?.trim() ?? "";
}

export async function summarizeTranscript(input: {
  transcript: string;
}): Promise<TranscriptSummaryPayload> {
  const openai = new OpenAI({ apiKey: getOpenAiApiKey() });

  const completion = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    temperature: 0.2,
    messages: [
      {
        role: "system",
        content: `You summarize the user's transcript in clear, readable markdown (headings and bullets when helpful). The user will see the full transcript separately below your summary — do not repeat or paste the transcript here.

Fidelity (non-negotiable): Only summarize what appears in the transcript. Do not invent facts, names, numbers, dates, or details the speaker did not say. If the transcript is vague, the summary stays vague on that point.

Produce a single comprehensive summary of everything in the transcript (not multiple separate documents or topics as distinct artifacts — one flowing summary is fine).`,
      },
      {
        role: "user",
        content: input.transcript,
      },
    ],
    response_format: {
      type: "json_schema",
      json_schema: transcriptSummaryJsonSchema,
    },
  });

  const raw = completion.choices[0]?.message?.content;
  if (!raw) throw new Error("Empty model response");

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error("Model returned invalid JSON");
  }

  return summaryPayloadSchema.parse(parsed);
}
