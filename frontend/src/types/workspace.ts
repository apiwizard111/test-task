export type TreeNode = {
  name: string;
  path: string;
  kind: "file" | "dir";
  language: string | null;
  children: TreeNode[];
};

export type ReadyState = {
  ingested: boolean;
  llm_configured: boolean;
  name: string;
  provider?: string;
  llm_model?: string;
  embedding_model?: string;
};

export type SourcesState = {
  ingested: boolean;
  name: string;
  source?: string;
  file_count: number;
  chunk_count: number;
  tree: TreeNode[];
};

export type IngestResult = {
  name: string;
  source: string;
  file_count: number;
  chunk_count: number;
  skipped_count: number;
};

export type Citation = {
  path: string;
  symbol: string;
  start_line: number;
  end_line: number;
};

export type RetrievedChunk = {
  path: string;
  symbol: string;
  start_line: number;
  end_line: number;
  score: number;
};

export type ChatTurn = {
  role: "user" | "assistant";
  content: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  retrieved: RetrievedChunk[];
  refused: boolean;
};

export type SourceSelection = {
  path: string;
  startLine?: number;
  endLine?: number;
};
