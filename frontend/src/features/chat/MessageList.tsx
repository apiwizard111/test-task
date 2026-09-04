import { useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";

import { MarkdownBody } from "./MarkdownBody";
import { SAMPLE_PROMPTS } from "./constants";
import { MENTION_SPLIT_RE } from "../../lib/paths";
import type { ChatMessage, Citation, RetrievedChunk } from "../../types/workspace";

type MessageListProps = {
  messages: ChatMessage[];
  onCite: (citation: Citation) => void;
  onOpenRetrieved: (chunk: RetrievedChunk) => void;
  onPickPrompt: (prompt: string) => void;
};

export function MessageList({ messages, onCite, onOpenRetrieved, onPickPrompt }: MessageListProps) {
  if (messages.length === 0) {
    return <EmptyChat onPick={onPickPrompt} />;
  }
  return (
    <>
      {messages.map((message) => (
        <MessageBlock
          key={message.id}
          message={message}
          onCite={onCite}
          onOpenRetrieved={onOpenRetrieved}
        />
      ))}
    </>
  );
}

function EmptyChat({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-mute">
        The corpus is loaded. Ask a question, type <span className="font-mono text-mist">@path</span>, or drag a
        file from the tree.
      </p>
      <div className="flex flex-wrap gap-2">
        {SAMPLE_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="rounded-full border border-line bg-raised px-3 py-1.5 text-left text-xs text-mist hover:border-lime/40"
            onClick={() => onPick(prompt)}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBlock({
  message,
  onCite,
  onOpenRetrieved,
}: {
  message: ChatMessage;
  onCite: (citation: Citation) => void;
  onOpenRetrieved: (chunk: RetrievedChunk) => void;
}) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) {
      return;
    }
    const timer = window.setTimeout(() => setCopied(false), 1200);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function copyAnswer(): Promise<void> {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
    } catch {
      return;
    }
  }

  const uniqueRetrieved = uniqueByPath(message.retrieved);

  return (
    <article className={`max-w-[46rem] ${isUser ? "ml-auto" : ""}`}>
      <div className="mb-1 flex items-center justify-between gap-2">
        <p className="font-mono text-[10px] uppercase tracking-widest text-mute">
          {isUser ? "You" : "RepoLens"}
        </p>
        {!isUser && message.content ? (
          <button
            type="button"
            className="inline-flex items-center gap-1 text-[11px] text-mute hover:text-mist"
            aria-label="Copy answer"
            onClick={() => void copyAnswer()}
          >
            {copied ? <Check className="h-3 w-3 text-lime" /> : <Copy className="h-3 w-3" />}
            {copied ? "Copied" : "Copy"}
          </button>
        ) : null}
      </div>
      <div
        className={`rounded-2xl px-4 py-3 text-sm leading-6 ${
          isUser
            ? "bg-raised whitespace-pre-wrap"
            : message.refused
              ? "border border-line bg-ink text-mute"
              : "border border-line bg-panel"
        }`}
      >
        {isUser ? <UserMessage text={message.content || "…"} /> : <MarkdownBody text={message.content || "…"} onCite={onCite} />}
      </div>
      {!isUser && uniqueRetrieved.length > 0 ? (
        <div className="mt-2">
          <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-mute">Used files</p>
          <div className="flex flex-wrap gap-1.5">
            {uniqueRetrieved.map((chunk) => (
              <button
                key={`${chunk.path}:${chunk.start_line}`}
                type="button"
                className="rounded-full border border-line bg-raised px-2 py-1 font-mono text-[11px] text-mist hover:border-lime/40 hover:text-lime"
                onClick={() => onOpenRetrieved(chunk)}
                title={`${chunk.path}:${chunk.start_line}-${chunk.end_line}`}
              >
                {chunk.path}
              </button>
            ))}
          </div>
        </div>
      ) : null}
      {message.citations.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {message.citations.map((citation) => (
            <button
              key={`${citation.path}:${citation.start_line}`}
              type="button"
              className="rounded-full border border-lime/30 bg-lime/10 px-2 py-1 font-mono text-[11px] text-lime"
              onClick={() => onCite(citation)}
            >
              {citation.path}:{citation.start_line}-{citation.end_line}
            </button>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function uniqueByPath(chunks: RetrievedChunk[]): RetrievedChunk[] {
  const seen = new Set<string>();
  const out: RetrievedChunk[] = [];
  for (const chunk of chunks) {
    if (seen.has(chunk.path)) {
      continue;
    }
    seen.add(chunk.path);
    out.push(chunk);
  }
  return out;
}

function UserMessage({ text }: { text: string }) {
  const parts = text.split(MENTION_SPLIT_RE);
  return (
    <>
      {parts.map((part, index) =>
        part.startsWith("@") ? (
          <span key={`${part}-${index}`} className="font-mono text-lime">
            {part}
          </span>
        ) : (
          <span key={`${index}-${part.slice(0, 8)}`}>{part}</span>
        ),
      )}
    </>
  );
}
