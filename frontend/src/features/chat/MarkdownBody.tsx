import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { Citation } from "../../types/workspace";

const CITE_RE = /\[([^\]\s]+):(\d+)-(\d+)\]/g;

type MarkdownBodyProps = {
  text: string;
  onCite: (citation: Citation) => void;
};

export function MarkdownBody({ text, onCite }: MarkdownBodyProps) {
  return (
    <div className="text-sm leading-6 text-mist">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components(onCite)}>
        {prepareMarkdown(text)}
      </ReactMarkdown>
    </div>
  );
}

function prepareMarkdown(text: string): string {
  return linkifyCitations(text)
    .replace(/<br\s*\/?>/gi, " · ")
    .replace(/\n{3,}/g, "\n\n");
}

function linkifyCitations(text: string): string {
  return text.replace(CITE_RE, (_match, path: string, start: string, end: string) => {
    const href = `#cite:${encodeURIComponent(path)}:${start}:${end}`;
    return `[${path}:${start}-${end}](${href})`;
  });
}

function components(onCite: (citation: Citation) => void): Components {
  return {
    h1: ({ children }) => <h1 className="mb-2 text-lg font-medium">{children}</h1>,
    h2: ({ children }) => <h2 className="mb-2 mt-4 text-base font-medium">{children}</h2>,
    h3: ({ children }) => <h3 className="mb-2 mt-3 text-sm font-medium">{children}</h3>,
    p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
    ul: ({ children }) => <ul className="mb-3 list-disc space-y-1 pl-5">{children}</ul>,
    ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1 pl-5">{children}</ol>,
    li: ({ children }) => <li className="leading-6">{children}</li>,
    hr: () => <hr className="my-4 border-line" />,
    strong: ({ children }) => <strong className="font-medium text-mist">{children}</strong>,
    em: ({ children }) => <em className="italic text-mute">{children}</em>,
    blockquote: ({ children }) => (
      <blockquote className="mb-3 border-l-2 border-lime/40 pl-3 text-mute">{children}</blockquote>
    ),
    table: ({ children }) => (
      <div className="my-3 overflow-x-auto">
        <table className="w-full min-w-[28rem] border-collapse text-left text-xs">{children}</table>
      </div>
    ),
    thead: ({ children }) => <thead className="bg-raised">{children}</thead>,
    th: ({ children }) => <th className="border border-line px-2.5 py-1.5 font-medium">{children}</th>,
    td: ({ children }) => <td className="border border-line px-2.5 py-1.5 align-top">{children}</td>,
    pre: ({ children }) => (
      <pre className="mb-3 overflow-x-auto rounded-lg bg-ink p-3 font-mono text-[12px] leading-5">{children}</pre>
    ),
    code: ({ className, children }) => {
      if (className) {
        return <code className={className}>{children}</code>;
      }
      return <code className="rounded bg-ink px-1 font-mono text-[12px] text-lime">{children}</code>;
    },
    a: ({ href, children }) => {
      const citation = parseCiteHref(href);
      if (citation) {
        return (
          <button
            type="button"
            className="font-mono text-[12px] text-lime underline decoration-lime/30 underline-offset-2"
            onClick={() => onCite(citation)}
          >
            {children}
          </button>
        );
      }
      return (
        <a href={href} className="text-lime underline underline-offset-2" target="_blank" rel="noreferrer">
          {children}
        </a>
      );
    },
  };
}

function parseCiteHref(href: string | undefined): Citation | null {
  if (!href || !href.startsWith("#cite:")) {
    return null;
  }
  const parts = href.slice(6).split(":");
  if (parts.length < 3) {
    return null;
  }
  const end = Number(parts[parts.length - 1]);
  const start = Number(parts[parts.length - 2]);
  const path = decodeURIComponent(parts.slice(0, -2).join(":"));
  if (!path || Number.isNaN(start) || Number.isNaN(end)) {
    return null;
  }
  return { path, symbol: "", start_line: start, end_line: end };
}
