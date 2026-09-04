import type { TreeNode } from "../types/workspace";

export const REPOLENS_PATH_MIME = "application/x-repolens-path";

export const MENTION_SPLIT_RE = /(@[A-Za-z0-9_.\-]+(?:\/[A-Za-z0-9_.\-]+)*)/g;
const MENTION_RE = /@([A-Za-z0-9_.\-]+(?:\/[A-Za-z0-9_.\-]+)*)/g;

export function flattenFilePaths(nodes: TreeNode[]): string[] {
  const paths: string[] = [];
  const walk = (items: TreeNode[]): void => {
    for (const node of items) {
      if (node.kind === "file") {
        paths.push(node.path);
      } else {
        walk(node.children);
      }
    }
  };
  walk(nodes);
  return paths.sort((left, right) => left.localeCompare(right, undefined, { sensitivity: "base" }));
}

export function extractMentions(text: string): string[] {
  const found: string[] = [];
  for (const match of text.matchAll(MENTION_RE)) {
    const path = match[1];
    if (path && !found.includes(path)) {
      found.push(path);
    }
  }
  return found;
}

export function activeMentionQuery(text: string, caret: number): { start: number; query: string } | null {
  const before = text.slice(0, caret);
  const match = /(?:^|[\s([{])@([A-Za-z0-9_./\-]*)$/.exec(before);
  if (!match) {
    return null;
  }
  return { start: before.length - match[1].length - 1, query: match[1] };
}

export function filterPaths(paths: string[], query: string, limit = 8): string[] {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return paths.slice(0, limit);
  }
  const scored = paths
    .map((path) => {
      const lower = path.toLowerCase();
      const name = path.split("/").pop()?.toLowerCase() ?? lower;
      let score = -1;
      if (name.startsWith(needle)) {
        score = 300 - name.length;
      } else if (lower.includes(`/${needle}`)) {
        score = 200 - lower.length;
      } else if (lower.includes(needle)) {
        score = 100 - lower.length;
      }
      return { path, score };
    })
    .filter((item) => item.score >= 0)
    .sort((left, right) => right.score - left.score || left.path.localeCompare(right.path));
  return scored.slice(0, limit).map((item) => item.path);
}

export function uniquePaths(...groups: string[][]): string[] {
  const out: string[] = [];
  for (const group of groups) {
    for (const path of group) {
      const cleaned = path.trim().replace(/\\/g, "/").replace(/^@/, "");
      if (cleaned && !out.includes(cleaned)) {
        out.push(cleaned);
      }
    }
  }
  return out;
}

export function languageFromPath(path: string): string {
  const extension = path.split(".").pop()?.toLowerCase() ?? "";
  const byExtension: Record<string, string> = {
    py: "python",
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    json: "json",
    md: "markdown",
    yaml: "yaml",
    yml: "yaml",
    toml: "toml",
    go: "go",
    rs: "rust",
    java: "java",
    sql: "sql",
    rb: "ruby",
    php: "php",
    cs: "csharp",
  };
  return byExtension[extension] ?? "text";
}
