import { useCallback, useRef, useState } from "react";

import { networkErrorMessage } from "../lib/errors";
import { streamChat } from "../lib/sse";
import type { ChatMessage, ChatTurn } from "../types/workspace";

export function useChatStream() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const send = useCallback(async (text: string, paths: string[] = []): Promise<void> => {
    setError(null);
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const history: ChatTurn[] = messagesRef.current.map((item) => ({
      role: item.role,
      content: item.content,
    }));
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      citations: [],
      retrieved: [],
      refused: false,
    };
    const assistantId = crypto.randomUUID();
    const assistant: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      citations: [],
      retrieved: [],
      refused: false,
    };
    setMessages((current) => [...current, userMessage, assistant]);
    setStreaming(true);

    const patchAssistant = (patch: Partial<ChatMessage>): void => {
      setMessages((current) =>
        current.map((item) => (item.id === assistantId ? { ...item, ...patch } : item)),
      );
    };

    try {
      await streamChat(text, history, {
        paths,
        signal: controller.signal,
        onToken: (token) => {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantId ? { ...item, content: item.content + token } : item,
            ),
          );
        },
        onRefusal: (refusal) => patchAssistant({ content: refusal, refused: true }),
        onError: (detail) => patchAssistant({ content: detail, refused: true }),
        onCitations: (citations) => patchAssistant({ citations }),
        onRetrieved: (retrieved) => patchAssistant({ retrieved }),
      });
    } catch (caught) {
      if (controller.signal.aborted) {
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantId && !item.content
              ? { ...item, content: "Stopped.", refused: true }
              : item,
          ),
        );
      } else {
        setError(caught instanceof Error ? networkErrorMessage(caught.message) : "The question failed.");
        setMessages((current) =>
          current.filter((item) => item.id !== assistantId && item.id !== userMessage.id),
        );
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
      }
      setStreaming(false);
    }
  }, []);

  return { messages, streaming, error, send, stop, clearMessages };
}
