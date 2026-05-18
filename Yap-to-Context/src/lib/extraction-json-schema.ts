/** OpenAI `response_format.json_schema` for transcript summary (single summary string). */
export const transcriptSummaryJsonSchema = {
  name: "transcript_summary",
  schema: {
    type: "object",
    additionalProperties: false,
    properties: {
      summary: { type: "string" },
    },
    required: ["summary"],
  },
  strict: true,
} as const;
