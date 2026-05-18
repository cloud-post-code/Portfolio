"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FolderTreeNode } from "@/lib/tree-build";
import {
  authedFetch,
  clearStoredSecret,
  getStoredSecret,
  setStoredSecret,
} from "@/lib/client-auth";

/** Narrow Web Speech API types (not always in TS `lib.dom`). */
type WebSpeechAlt = { transcript: string };
type WebSpeechResult = { 0: WebSpeechAlt; isFinal: boolean };
type WebSpeechRecognitionEvent = {
  resultIndex: number;
  results: { length: number; [i: number]: WebSpeechResult };
};
type WebSpeechRecognitionErrorEvent = { error: string };
type WebSpeechRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((ev: WebSpeechRecognitionEvent) => void) | null;
  onerror: ((ev: WebSpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
};

function getSpeechRecognitionCtor():
  | (new () => WebSpeechRecognition)
  | undefined {
  if (typeof window === "undefined") return undefined;
  const w = window as typeof window & {
    SpeechRecognition?: new () => WebSpeechRecognition;
    webkitSpeechRecognition?: new () => WebSpeechRecognition;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition;
}

type AuthStatus = {
  secretConfigured: boolean;
  openAiConfigured: boolean;
};

type StoredAudioRow = {
  id: string;
  filename: string;
  createdAt: string;
  status: string;
};

function TreeList({
  nodes,
  depth,
  folderActionsDisabled,
  busy,
  onAddChild,
}: {
  nodes: FolderTreeNode[];
  depth: number;
  folderActionsDisabled: boolean;
  busy: boolean;
  onAddChild: (parentId: string) => void;
}) {
  if (nodes.length === 0) return null;
  return (
    <ul
      className={`space-y-1 ${depth ? "ml-3 border-l border-[var(--border)] pl-3" : ""}`}
    >
      {nodes.map((n) => (
        <li key={n.id}>
          <div className="flex min-h-[44px] items-center gap-1 rounded-lg px-2 py-2 hover:bg-[var(--surface)]">
            <Link
              href={`/folder/${n.id}`}
              className="flex min-w-0 flex-1 items-center justify-between py-1"
            >
              <span className="truncate">{n.name}</span>
              <span className="ml-2 shrink-0 text-sm text-[var(--muted)]">
                {n.docCount}
              </span>
            </Link>
            <button
              type="button"
              title="Add subgroup"
              disabled={folderActionsDisabled || busy}
              className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-[var(--border)] text-lg leading-none text-[var(--accent)] disabled:opacity-40"
              onClick={(e) => {
                e.preventDefault();
                onAddChild(n.id);
              }}
            >
              +
            </button>
          </div>
          <TreeList
            nodes={n.children}
            depth={depth + 1}
            folderActionsDisabled={folderActionsDisabled}
            busy={busy}
            onAddChild={onAddChild}
          />
        </li>
      ))}
    </ul>
  );
}

/** Avoid doubling speech segments when the browser replays the same final result. */
function mergeInterimTail(prev: string, tail: string): string {
  const p = prev.trimEnd();
  const t = tail.trim();
  if (!t) return p;
  if (!p) return t;
  const pn = p.replace(/\s+/g, " ");
  const tn = t.replace(/\s+/g, " ");
  if (pn === tn || pn.endsWith(tn)) return p;
  return `${p} ${t}`;
}

function flattenFoldersForPicker(
  nodes: FolderTreeNode[],
  prefix: string[] = [],
): { id: string; label: string }[] {
  const rows: { id: string; label: string }[] = [];
  for (const n of nodes) {
    const parts = [...prefix, n.name];
    rows.push({ id: n.id, label: parts.join(" / ") });
    rows.push(...flattenFoldersForPicker(n.children, parts));
  }
  return rows;
}

export default function HomeClient() {
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const [signInPassword, setSignInPassword] = useState("");
  const [tree, setTree] = useState<FolderTreeNode[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");
  const [interimText, setInterimText] = useState("");
  const [isDictating, setIsDictating] = useState(false);
  const [speechSupported, setSpeechSupported] = useState<boolean | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [storedAudio, setStoredAudio] = useState<StoredAudioRow[] | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [destinationFolderIds, setDestinationFolderIds] = useState<string[]>(
    [],
  );
  const fileRef = useRef<HTMLInputElement>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  /** When false, the next `MediaRecorder` `onstop` discards audio (user canceled). */
  const recordSaveRef = useRef(true);
  const recognitionRef = useRef<WebSpeechRecognition | null>(null);
  const dictatingRef = useRef(false);
  const interimRef = useRef("");
  /** Indices already committed from `results` (some engines emit duplicate finals). */
  const processedFinalIndicesRef = useRef<Set<number>>(new Set());

  const refreshAuth = useCallback(async () => {
    const res = await fetch("/api/auth/status");
    const data = (await res.json()) as AuthStatus;
    setAuth(data);
  }, []);

  const loadTree = useCallback(async () => {
    const res = await authedFetch("/api/tree");
    if (!res.ok) {
      setTree([]);
      return;
    }
    const data = await res.json();
    setTree(data.tree as FolderTreeNode[]);
  }, []);

  useEffect(() => {
    setSignedIn(!!getStoredSecret());
  }, []);

  useEffect(() => {
    void refreshAuth();
  }, [refreshAuth]);

  const loadStoredAudio = useCallback(async () => {
    if (!getStoredSecret()) {
      setStoredAudio(null);
      return;
    }
    const res = await authedFetch("/api/transcripts");
    if (!res.ok) {
      setStoredAudio([]);
      return;
    }
    const data = (await res.json()) as { items: StoredAudioRow[] };
    setStoredAudio(data.items);
  }, []);

  useEffect(() => {
    if (signedIn) void loadTree();
  }, [loadTree, signedIn]);

  useEffect(() => {
    if (signedIn) void loadStoredAudio();
    else setStoredAudio(null);
  }, [loadStoredAudio, signedIn]);

  useEffect(() => {
    setSpeechSupported(!!getSpeechRecognitionCtor());
  }, []);

  useEffect(() => {
    return () => {
      dictatingRef.current = false;
      try {
        recognitionRef.current?.abort();
      } catch {
        /* ignore */
      }
      recognitionRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (tree === null) return;
    const valid = new Set(flattenFoldersForPicker(tree).map((r) => r.id));
    setDestinationFolderIds((prev) => prev.filter((id) => valid.has(id)));
  }, [tree]);

  const folderPickerRows = useMemo(() => {
    if (!tree || tree.length === 0) return [];
    return flattenFoldersForPicker(tree).sort((a, b) =>
      a.label.localeCompare(b.label),
    );
  }, [tree]);

  const ingestForm = async (form: FormData) => {
    setBusy(true);
    setStatus(null);
    try {
      for (const id of destinationFolderIds) {
        form.append("folderIds", id);
      }
      const res = await authedFetch("/api/ingest", {
        method: "POST",
        body: form,
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error || res.statusText);
      setStatus(
        `Saved summary with full transcript below (${body.documentsCreated ?? 1} document).`,
      );
      await loadTree();
      await loadStoredAudio();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Ingest failed");
    } finally {
      setBusy(false);
    }
  };

  const submitText = async () => {
    const fd = new FormData();
    fd.set("text", noteText);
    await ingestForm(fd);
    setNoteText("");
    setInterimText("");
    interimRef.current = "";
  };

  const onPickFile = async () => {
    const f = fileRef.current?.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.set("audio", f);
    await ingestForm(fd);
    fileRef.current!.value = "";
  };

  const stopRecording = () => {
    const rec = mediaRef.current;
    if (!rec) return;
    recordSaveRef.current = true;
    setIsRecording(false);
    setBusy(true);
    setStatus("Transcribing and summarizing…");
    rec.stop();
    mediaRef.current = null;
  };

  const cancelRecording = () => {
    const rec = mediaRef.current;
    if (!rec) return;
    recordSaveRef.current = false;
    setIsRecording(false);
    setStatus("Recording canceled. Nothing was saved.");
    rec.stop();
    mediaRef.current = null;
  };

  const startRecording = async () => {
    if (mediaRef.current) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      recordSaveRef.current = true;
      rec.ondataavailable = (ev) => {
        if (ev.data.size) chunksRef.current.push(ev.data);
      };
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const shouldSave = recordSaveRef.current;
        recordSaveRef.current = true;
        if (!shouldSave) {
          chunksRef.current = [];
          return;
        }
        const blob = new Blob(chunksRef.current, { type: rec.mimeType });
        const fd = new FormData();
        fd.set(
          "audio",
          blob,
          `recording.${blob.type.includes("webm") ? "webm" : "ogg"}`,
        );
        await ingestForm(fd);
      };
      rec.start();
      mediaRef.current = rec;
      setIsRecording(true);
      setStatus("Recording… stop to save, or cancel to discard.");
    } catch (e) {
      setStatus(
        e instanceof Error ? e.message : "Could not access microphone",
      );
    }
  };

  const signIn = async () => {
    setBusy(true);
    setStatus(null);
    try {
      const candidate = signInPassword.trim();
      const res = await fetch("/api/auth/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ secret: candidate }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error || res.statusText);
      setStoredSecret(candidate);
      setSignedIn(true);
      setSignInPassword("");
      setStatus("Signed in.");
      await loadTree();
      await loadStoredAudio();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  };

  const signOut = () => {
    dictatingRef.current = false;
    setIsDictating(false);
    try {
      recognitionRef.current?.abort();
    } catch {
      /* ignore */
    }
    recognitionRef.current = null;
    interimRef.current = "";
    setInterimText("");
    recordSaveRef.current = false;
    const recOut = mediaRef.current;
    if (recOut) {
      try {
        recOut.stop();
      } catch {
        /* ignore */
      }
      mediaRef.current = null;
    }
    chunksRef.current = [];
    setIsRecording(false);
    clearStoredSecret();
    setSignedIn(false);
    setTree(null);
    setStoredAudio(null);
    setStatus("Signed out.");
  };

  const deleteStoredAudio = async (row: StoredAudioRow) => {
    if (
      !window.confirm(
        `Delete “${row.filename}” from disk? Notes from this ingest stay in the library; only the audio file is removed.`,
      )
    ) {
      return;
    }
    setDeletingId(row.id);
    setStatus(null);
    try {
      const res = await authedFetch(`/api/transcripts/${row.id}/audio`, {
        method: "DELETE",
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error || res.statusText);
      setStatus("Audio file deleted.");
      await loadStoredAudio();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  const serverNotReady = !!auth && (!auth.secretConfigured || !auth.openAiConfigured);
  const treeLoadingBlocksIngest =
    signedIn && !!auth?.openAiConfigured && tree === null;
  const destinationsIncomplete =
    signedIn &&
    !!auth?.openAiConfigured &&
    tree !== null &&
    (tree.length === 0 || destinationFolderIds.length === 0);
  const ingestDisabled =
    serverNotReady ||
    !signedIn ||
    treeLoadingBlocksIngest ||
    destinationsIncomplete;
  const clearDbDisabled =
    !signedIn || busy || auth === null || !auth.secretConfigured;

  const clearDatabase = useCallback(async () => {
    if (clearDbDisabled) return;
    if (
      !window.confirm(
        "Permanently delete all notes, transcripts, ingest history, custom folders, and stored audio files? Blog, Company, Ideas, and Inbox will be recreated empty. This cannot be undone.",
      )
    ) {
      return;
    }
    setBusy(true);
    setStatus(null);
    try {
      const res = await authedFetch("/api/database/clear", { method: "POST" });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error || res.statusText);
      setNoteText("");
      setInterimText("");
      interimRef.current = "";
      await loadTree();
      await loadStoredAudio();
      setStatus(
        "Database cleared. Root folders (Blog, Company, Ideas, Inbox) were recreated.",
      );
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Could not clear database");
    } finally {
      setBusy(false);
    }
  }, [clearDbDisabled, loadStoredAudio, loadTree]);

  const stopDictation = useCallback(() => {
    dictatingRef.current = false;
    setIsDictating(false);
    const rec = recognitionRef.current;
    recognitionRef.current = null;
    if (rec) {
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
    }
    const tail = interimRef.current.trim();
    interimRef.current = "";
    setInterimText("");
    if (tail) {
      setNoteText((prev) => mergeInterimTail(prev, tail));
    }
  }, []);

  const startDictation = useCallback(() => {
    if (ingestDisabled || busy || isDictating) return;
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      setStatus("Speech recognition is not available in this browser.");
      return;
    }
    try {
      recognitionRef.current?.abort();
    } catch {
      /* ignore */
    }
    recognitionRef.current = null;

    const rec = new Ctor();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = navigator.language || "en-US";
    processedFinalIndicesRef.current.clear();

    rec.onresult = (event: WebSpeechRecognitionEvent) => {
      let interim = "";
      for (let i = 0; i < event.results.length; i++) {
        if (!event.results[i].isFinal) {
          interim += event.results[i][0].transcript;
        }
      }
      const trimmed = interim.replace(/^\s+/, "");
      interimRef.current = trimmed;
      setInterimText(trimmed);

      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (!event.results[i].isFinal) continue;
        if (processedFinalIndicesRef.current.has(i)) continue;
        processedFinalIndicesRef.current.add(i);
        const add = event.results[i][0].transcript.trim();
        if (add) {
          setNoteText((prev) =>
            prev.trim() ? `${prev.trimEnd()} ${add}` : add,
          );
        }
      }
    };

    rec.onerror = (ev: WebSpeechRecognitionErrorEvent) => {
      if (ev.error === "aborted") return;
      if (ev.error === "no-speech") return;
      setStatus(`Speech: ${ev.error}`);
    };

    rec.onend = () => {
      if (!dictatingRef.current) return;
      const current = recognitionRef.current;
      if (!current) return;
      processedFinalIndicesRef.current.clear();
      try {
        current.start();
      } catch {
        /* already running or invalid state */
      }
    };

    recognitionRef.current = rec;
    dictatingRef.current = true;
    setIsDictating(true);
    interimRef.current = "";
    setInterimText("");
    try {
      rec.start();
    } catch (e) {
      dictatingRef.current = false;
      setIsDictating(false);
      recognitionRef.current = null;
      setStatus(
        e instanceof Error ? e.message : "Could not start speech recognition",
      );
    }
  }, [busy, ingestDisabled, isDictating]);

  const createFolder = useCallback(
    async (parentId: string | null) => {
      if (ingestDisabled) {
        setStatus("Sign in with the app password to add folders.");
        return;
      }
      const label =
        parentId === null ? "Library name (top-level folder)" : "Subgroup name";
      const raw = window.prompt(label);
      if (raw === null) return;
      const name = raw.trim();
      if (!name) return;

      setBusy(true);
      setStatus(null);
      try {
        const res = await authedFetch("/api/folders", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ parentId, name }),
        });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.error || res.statusText);
        await loadTree();
        setStatus(
          parentId === null
            ? `Added library “${name}”.`
            : `Added subgroup “${name}”.`,
        );
      } catch (e) {
        setStatus(e instanceof Error ? e.message : "Could not create folder");
      } finally {
        setBusy(false);
      }
    },
    [ingestDisabled, loadTree],
  );

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6 px-4 py-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Yap to Context</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Set <code className="text-[var(--accent)]">OPENAI_API_KEY</code> and{" "}
          <code className="text-[var(--accent)]">AUTH_SECRET</code> as Railway
          service variables. Sign in below with{" "}
          <code className="text-[var(--accent)]">AUTH_SECRET</code> to capture
          notes and manage folders.
        </p>
      </header>

      {auth && !auth.secretConfigured ? (
        <p className="rounded-xl border border-red-600/50 bg-red-950/40 px-4 py-3 text-sm">
          Server not ready: set{" "}
          <code className="text-[var(--accent)]">AUTH_SECRET</code> in Railway
          variables, then redeploy.
        </p>
      ) : null}

      {auth && auth.secretConfigured && !auth.openAiConfigured ? (
        <p className="rounded-xl border border-amber-600/50 bg-amber-950/40 px-4 py-3 text-sm">
          Set <code className="text-[var(--accent)]">OPENAI_API_KEY</code> in
          Railway to enable transcription and extraction.
        </p>
      ) : null}

      {auth && auth.secretConfigured && !signedIn ? (
        <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <h2 className="font-medium">Sign in</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Enter the app password (<code className="text-[var(--accent)]">AUTH_SECRET</code>).
          </p>
          <input
            type="password"
            autoComplete="off"
            className="mt-3 w-full min-h-[44px] rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3"
            placeholder="App password"
            value={signInPassword}
            onChange={(e) => setSignInPassword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && signInPassword.trim() && !busy) {
                void signIn();
              }
            }}
          />
          <button
            type="button"
            disabled={busy || !signInPassword.trim()}
            className="mt-3 w-full min-h-[44px] rounded-lg bg-[var(--accent)] font-medium text-[var(--bg)] disabled:opacity-40"
            onClick={() => void signIn()}
          >
            Sign in
          </button>
        </section>
      ) : null}

      {signedIn ? (
        <button
          type="button"
          className="min-h-[44px] self-start rounded-lg border border-[var(--border)] px-3 text-sm"
          onClick={signOut}
        >
          Sign out
        </button>
      ) : null}

      {signedIn && auth?.openAiConfigured ? (
        <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <h2 className="font-medium">Save notes to</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Pick one or more folders. Notes from each ingest are saved into every
            folder you check (the model only writes titles and bodies—you choose
            where they go).
          </p>
          {tree === null ? (
            <p className="mt-3 text-sm text-[var(--muted)]">Loading folders…</p>
          ) : tree.length === 0 ? (
            <p className="mt-3 text-sm text-amber-300">
              No folders yet. Add libraries in the Library section below first.
            </p>
          ) : (
            <ul className="mt-3 max-h-52 space-y-1 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--bg)] p-2">
              {folderPickerRows.map((row) => (
                <li key={row.id}>
                  <label className="flex min-h-[44px] cursor-pointer items-start gap-3 rounded-md px-2 py-1.5 hover:bg-[var(--surface)]">
                    <input
                      type="checkbox"
                      className="mt-1 size-4 shrink-0 accent-[var(--accent)]"
                      checked={destinationFolderIds.includes(row.id)}
                      onChange={() => {
                        setDestinationFolderIds((prev) =>
                          prev.includes(row.id)
                            ? prev.filter((x) => x !== row.id)
                            : [...prev, row.id],
                        );
                      }}
                    />
                    <span className="text-sm leading-snug">{row.label}</span>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
        <h2 className="font-medium">Add from text</h2>
        {speechSupported === false ? (
          <textarea
            className="mt-2 min-h-[120px] w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3 text-[var(--text)]"
            placeholder="Paste rough notes…"
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
          />
        ) : (
          <>
            <div
              className="mt-2 min-h-[120px] w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3 text-[var(--text)] whitespace-pre-wrap"
              aria-label="Live captions"
              aria-live="polite"
              aria-relevant="additions text"
            >
              {noteText ? <span>{noteText}</span> : null}
              {interimText ? (
                <span className="text-[var(--muted)]">
                  {noteText ? " " : ""}
                  {interimText}
                </span>
              ) : null}
              {isDictating && !noteText && !interimText ? (
                <span className="text-[var(--muted)]"> Listening…</span>
              ) : null}
            </div>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              {!isDictating ? (
                <button
                  type="button"
                  disabled={ingestDisabled || busy}
                  className="min-h-[44px] flex-1 rounded-lg bg-[var(--accent)] font-medium text-[var(--bg)] disabled:opacity-40"
                  onClick={() => void startDictation()}
                >
                  Start listening
                </button>
              ) : (
                <button
                  type="button"
                  disabled={busy}
                  className="min-h-[44px] flex-1 rounded-lg border-2 border-red-500/80 bg-transparent font-medium text-red-400 disabled:opacity-40"
                  onClick={stopDictation}
                >
                  Stop listening
                </button>
              )}
              <button
                type="button"
                disabled={busy || (!noteText.trim() && !interimText.trim())}
                className="min-h-[44px] flex-1 rounded-lg border border-[var(--border)] px-3 font-medium disabled:opacity-40"
                onClick={() => {
                  setNoteText("");
                  setInterimText("");
                  interimRef.current = "";
                }}
              >
                Clear
              </button>
            </div>
          </>
        )}
        <button
          type="button"
          disabled={
            busy ||
            !noteText.trim() ||
            ingestDisabled ||
            (speechSupported !== false && !!interimText.trim())
          }
          className="mt-3 w-full min-h-[44px] rounded-lg border border-[var(--border)] px-3 font-medium disabled:opacity-40"
          onClick={() => void submitText()}
        >
          Ingest text
        </button>
      </section>

      <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
        <h2 className="font-medium">Voice</h2>
        <div className="mt-3 flex flex-col gap-3">
          {isRecording ? (
            <div className="flex flex-col gap-2">
              <button
                type="button"
                disabled={busy}
                className="min-h-[44px] w-full rounded-lg border-2 border-red-500/80 bg-transparent px-3 font-medium text-red-400 disabled:opacity-40"
                onClick={stopRecording}
              >
                Stop recording and save
              </button>
              <button
                type="button"
                disabled={busy}
                className="min-h-[44px] w-full rounded-lg border border-[var(--border)] px-3 font-medium disabled:opacity-40"
                onClick={cancelRecording}
              >
                Cancel recording
              </button>
            </div>
          ) : (
            <button
              type="button"
              disabled={ingestDisabled || busy}
              className="min-h-[44px] w-full rounded-lg bg-[var(--accent)] px-3 font-medium text-[var(--bg)] disabled:opacity-40"
              onClick={() => void startRecording()}
            >
              Start recording
            </button>
          )}
          <input
            ref={fileRef}
            type="file"
            accept="audio/*"
            className="hidden"
            disabled={ingestDisabled || busy}
            onChange={() => void onPickFile()}
          />
          <button
            type="button"
            disabled={ingestDisabled || busy}
            className="text-center text-sm text-[var(--muted)] underline decoration-[var(--border)] underline-offset-2 disabled:opacity-40"
            onClick={() => fileRef.current?.click()}
          >
            Upload an audio file instead
          </button>
        </div>
      </section>

      {signedIn ? (
        <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <div className="flex min-h-[44px] flex-wrap items-center gap-2">
            <h2 className="font-medium">Stored audio</h2>
            <button
              type="button"
              className="ml-auto text-sm text-[var(--accent)]"
              onClick={() => void loadStoredAudio()}
            >
              Refresh
            </button>
          </div>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Voice uploads and recordings are kept on disk until you delete them
            here. Transcripts and notes are unchanged.
          </p>
          <ul className="mt-3 space-y-2">
            {storedAudio === null ? (
              <li className="text-sm text-[var(--muted)]">Loading…</li>
            ) : storedAudio.length === 0 ? (
              <li className="text-sm text-[var(--muted)]">No audio files on disk.</li>
            ) : (
              storedAudio.map((row) => (
                <li
                  key={row.id}
                  className="flex min-h-[44px] flex-wrap items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-mono text-sm">{row.filename}</p>
                    <p className="text-xs text-[var(--muted)]">
                      {new Date(row.createdAt).toLocaleString()} · {row.status}
                    </p>
                  </div>
                  <button
                    type="button"
                    disabled={!!deletingId}
                    className="shrink-0 rounded-lg border border-red-500/60 px-3 py-1.5 text-sm text-red-400 disabled:opacity-40"
                    onClick={() => void deleteStoredAudio(row)}
                  >
                    {deletingId === row.id ? "Deleting…" : "Delete"}
                  </button>
                </li>
              ))
            )}
          </ul>
        </section>
      ) : null}

      {status ? (
        <p className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
          {status}
        </p>
      ) : null}

      <details className="group rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
        <summary className="flex min-h-[44px] cursor-pointer list-none flex-wrap items-center gap-2 [&::-webkit-details-marker]:hidden">
          <span
            className="inline-block shrink-0 text-[var(--muted)] transition-transform duration-200 group-open:rotate-90"
            aria-hidden
          >
            ▶
          </span>
          <h2 className="font-medium">Library</h2>
          <div
            className="ml-auto flex flex-wrap items-center gap-2"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              title="Add top-level library"
              disabled={ingestDisabled || busy}
              className="flex size-9 items-center justify-center rounded-lg border border-[var(--border)] text-lg leading-none text-[var(--accent)] disabled:opacity-40"
              onClick={() => void createFolder(null)}
            >
              +
            </button>
            <button
              type="button"
              className="text-sm text-[var(--accent)]"
              onClick={() => void loadTree()}
            >
              Refresh
            </button>
          </div>
        </summary>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Use + next to a folder to add a subgroup. When you ingest, pick
          destinations in the Save notes to section on this page—create the folders you need
          here first.
        </p>
        <div className="mt-3">
          {!signedIn ? (
            <p className="text-[var(--muted)]">Sign in to view the library.</p>
          ) : tree === null ? (
            <p className="text-[var(--muted)]">Loading…</p>
          ) : (
            <TreeList
              nodes={tree}
              depth={0}
              folderActionsDisabled={ingestDisabled}
              busy={busy}
              onAddChild={(id) => void createFolder(id)}
            />
          )}
        </div>
      </details>

      {signedIn && auth?.secretConfigured ? (
        <section className="rounded-xl border border-red-500/35 bg-[var(--surface)] p-4">
          <h2 className="font-medium text-red-400/95">Danger zone</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Remove all library data and audio from the database and disk.
            Default top-level folders are seeded again afterward.
          </p>
          <button
            type="button"
            disabled={clearDbDisabled}
            className="mt-3 min-h-[44px] w-full rounded-lg border border-red-500/60 px-3 text-sm font-medium text-red-400 disabled:opacity-40"
            onClick={() => void clearDatabase()}
          >
            {busy ? "Working…" : "Clear database"}
          </button>
        </section>
      ) : null}
    </div>
  );
}
