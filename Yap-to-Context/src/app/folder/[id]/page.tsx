"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { authedFetch } from "@/lib/client-auth";

type DocRow = {
  id: string;
  title: string;
  createdAt: string;
};

export default function FolderPage() {
  const params = useParams();
  const id = params.id as string;
  const [docs, setDocs] = useState<DocRow[] | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const res = await authedFetch(`/api/folders/${id}/documents`);
      if (!res.ok) {
        setError(res.status === 401 ? "Sign in on Home to view this folder." : "Could not load folder.");
        setDocs([]);
        return;
      }
      const data = await res.json();
      setDocs(data.documents as DocRow[]);
    })();
  }, [id]);

  const download = async () => {
    setDownloading(true);
    setError(null);
    try {
      const res = await authedFetch(`/api/folders/${id}/download`);
      if (!res.ok) {
        setError(res.status === 401 ? "Sign in on Home to download." : "Download failed.");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `folder-${id.slice(0, 8)}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg px-4 py-6">
      <Link href="/" className="text-sm text-[var(--muted)]">
        ← Home
      </Link>
      <div className="mt-4 flex min-h-[44px] items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Folder</h1>
        <button
          type="button"
          disabled={downloading}
          className="min-h-[44px] shrink-0 rounded-lg bg-[var(--accent)] px-3 text-sm font-medium text-[var(--bg)] disabled:opacity-40"
          onClick={() => void download()}
        >
          {downloading ? "Preparing…" : "Download ZIP"}
        </button>
      </div>
      <p className="mt-1 font-mono text-xs text-[var(--muted)]">{id}</p>

      {error ? (
        <p className="mt-4 rounded-lg border border-amber-600/50 bg-amber-950/40 px-3 py-2 text-sm">
          {error}
        </p>
      ) : null}

      <ul className="mt-6 space-y-2">
        {docs === null ? (
          <li className="text-[var(--muted)]">Loading…</li>
        ) : docs.length === 0 ? (
          <li className="text-[var(--muted)]">No documents here.</li>
        ) : (
          docs.map((d) => (
            <li key={d.id}>
              <Link
                href={`/document/${d.id}`}
                className="flex min-h-[44px] flex-col justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2"
              >
                <span>{d.title}</span>
                <span className="text-xs text-[var(--muted)]">
                  {new Date(d.createdAt).toLocaleString()}
                </span>
              </Link>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
