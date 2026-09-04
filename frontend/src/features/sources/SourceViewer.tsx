import { useEffect, useRef, useState } from "react";
import { Check, Copy, X } from "lucide-react";
import { Highlight, themes, type Language } from "prism-react-renderer";

import { getFileContent } from "../../lib/api";
import { languageFromPath } from "../../lib/paths";
import type { SourceSelection } from "../../types/workspace";
import { SourceIcon } from "./SourceIcon";

type SourceViewerProps = {
  selection: SourceSelection | null;
  tabs: SourceSelection[];
  onSelectTab: (path: string) => void;
  onCloseTab: (path: string) => void;
  onCloseAll: () => void;
  onAskAboutFile: (path: string) => void;
};

export function SourceViewer({
  selection,
  tabs,
  onSelectTab,
  onCloseTab,
  onCloseAll,
  onAskAboutFile,
}: SourceViewerProps) {
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activePath = selection?.path ?? null;

  useEffect(() => {
    if (!activePath) {
      setContent(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setContent(null);
    setError(null);
    getFileContent(activePath)
      .then((text) => {
        if (!cancelled) {
          setContent(text);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Could not open this file.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activePath]);

  useEffect(() => {
    if (content === null || !selection?.startLine) {
      return;
    }
    document.getElementById(`L${selection.startLine}`)?.scrollIntoView({ block: "center" });
  }, [content, selection?.startLine]);

  return (
    <div className="flex h-full flex-col">
      <SourceTabs
        tabs={tabs}
        activePath={selection?.path ?? null}
        onSelect={onSelectTab}
        onClose={onCloseTab}
        onCloseAll={onCloseAll}
      />
      {error ? (
        <div className="p-4 text-sm text-danger">{error}</div>
      ) : content === null ? (
        <SourceSkeleton />
      ) : selection ? (
        <SourceCode
          key={selection.path}
          selection={selection}
          content={content}
          onAskAboutFile={onAskAboutFile}
        />
      ) : null}
    </div>
  );
}

function SourceTabs({
  tabs,
  activePath,
  onSelect,
  onClose,
  onCloseAll,
}: {
  tabs: SourceSelection[];
  activePath: string | null;
  onSelect: (path: string) => void;
  onClose: (path: string) => void;
  onCloseAll: () => void;
}) {
  return (
    <div className="flex h-9 shrink-0 items-stretch border-b border-line bg-ink">
      <div className="flex min-w-0 flex-1 overflow-x-auto" role="tablist">
        {tabs.map((tab) => {
          const active = tab.path === activePath;
          const name = tab.path.split("/").pop() ?? tab.path;
          const language = languageFromPath(tab.path);
          return (
            <div
              key={tab.path}
              className={`group flex min-w-0 max-w-52 shrink-0 items-center border-r border-line ${
                active ? "border-t-2 border-t-lime bg-panel text-mist" : "border-t-2 border-t-transparent text-mute"
              }`}
            >
              <button
                type="button"
                role="tab"
                aria-selected={active}
                title={tab.path}
                className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 font-mono text-[11px]"
                onClick={() => onSelect(tab.path)}
              >
                <SourceIcon name={name} language={language} />
                <span className="truncate">{name}</span>
              </button>
              <button
                type="button"
                className={`mr-1 grid h-5 w-5 shrink-0 place-items-center rounded hover:bg-raised hover:text-mist group-hover:opacity-100 focus:opacity-100 ${
                  active ? "opacity-100" : "opacity-0"
                }`}
                aria-label={`Close ${name}`}
                onClick={() => onClose(tab.path)}
              >
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </div>
          );
        })}
      </div>
      <button
        type="button"
        className="shrink-0 border-l border-line px-3 text-[11px] text-mute hover:bg-raised hover:text-mist"
        onClick={onCloseAll}
        title="Close all open files"
      >
        Close all
      </button>
    </div>
  );
}

function SourceCode({
  selection,
  content,
  onAskAboutFile,
}: {
  selection: SourceSelection;
  content: string;
  onAskAboutFile: (path: string) => void;
}) {
  const [copied, setCopied] = useState(false);
  const copyResetTimeout = useRef<number | null>(null);
  const start = selection.startLine ?? -1;
  const end = selection.endLine ?? -1;
  const language = languageFromPath(selection.path);

  useEffect(
    () => () => {
      if (copyResetTimeout.current !== null) {
        window.clearTimeout(copyResetTimeout.current);
      }
    },
    [],
  );

  async function copyContent(): Promise<void> {
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      return;
    }

    if (copyResetTimeout.current !== null) {
      window.clearTimeout(copyResetTimeout.current);
    }
    setCopied(true);
    copyResetTimeout.current = window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <>
      <div className="flex h-9 shrink-0 items-center justify-between gap-2 border-b border-line bg-panel px-3">
        <div className="flex min-w-0 items-center gap-2 font-mono text-xs text-mist">
          <SourceIcon name={selection.path} language={language} />
          <span className="truncate">{selection.path}</span>
          <span className="rounded border border-line bg-raised px-1.5 py-0.5 text-[9px] uppercase text-mute">
            {language}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            className="rounded-md px-2 py-1 text-xs text-mute hover:bg-raised hover:text-mist"
            onClick={() => onAskAboutFile(selection.path)}
          >
            Ask about file
          </button>
          <button
            type="button"
            className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-mute hover:bg-raised hover:text-mist"
            onClick={() => void copyContent()}
            aria-label="Copy file contents"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-lime" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto bg-[#011627]">
        <Highlight theme={themes.nightOwl} code={content} language={prismLanguage(language)}>
          {({ className, style, tokens, getLineProps, getTokenProps }) => (
            <pre
              className={`${className} min-w-max py-3 font-mono text-[12px] leading-5`}
              style={{ ...style, margin: 0, minHeight: "100%", background: "#011627", whiteSpace: "pre" }}
            >
              {tokens.map((line, index) => {
                const lineNumber = index + 1;
                const highlighted = start > 0 && lineNumber >= start && lineNumber <= end;
                const lineProps = getLineProps({ line });
                return (
                  <div
                    {...lineProps}
                    key={lineNumber}
                    id={`L${lineNumber}`}
                    className={`flex flex-nowrap whitespace-pre px-3 ${lineProps.className ?? ""} ${
                      highlighted ? "border-l-2 border-lime bg-lime/10 pl-[10px]" : ""
                    }`}
                  >
                    <span className="mr-4 w-8 shrink-0 select-none text-right text-[#637777]">
                      {lineNumber}
                    </span>
                    <span className="whitespace-pre">
                      {line.map((token, tokenIndex) => {
                        const tokenProps = getTokenProps({ token });
                        return (
                          <span
                            {...tokenProps}
                            key={tokenIndex}
                            className={withoutTailwindCollisions(tokenProps.className)}
                          />
                        );
                      })}
                    </span>
                  </div>
                );
              })}
            </pre>
          )}
        </Highlight>
      </div>
    </>
  );
}

function prismLanguage(language: string): Language {
  if (language === "typescript") {
    return "tsx";
  }
  if (language === "text") {
    return "markup";
  }
  return language;
}

/** Prism emits types like `table`; Tailwind's `.table { display:table }` then explodes GFM rows. */
function withoutTailwindCollisions(className: string | undefined): string | undefined {
  if (!className) {
    return className;
  }
  return className
    .split(/\s+/)
    .filter((part) => part.length > 0 && part !== "table")
    .join(" ");
}

function SourceSkeleton() {
  return (
    <div className="space-y-2 p-4">
      <div className="h-3 w-1/2 animate-pulse rounded bg-raised" />
      <div className="h-3 w-full animate-pulse rounded bg-raised" />
      <div className="h-3 w-5/6 animate-pulse rounded bg-raised" />
    </div>
  );
}
