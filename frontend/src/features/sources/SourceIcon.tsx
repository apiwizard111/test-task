import {
  Braces,
  FileCode2,
  FileJson2,
  FileText,
  Folder,
  FolderOpen,
  Settings2,
} from "lucide-react";

type SourceIconProps = {
  name: string;
  language: string | null;
  folder?: "open" | "closed";
};

const ICON_CLASS = "h-4 w-4 shrink-0";

export function SourceIcon({ name, language, folder }: SourceIconProps) {
  if (folder === "open") {
    return <FolderOpen className={`${ICON_CLASS} text-[#dcb67a]`} aria-hidden="true" />;
  }
  if (folder === "closed") {
    return <Folder className={`${ICON_CLASS} text-[#dcb67a]`} aria-hidden="true" />;
  }

  switch (language) {
    case "python":
      return <FileCode2 className={`${ICON_CLASS} text-[#5b9bd5]`} aria-hidden="true" />;
    case "typescript":
      return <Braces className={`${ICON_CLASS} text-[#3b82c4]`} aria-hidden="true" />;
    case "javascript":
      return <Braces className={`${ICON_CLASS} text-[#ceb02a]`} aria-hidden="true" />;
    case "json":
      return <FileJson2 className={`${ICON_CLASS} text-[#ceb02a]`} aria-hidden="true" />;
    case "yaml":
    case "toml":
      return <Settings2 className={`${ICON_CLASS} text-[#b57edc]`} aria-hidden="true" />;
    case "markdown":
      return <FileText className={`${ICON_CLASS} text-[#6a9fb5]`} aria-hidden="true" />;
    case "text":
      return <FileText className={`${ICON_CLASS} text-mute`} aria-hidden="true" />;
    default:
      return fileIconForName(name);
  }
}

function fileIconForName(name: string) {
  const lower = name.toLowerCase();
  if (lower.startsWith("readme") || lower.endsWith(".md")) {
    return <FileText className={`${ICON_CLASS} text-[#6a9fb5]`} aria-hidden="true" />;
  }
  if (lower === "dockerfile" || lower.includes("docker-compose")) {
    return <FileCode2 className={`${ICON_CLASS} text-[#4d8fc5]`} aria-hidden="true" />;
  }
  return <FileCode2 className={`${ICON_CLASS} text-mute`} aria-hidden="true" />;
}
