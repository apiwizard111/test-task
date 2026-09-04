type StatusPillProps = {
  ingested: boolean;
  llmConfigured: boolean;
  name: string;
};

export function StatusPill({ ingested, llmConfigured, name }: StatusPillProps) {
  if (!llmConfigured) {
    return <span className="rounded-full border border-danger/40 bg-danger/10 px-2.5 py-1 text-xs text-danger">API key missing</span>;
  }
  if (!ingested) {
    return <span className="rounded-full border border-line bg-raised px-2.5 py-1 text-xs text-mute">No corpus</span>;
  }
  return (
    <span className="rounded-full border border-lime/30 bg-lime/10 px-2.5 py-1 text-xs text-lime">
      {name || "Ready"}
    </span>
  );
}
