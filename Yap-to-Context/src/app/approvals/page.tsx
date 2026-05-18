"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { authedFetch } from "@/lib/client-auth";

type Proposal = {
  id: string;
  transcriptId: string;
  parentFolderId: string | null;
  parentName: string | null;
  segments: string[];
  pendingDocumentCount: number;
  createdAt: string;
};

export default function ApprovalsPage() {
  const [rows, setRows] = useState<Proposal[] | null>(null);
  const [authHint, setAuthHint] = useState<string | null>(null);

  const load = useCallback(async () => {
    setAuthHint(null);
    const res = await authedFetch("/api/pending-proposals");
    if (res.status === 401) {
      setAuthHint("Sign in on Home to view legacy approvals.");
      setRows([]);
      return;
    }
    const data = await res.json();
    setRows(data.proposals as Proposal[]);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const approve = async (id: string) => {
    setAuthHint(null);
    const res = await authedFetch("/api/pending-proposals/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: [id] }),
    });
    if (res.status === 401) {
      setAuthHint("Unauthorized — sign in on Home first.");
      return;
    }
    await load();
  };

  const reject = async (id: string) => {
    setAuthHint(null);
    const res = await authedFetch("/api/pending-proposals/reject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: [id] }),
    });
    if (res.status === 401) {
      setAuthHint("Unauthorized — sign in on Home first.");
      return;
    }
    await load();
  };

  return (
    <div className="mx-auto max-w-lg px-4 py-6">
      <Link href="/" className="text-sm text-[var(--muted)]">
        ← Home
      </Link>
      <h1 className="mt-4 text-xl font-semibold">Pending folders</h1>
      <p className="mt-1 text-sm text-[var(--muted)]">
        New ingests no longer queue folders here; approve legacy rows only,
        or reject them.
      </p>

      {authHint ? (
        <p className="mt-3 text-sm text-amber-300">{authHint}</p>
      ) : null}

      <ul className="mt-6 space-y-4">
        {rows === null ? (
          <li className="text-[var(--muted)]">Loading…</li>
        ) : rows.length === 0 ? (
          <li className="text-[var(--muted)]">Nothing pending.</li>
        ) : (
          rows.map((p) => (
            <li
              key={p.id}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"
            >
              <p className="font-medium">
                {p.parentName ? `${p.parentName} / ` : "Library root / "}
                {p.segments.join(" / ")}
              </p>
              <p className="mt-1 text-xs text-[var(--muted)]">
                {p.pendingDocumentCount} doc(s) waiting ·{" "}
                {new Date(p.createdAt).toLocaleString()}
              </p>
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  className="min-h-[44px] flex-1 rounded-lg bg-[var(--accent)] font-medium text-[var(--bg)]"
                  onClick={() => void approve(p.id)}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="min-h-[44px] flex-1 rounded-lg border border-[var(--border)] font-medium"
                  onClick={() => void reject(p.id)}
                >
                  Reject
                </button>
              </div>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
