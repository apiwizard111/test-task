import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import type { TreeNode } from "../../types/workspace";
import { REPOLENS_PATH_MIME } from "../../lib/paths";
import { SourceIcon } from "./SourceIcon";

const INDENT = 12;
const GUTTER = 8;

type FileTreeProps = {
  nodes: TreeNode[];
  activePath: string | null;
  foldEpoch: number;
  filterQuery: string;
  onSelect: (path: string) => void;
};

export function FileTree({ nodes, activePath, foldEpoch, filterQuery, onSelect }: FileTreeProps) {
  const visible = useMemo(() => filterTree(nodes, filterQuery), [nodes, filterQuery]);
  const filtering = filterQuery.trim().length > 0;

  if (nodes.length === 0) {
    return <p className="px-3 py-6 text-sm text-mute">No files ingested yet.</p>;
  }
  if (visible.length === 0) {
    return <p className="px-3 py-6 text-sm text-mute">No files match “{filterQuery.trim()}”.</p>;
  }
  return (
    <ul className="select-none py-1" role="tree">
      {sortTreeNodes(visible).map((node) => (
        <TreeItem
          key={node.path}
          node={node}
          activePath={activePath}
          foldEpoch={foldEpoch}
          forceOpen={filtering}
          onSelect={onSelect}
          depth={0}
        />
      ))}
    </ul>
  );
}

function TreeItem({
  node,
  activePath,
  foldEpoch,
  forceOpen,
  onSelect,
  depth,
}: {
  node: TreeNode;
  activePath: string | null;
  foldEpoch: number;
  forceOpen: boolean;
  onSelect: (path: string) => void;
  depth: number;
}) {
  const [open, setOpen] = useState(() => shouldAutoOpen(node, depth));

  useEffect(() => {
    if (foldEpoch === 0) {
      return;
    }
    setOpen(false);
  }, [foldEpoch]);

  useEffect(() => {
    if (forceOpen) {
      setOpen(true);
    }
  }, [forceOpen, node.path]);

  if (node.kind === "dir") {
    const expanded = forceOpen || open;
    return (
      <li role="treeitem" aria-expanded={expanded}>
        <button
          type="button"
          className="group relative flex h-[22px] w-full items-center gap-1 pr-2 text-left text-[13px] text-mist hover:bg-raised"
          style={{ paddingLeft: GUTTER + depth * INDENT }}
          onClick={() => setOpen((value) => !value)}
          title={node.path}
        >
          <IndentGuides depth={depth} />
          <span className="grid h-4 w-4 shrink-0 place-items-center text-mute">
            {expanded ? (
              <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
            )}
          </span>
          <SourceIcon name={node.name} language={null} folder={expanded ? "open" : "closed"} />
          <span className="truncate leading-none">{node.name}</span>
        </button>
        {expanded ? (
          <ul role="group">
            {sortTreeNodes(node.children).map((child) => (
              <TreeItem
                key={child.path}
                node={child}
                activePath={activePath}
                foldEpoch={foldEpoch}
                forceOpen={forceOpen}
                onSelect={onSelect}
                depth={depth + 1}
              />
            ))}
          </ul>
        ) : null}
      </li>
    );
  }

  const active = node.path === activePath;
  return (
    <li role="treeitem">
      <button
        type="button"
        draggable
        className={`relative flex h-[22px] w-full items-center gap-1 pr-2 text-left text-[13px] ${
          active ? "bg-lime/15 text-lime" : "text-mist hover:bg-raised"
        }`}
        style={{ paddingLeft: GUTTER + depth * INDENT }}
        onClick={() => onSelect(node.path)}
        onDragStart={(event) => {
          event.dataTransfer.setData(REPOLENS_PATH_MIME, node.path);
          event.dataTransfer.setData("text/plain", `@${node.path}`);
          event.dataTransfer.effectAllowed = "copy";
        }}
        title={`${node.path} — drag into chat to @mention`}
      >
        <IndentGuides depth={depth} />
        <span className="grid h-4 w-4 shrink-0 place-items-center" aria-hidden="true" />
        <SourceIcon name={node.name} language={node.language} />
        <span className="truncate leading-none">{node.name}</span>
      </button>
    </li>
  );
}

function IndentGuides({ depth }: { depth: number }) {
  if (depth === 0) {
    return null;
  }
  return (
    <>
      {Array.from({ length: depth }, (_, index) => (
        <span
          key={index}
          aria-hidden="true"
          className="pointer-events-none absolute top-0 bottom-0 w-px bg-[#2b3240]"
          style={{ left: GUTTER + index * INDENT + 7 }}
        />
      ))}
    </>
  );
}

function filterTree(nodes: TreeNode[], query: string): TreeNode[] {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return nodes;
  }
  const out: TreeNode[] = [];
  for (const node of nodes) {
    if (node.kind === "file") {
      if (node.path.toLowerCase().includes(needle) || node.name.toLowerCase().includes(needle)) {
        out.push(node);
      }
      continue;
    }
    const children = filterTree(node.children, query);
    if (children.length > 0 || node.name.toLowerCase().includes(needle)) {
      out.push({ ...node, children });
    }
  }
  return out;
}

function sortTreeNodes(nodes: TreeNode[]): TreeNode[] {
  return [...nodes].sort((left, right) => {
    if (left.kind !== right.kind) {
      return left.kind === "dir" ? -1 : 1;
    }
    return left.name.localeCompare(right.name, undefined, { sensitivity: "base" });
  });
}

function shouldAutoOpen(node: TreeNode, depth: number): boolean {
  if (node.kind !== "dir") {
    return false;
  }
  if (depth <= 1) {
    return true;
  }
  const dirs = node.children.filter((child) => child.kind === "dir");
  const files = node.children.filter((child) => child.kind === "file");
  if (files.length > 0) {
    return true;
  }
  return dirs.length === 1;
}
