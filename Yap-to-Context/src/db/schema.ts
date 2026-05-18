import {
  foreignKey,
  pgTable,
  text,
  timestamp,
  primaryKey,
} from "drizzle-orm/pg-core";

export const folders = pgTable(
  "folders",
  {
    id: text("id").primaryKey(),
    parentId: text("parent_id"),
    name: text("name").notNull(),
    createdAt: timestamp("created_at", {
      withTimezone: true,
      mode: "date",
    }).notNull(),
  },
  (table) => ({
    parentFk: foreignKey({
      columns: [table.parentId],
      foreignColumns: [table.id],
    }),
  }),
);

export const transcripts = pgTable("transcripts", {
  id: text("id").primaryKey(),
  audioRelpath: text("audio_relpath").notNull(),
  text: text("text"),
  status: text("status").notNull(),
  createdAt: timestamp("created_at", {
    withTimezone: true,
    mode: "date",
  }).notNull(),
});

export const documents = pgTable("documents", {
  id: text("id").primaryKey(),
  title: text("title").notNull(),
  body: text("body").notNull(),
  sourceTranscriptId: text("source_transcript_id").references(
    () => transcripts.id,
  ),
  createdAt: timestamp("created_at", {
    withTimezone: true,
    mode: "date",
  }).notNull(),
});

export const documentFolders = pgTable(
  "document_folders",
  {
    documentId: text("document_id")
      .notNull()
      .references(() => documents.id, { onDelete: "cascade" }),
    folderId: text("folder_id")
      .notNull()
      .references(() => folders.id, { onDelete: "cascade" }),
  },
  (t) => ({
    pk: primaryKey({ columns: [t.documentId, t.folderId] }),
  }),
);

export const ingestJobs = pgTable("ingest_jobs", {
  id: text("id").primaryKey(),
  transcriptId: text("transcript_id")
    .notNull()
    .references(() => transcripts.id, { onDelete: "cascade" }),
  model: text("model").notNull(),
  rawLlmJson: text("raw_llm_json"),
  status: text("status").notNull(),
  createdAt: timestamp("created_at", {
    withTimezone: true,
    mode: "date",
  }).notNull(),
});

export const folderProposals = pgTable("folder_proposals", {
  id: text("id").primaryKey(),
  transcriptId: text("transcript_id")
    .notNull()
    .references(() => transcripts.id, { onDelete: "cascade" }),
  /** Null means create new top-level folder segments under the library root (parent_id NULL). */
  parentFolderId: text("parent_folder_id").references(() => folders.id),
  segmentsJson: text("segments_json").notNull(),
  status: text("status").notNull(),
  createdAt: timestamp("created_at", {
    withTimezone: true,
    mode: "date",
  }).notNull(),
});

export const pendingDocumentPlacements = pgTable(
  "pending_document_placements",
  {
    id: text("id").primaryKey(),
    documentId: text("document_id")
      .notNull()
      .references(() => documents.id, { onDelete: "cascade" }),
    proposalId: text("proposal_id")
      .notNull()
      .references(() => folderProposals.id, { onDelete: "cascade" }),
    createdAt: timestamp("created_at", {
      withTimezone: true,
      mode: "date",
    }).notNull(),
  },
);
