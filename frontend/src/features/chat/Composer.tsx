import { useEffect, useMemo, useRef, useState, type DragEvent, type FormEvent, type KeyboardEvent } from "react";
import { Square, X } from "lucide-react";

import {
  REPOLENS_PATH_MIME,
  activeMentionQuery,
  extractMentions,
  filterPaths,
  uniquePaths,
} from "../../lib/paths";

type ComposerProps = {
  filePaths: string[];
  streaming: boolean;
  askPath: string | null;
  askNonce: number;
  onSend: (text: string, paths: string[]) => Promise<void>;
  onStop: () => void;
};

export function Composer({ filePaths, streaming, askPath, askNonce, onSend, onStop }: ComposerProps) {
  const [draft, setDraft] = useState("");
  const [attachments, setAttachments] = useState<string[]>([]);
  const [dropActive, setDropActive] = useState(false);
  const [mentionIndex, setMentionIndex] = useState(0);
  const [caret, setCaret] = useState(0);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const mention = useMemo(() => activeMentionQuery(draft, caret), [draft, caret]);
  const suggestions = useMemo(() => {
    if (!mention) {
      return [];
    }
    return filterPaths(filePaths, mention.query);
  }, [filePaths, mention]);

  useEffect(() => {
    setMentionIndex(0);
  }, [mention?.query, mention?.start]);

  useEffect(() => {
    if (!askPath || askNonce === 0) {
      return;
    }
    setAttachments((current) => uniquePaths(current, [askPath]));
    setDraft((current) => {
      if (current.trim()) {
        if (current.includes(`@${askPath}`)) {
          return current;
        }
        return `${current.trimEnd()} @${askPath} `;
      }
      return `Explain how @${askPath} works `;
    });
    inputRef.current?.focus();
  }, [askPath, askNonce]);

  function addAttachment(path: string): void {
    setAttachments((current) => uniquePaths(current, [path]));
  }

  function insertMention(path: string): void {
    const localCaret = inputRef.current?.selectionStart ?? caret;
    const active = activeMentionQuery(draft, localCaret);
    if (!active) {
      setDraft((current) => `${current}${current.endsWith(" ") || current.length === 0 ? "" : " "}@${path} `);
      addAttachment(path);
      return;
    }
    const before = draft.slice(0, active.start);
    const after = draft.slice(localCaret);
    const next = `${before}@${path} ${after}`;
    const nextCaret = before.length + path.length + 2;
    setDraft(next);
    setCaret(nextCaret);
    addAttachment(path);
    requestAnimationFrame(() => {
      inputRef.current?.setSelectionRange(nextCaret, nextCaret);
      inputRef.current?.focus();
    });
  }

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    const value = draft.trim();
    if (!value || streaming) {
      return;
    }
    const paths = uniquePaths(attachments, extractMentions(value)).filter((path) => filePaths.includes(path));
    setDraft("");
    setAttachments([]);
    await onSend(value, paths);
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (suggestions.length > 0 && mention) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setMentionIndex((index) => (index + 1) % suggestions.length);
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setMentionIndex((index) => (index - 1 + suggestions.length) % suggestions.length);
        return;
      }
      if (event.key === "Enter" || event.key === "Tab") {
        event.preventDefault();
        insertMention(suggestions[mentionIndex] ?? suggestions[0]);
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        setCaret(draft.length);
        return;
      }
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  function onDrop(event: DragEvent<HTMLFormElement>): void {
    event.preventDefault();
    setDropActive(false);
    const path =
      event.dataTransfer.getData(REPOLENS_PATH_MIME) ||
      event.dataTransfer.getData("text/plain").replace(/^@/, "").trim();
    if (!path || !filePaths.includes(path)) {
      return;
    }
    addAttachment(path);
    if (!draft.includes(`@${path}`)) {
      setDraft((current) => `${current}${current && !current.endsWith(" ") ? " " : ""}@${path} `);
    }
    inputRef.current?.focus();
  }

  return (
    <form
      onSubmit={(event) => void handleSubmit(event)}
      onDragOver={(event) => {
        event.preventDefault();
        setDropActive(true);
      }}
      onDragLeave={() => setDropActive(false)}
      onDrop={onDrop}
      className={`relative border-t border-line p-4 ${dropActive ? "bg-lime/5" : ""}`}
    >
      {attachments.length > 0 ? (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {attachments.map((path) => (
            <span
              key={path}
              className="inline-flex max-w-full items-center gap-1 rounded-full border border-lime/30 bg-lime/10 px-2 py-1 font-mono text-[11px] text-lime"
            >
              <span className="truncate">@{path}</span>
              <button
                type="button"
                className="grid h-4 w-4 place-items-center rounded hover:bg-lime/20"
                aria-label={`Remove ${path}`}
                onClick={() => setAttachments((current) => current.filter((item) => item !== path))}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      ) : null}
      {suggestions.length > 0 ? (
        <div
          className="absolute bottom-[calc(100%-0.5rem)] left-4 right-4 z-20 overflow-hidden rounded-xl border border-line bg-panel shadow-xl"
          role="listbox"
          aria-label="File mentions"
        >
          {suggestions.map((path, index) => (
            <button
              key={path}
              type="button"
              role="option"
              aria-selected={index === mentionIndex}
              className={`flex w-full items-center px-3 py-2 text-left font-mono text-xs ${
                index === mentionIndex ? "bg-lime/15 text-lime" : "text-mist hover:bg-raised"
              }`}
              onMouseDown={(event) => {
                event.preventDefault();
                insertMention(path);
              }}
            >
              @{path}
            </button>
          ))}
        </div>
      ) : null}
      <label className="sr-only" htmlFor="chat-composer">
        Ask a question about the repository
      </label>
      <textarea
        id="chat-composer"
        ref={inputRef}
        rows={3}
        disabled={streaming}
        value={draft}
        aria-label="Ask a question about the repository"
        onChange={(event) => {
          setDraft(event.target.value);
          setCaret(event.target.selectionStart);
        }}
        onClick={(event) => setCaret(event.currentTarget.selectionStart)}
        onKeyUp={(event) => setCaret(event.currentTarget.selectionStart)}
        placeholder="Ask about the code… @path to pin a file, or drag one from the tree"
        className={`w-full resize-none rounded-xl border bg-ink px-3 py-2 text-sm leading-6 ${
          dropActive ? "border-lime" : "border-line"
        }`}
        onKeyDown={onComposerKeyDown}
      />
      <div className="mt-2 flex items-center justify-between gap-3">
        <p className="text-xs text-mute">
          {dropActive ? "Drop to attach file" : "@ file · drag from tree · Enter send · Shift+Enter newline"}
        </p>
        {streaming ? (
          <button
            type="button"
            onClick={onStop}
            className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-raised px-3 py-1.5 text-sm text-mist hover:border-danger/40 hover:text-danger"
          >
            <Square className="h-3 w-3 fill-current" />
            Stop
          </button>
        ) : (
          <button
            type="submit"
            disabled={!draft.trim()}
            className="rounded-lg bg-lime px-3 py-1.5 text-sm font-medium text-ink disabled:opacity-40"
          >
            Ask
          </button>
        )}
      </div>
    </form>
  );
}
