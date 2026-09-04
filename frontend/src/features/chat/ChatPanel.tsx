import { useEffect, useRef } from "react";

import { MessageList } from "./MessageList";
import { Composer } from "./Composer";
import type { ChatMessage, Citation, RetrievedChunk } from "../../types/workspace";

type ChatPanelProps = {
  messages: ChatMessage[];
  streaming: boolean;
  error: string | null;
  filePaths: string[];
  askPath: string | null;
  askNonce: number;
  onSend: (text: string, paths: string[]) => Promise<void>;
  onStop: () => void;
  onCite: (citation: Citation) => void;
  onOpenRetrieved: (chunk: RetrievedChunk) => void;
};

export function ChatPanel({
  messages,
  streaming,
  error,
  filePaths,
  askPath,
  askNonce,
  onSend,
  onStop,
  onCite,
  onOpenRetrieved,
}: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-auto px-5 py-5">
        <MessageList
          messages={messages}
          onCite={onCite}
          onOpenRetrieved={onOpenRetrieved}
          onPickPrompt={(prompt) => void onSend(prompt, [])}
        />
        <div ref={bottomRef} />
      </div>
      {error ? <p className="px-5 pb-2 text-sm text-danger">{error}</p> : null}
      <Composer
        filePaths={filePaths}
        streaming={streaming}
        askPath={askPath}
        askNonce={askNonce}
        onSend={onSend}
        onStop={onStop}
      />
    </div>
  );
}
