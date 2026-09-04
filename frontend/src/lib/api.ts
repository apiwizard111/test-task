import type { IngestResult, ReadyState, SourcesState } from "../types/workspace";

type ErrorBody = {
  detail?: string | Array<{ msg?: string }>;
};

export async function getReady(): Promise<ReadyState> {
  return readJson("/api/ready");
}

export async function getSources(): Promise<SourcesState> {
  return readJson("/api/sources");
}

export async function getFileContent(path: string): Promise<string> {
  const data = await readJson<{ path: string; content: string }>(
    `/api/sources/content?path=${encodeURIComponent(path)}`,
  );
  return data.content;
}

export async function ingestSample(): Promise<IngestResult> {
  return readJson("/api/ingest/sample", { method: "POST" });
}

export async function ingestGithub(url: string): Promise<IngestResult> {
  return readJson("/api/ingest/github", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

export async function ingestZip(file: File): Promise<IngestResult> {
  const body = new FormData();
  body.append("file", file);
  return readJson("/api/ingest/zip", { method: "POST", body });
}

async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const data: unknown = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(friendlyApiError(data, response.status));
  }
  return data as T;
}

export function friendlyApiError(data: unknown, status: number): string {
  if (status === 503) {
    return "Add an OPENAI_API_KEY to .env, then restart the API.";
  }
  if (status === 409) {
    return "Ingest a repository before asking questions.";
  }
  if (isErrorBody(data)) {
    if (typeof data.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
    if (Array.isArray(data.detail) && data.detail[0]?.msg) {
      return data.detail[0].msg;
    }
  }
  return "The request failed. Try again.";
}

function isErrorBody(value: unknown): value is ErrorBody {
  return typeof value === "object" && value !== null;
}
