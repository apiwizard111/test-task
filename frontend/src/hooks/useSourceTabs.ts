import { useCallback, useState } from "react";

import type { Citation, RetrievedChunk, SourceSelection } from "../types/workspace";

export function useSourceTabs() {
  const [selection, setSelection] = useState<SourceSelection | null>(null);
  const [openSources, setOpenSources] = useState<SourceSelection[]>([]);

  const openSource = useCallback((source: SourceSelection): void => {
    setOpenSources((current) => {
      const existing = current.findIndex((item) => item.path === source.path);
      if (existing === -1) {
        return [...current, source];
      }
      return current.map((item, index) => (index === existing ? source : item));
    });
    setSelection(source);
  }, []);

  const openCitation = useCallback(
    (citation: Citation): void => {
      openSource({
        path: citation.path,
        startLine: citation.start_line,
        endLine: citation.end_line,
      });
    },
    [openSource],
  );

  const openRetrieved = useCallback(
    (chunk: RetrievedChunk): void => {
      openSource({
        path: chunk.path,
        startLine: chunk.start_line,
        endLine: chunk.end_line,
      });
    },
    [openSource],
  );

  const selectSource = useCallback(
    (path: string): void => {
      const source = openSources.find((item) => item.path === path);
      if (source) {
        setSelection(source);
      }
    },
    [openSources],
  );

  const closeSource = useCallback(
    (path: string): void => {
      const closingIndex = openSources.findIndex((item) => item.path === path);
      const remaining = openSources.filter((item) => item.path !== path);
      setOpenSources(remaining);
      if (selection?.path === path) {
        setSelection(remaining[Math.min(closingIndex, remaining.length - 1)] ?? null);
      }
    },
    [openSources, selection?.path],
  );

  const closeAll = useCallback((): void => {
    setOpenSources([]);
    setSelection(null);
  }, []);

  return {
    selection,
    openSources,
    openSource,
    openCitation,
    openRetrieved,
    selectSource,
    closeSource,
    closeAll,
    reset: closeAll,
  };
}
