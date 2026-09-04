import { friendlyApiError } from "./api";
import type { ChatTurn, Citation, RetrievedChunk } from "../types/workspace";

type StreamHandlers = {
  paths?: string[];
  signal?: AbortSignal;
  onToken: (text: string) => void;
  onCitations: (citations: Citation[]) => void;
  onRefusal: (text: string) => void;
  onRetrieved: (chunks: RetrievedChunk[]) => void;
  onError: (text: string) => void;
};

export async function streamChat(
  message: string,
  history: ChatTurn[],
  handlers: StreamHandlers,
): Promise<void> {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, paths: handlers.paths ?? [] }),
    signal: handlers.signal,
  });
  if (!response.ok || !response.body) {
    const data: unknown = await response.json().catch(() => ({}));
    throw new Error(friendlyApiError(data, response.status));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (handlers.signal?.aborted) {
        await reader.cancel();
        break;
      }
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        applySseBlock(part, handlers);
      }
    }
    if (buffer.trim() && !handlers.signal?.aborted) {
      applySseBlock(buffer, handlers);
    }
  } catch (error) {
    if (handlers.signal?.aborted || (error instanceof DOMException && error.name === "AbortError")) {
      return;
    }
    throw error;
  }
}

function applySseBlock(block: string, handlers: StreamHandlers): void {
  let eventName = "message";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) {
    return;
  }
  const parsed: unknown = JSON.parse(dataLines.join("\n"));
  if (eventName === "token" && isRecord(parsed) && typeof parsed.text === "string") {
    handlers.onToken(parsed.text);
    return;
  }
  if (eventName === "refusal" && isRecord(parsed) && typeof parsed.text === "string") {
    handlers.onRefusal(parsed.text);
    return;
  }
  if (eventName === "meta" && isRecord(parsed) && Array.isArray(parsed.retrieved)) {
    handlers.onRetrieved(asRetrievedChunks(parsed.retrieved));
    return;
  }
  if (eventName === "error" && isRecord(parsed) && typeof parsed.text === "string") {
    handlers.onError(parsed.text);
    return;
  }
  if (eventName === "done" && isRecord(parsed) && Array.isArray(parsed.citations)) {
    handlers.onCitations(asCitations(parsed.citations));
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function asCitations(value: unknown[]): Citation[] {
  return value.filter(isCitation);
}

function asRetrievedChunks(value: unknown[]): RetrievedChunk[] {
  return value.filter(isRetrievedChunk);
}

function isCitation(value: unknown): value is Citation {
  return (
    isRecord(value) &&
    typeof value.path === "string" &&
    typeof value.symbol === "string" &&
    typeof value.start_line === "number" &&
    typeof value.end_line === "number"
  );
}

function isRetrievedChunk(value: unknown): value is RetrievedChunk {
  return (
    isRecord(value) &&
    typeof value.path === "string" &&
    typeof value.symbol === "string" &&
    typeof value.start_line === "number" &&
    typeof value.end_line === "number" &&
    typeof value.score === "number"
  );
}
