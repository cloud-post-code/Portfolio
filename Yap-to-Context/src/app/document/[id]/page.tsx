"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { authedFetch } from "@/lib/client-auth";

type Doc = {
  id: string;
  title: string;
  body: string;
  createdAt: string;
};

export default function DocumentPage() {
  const params = useParams();
  const id = params.id as string;
  const [doc, setDoc] = useState<Doc | null | undefined>(undefined);
  const [folders, setFolders] = useState<{ id: string; name: string }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const res = await authedFetch(`/api/documents/${id}`);
      if (!res.ok) {
        setError(
          res.status === 401
            ? "Sign in on Home to view this document."
            : "Could not load document.",
        );
        setDoc(null);
        return;
      }
      const data = await res.json();
      setDoc(data.document as Doc);
      setFolders(data.folders as { id: string; name: string }[]);
    })();
  }, [id]);

  if (doc === undefined) {
    return (
      <div className="px-4 py-6 text-[var(--muted)]">
        <Link href="/">← Home</Link>
        <p className="mt-4">Loading…</p>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="px-4 py-6">
        <Link href="/">← Home</Link>
        <p className="mt-4">{error ?? "Not found."}</p>
      </div>
    );
  }

  return (
    <article className="mx-auto max-w-lg px-4 py-6">
      <Link href="/" className="text-sm text-[var(--muted)]">
        ← Home
      </Link>
      <h1 className="mt-4 text-2xl font-semibold">{doc.title}</h1>
      <p className="mt-1 text-xs text-[var(--muted)]">
        {new Date(doc.createdAt).toLocaleString()}
      </p>
      {folders.length > 0 ? (
        <p className="mt-2 text-sm text-[var(--muted)]">
          In:{" "}
          {folders.map((f, i) => (
            <span key={f.id}>
              {i > 0 ? ", " : ""}
              <Link href={`/folder/${f.id}`} className="text-[var(--accent)]">
                {f.name}
              </Link>
            </span>
          ))}
        </p>
      ) : null}
      <pre className="mt-6 whitespace-pre-wrap rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 font-sans text-sm leading-relaxed">
        {doc.body}
      </pre>
    </article>
  );
}
