import { useState, type DragEvent, type FormEvent } from "react";

type OnboardingProps = {
  busy: boolean;
  error: string | null;
  llmConfigured: boolean;
  onSample: () => Promise<void>;
  onGithub: (url: string) => Promise<void>;
  onZip: (file: File) => Promise<void>;
  onCancel?: () => void;
};

export function Onboarding({ busy, error, llmConfigured, onSample, onGithub, onZip, onCancel }: OnboardingProps) {
  const [url, setUrl] = useState("");
  const [dragging, setDragging] = useState(false);

  async function handleGithub(event: FormEvent): Promise<void> {
    event.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      return;
    }
    await onGithub(trimmed);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>): void {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) {
      void onZip(file);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-6 py-16">
      <div className="space-y-3">
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-lime">Code documentation assistant</p>
        <h1 className="text-4xl font-medium tracking-tight text-mist">Ask a repository. Get cited answers.</h1>
        <p className="max-w-xl text-sm leading-6 text-mute">
          RepoLens chunks source by symbol, retrieves with hybrid search, and answers only from
          what it found — with file:line citations you can open.
        </p>
      </div>

      {!llmConfigured ? (
        <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          Copy <code className="font-mono">.env.example</code> to <code className="font-mono">.env</code> and set
          an OpenAI-compatible API key before ingesting.
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <button
          type="button"
          disabled={busy || !llmConfigured}
          onClick={() => void onSample()}
          className="rounded-2xl border border-lime/30 bg-lime/10 p-5 text-left shadow-glow disabled:opacity-40"
        >
          <p className="font-mono text-xs text-lime">01</p>
          <h2 className="mt-2 text-lg">Load sample repo</h2>
          <p className="mt-2 text-sm leading-6 text-mute">
            Nexus Tasks — a tiny FastAPI tracker with API-key auth, roles, and assignment rules.
          </p>
        </button>

        <form
          onSubmit={(event) => void handleGithub(event)}
          className="rounded-2xl border border-line bg-panel p-5"
        >
          <p className="font-mono text-xs text-mute">02</p>
          <h2 className="mt-2 text-lg">Public GitHub URL</h2>
          <input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://github.com/owner/repo"
            disabled={busy || !llmConfigured}
            className="mt-4 w-full rounded-lg border border-line bg-ink px-3 py-2 font-mono text-sm"
          />
          <button
            type="submit"
            disabled={busy || !llmConfigured || url.trim().length === 0}
            className="mt-3 rounded-lg bg-mist px-3 py-2 text-sm font-medium text-ink disabled:opacity-40"
          >
            Ingest repository
          </button>
        </form>
      </div>

      <label
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`cursor-pointer rounded-2xl border border-dashed p-6 text-center ${
          dragging ? "border-lime bg-lime/10" : "border-line bg-panel"
        }`}
      >
        <input
          type="file"
          accept=".zip"
          className="hidden"
          disabled={busy || !llmConfigured}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              void onZip(file);
            }
          }}
        />
        <p className="font-mono text-xs text-mute">03</p>
        <p className="mt-2">Drop a .zip of a local codebase</p>
        <p className="mt-1 text-sm text-mute">Ignored: node_modules, lockfiles, binaries, files over 200KB.</p>
      </label>

      {busy ? <p className="font-mono text-sm text-lime">Chunking and embedding…</p> : null}
      {error ? <p className="text-sm text-danger">{error}</p> : null}
      {onCancel ? (
        <button type="button" className="text-sm text-mute underline" onClick={onCancel}>
          Back to current corpus
        </button>
      ) : null}
    </div>
  );
}
