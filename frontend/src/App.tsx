import { useCallback, useEffect, useState } from "react";

import { ResizeHandle } from "./components/ResizeHandle";
import { StatusPill } from "./components/StatusPill";
import { ChatPanel } from "./features/chat/ChatPanel";
import { Onboarding } from "./features/ingest/Onboarding";
import { FileTree } from "./features/sources/FileTree";
import { SourceViewer } from "./features/sources/SourceViewer";
import { useChatStream } from "./hooks/useChatStream";
import { useSourceTabs } from "./hooks/useSourceTabs";
import { getReady, getSources, ingestGithub, ingestSample, ingestZip } from "./lib/api";
import { networkErrorMessage } from "./lib/errors";
import { flattenFilePaths } from "./lib/paths";
import type { ReadyState, SourcesState } from "./types/workspace";

const DEFAULT_CODE_PANE_WIDTH = 440;
const MIN_CODE_PANE_WIDTH = 320;
const MAX_CODE_PANE_WIDTH = 760;

export function App() {
  const [ready, setReady] = useState<ReadyState | null>(null);
  const [sources, setSources] = useState<SourcesState | null>(null);
  const [ingestBusy, setIngestBusy] = useState(false);
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [codePaneWidth, setCodePaneWidth] = useState(DEFAULT_CODE_PANE_WIDTH);
  const [foldEpoch, setFoldEpoch] = useState(0);
  const [treeFilter, setTreeFilter] = useState("");
  const [askPath, setAskPath] = useState<string | null>(null);
  const [askNonce, setAskNonce] = useState(0);
  const [replacing, setReplacing] = useState(false);
  const [bootError, setBootError] = useState<string | null>(null);

  const chat = useChatStream();
  const tabs = useSourceTabs();

  const refresh = useCallback(async () => {
    const [nextReady, nextSources] = await Promise.all([getReady(), getSources()]);
    setReady(nextReady);
    setSources(nextSources);
  }, []);

  useEffect(() => {
    refresh().catch(() => {
      setBootError("Could not reach the API. Start the backend and refresh.");
    });
  }, [refresh]);

  async function runIngest(job: () => Promise<unknown>): Promise<void> {
    setIngestBusy(true);
    setIngestError(null);
    try {
      await job();
      chat.clearMessages();
      tabs.reset();
      setTreeFilter("");
      await refresh();
      setReplacing(false);
    } catch (error) {
      setIngestError(error instanceof Error ? networkErrorMessage(error.message) : "Ingest failed.");
    } finally {
      setIngestBusy(false);
    }
  }

  const llmConfigured = ready?.llm_configured ?? true;
  const ingested = Boolean(sources?.ingested);
  const name = sources?.name ?? "";
  const codePaneOpen = tabs.openSources.length > 0;

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-line px-5 py-3">
        <div className="flex items-center gap-3">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-lime font-mono text-sm text-ink">RL</span>
          <div>
            <p className="text-sm font-medium">RepoLens</p>
            <p className="font-mono text-[11px] text-mute">
              {ready?.provider && ready.provider !== "none" && ready.llm_model
                ? `${ready.provider} · ${ready.llm_model}`
                : "grounded answers from source"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {ingested ? (
            <button
              type="button"
              className="text-xs text-mute underline-offset-2 hover:text-mist hover:underline"
              onClick={() => setReplacing(true)}
            >
              Replace corpus
            </button>
          ) : null}
          <StatusPill ingested={ingested} llmConfigured={llmConfigured} name={name} />
        </div>
      </header>

      {bootError ? (
        <div className="px-6 py-16 text-sm text-danger">{bootError}</div>
      ) : !ingested || replacing ? (
        <Onboarding
          busy={ingestBusy}
          error={ingestError}
          llmConfigured={llmConfigured}
          onSample={() => runIngest(ingestSample)}
          onGithub={(url) => runIngest(() => ingestGithub(url))}
          onZip={(file) => runIngest(() => ingestZip(file))}
          onCancel={replacing ? () => setReplacing(false) : undefined}
        />
      ) : (
        <div className="flex min-h-0 flex-1">
          <aside className="hidden min-h-0 w-64 shrink-0 overflow-auto border-r border-line md:block">
            <div className="sticky top-0 z-10 space-y-2 border-b border-line bg-panel px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <p className="font-mono text-[11px] uppercase tracking-widest text-mute">
                  {sources?.file_count} files · {sources?.chunk_count} chunks
                </p>
                <button
                  type="button"
                  className="shrink-0 text-[11px] text-mute hover:text-mist"
                  title="Collapse all folders"
                  onClick={() => setFoldEpoch((value) => value + 1)}
                >
                  Collapse
                </button>
              </div>
              <input
                type="search"
                value={treeFilter}
                onChange={(event) => setTreeFilter(event.target.value)}
                placeholder="Filter files…"
                className="w-full rounded-md border border-line bg-ink px-2 py-1.5 text-xs text-mist placeholder:text-mute"
              />
            </div>
            <FileTree
              nodes={sources?.tree ?? []}
              activePath={tabs.selection?.path ?? null}
              foldEpoch={foldEpoch}
              filterQuery={treeFilter}
              onSelect={(path) => tabs.openSource({ path })}
            />
          </aside>
          <main className="min-h-0 min-w-[360px] flex-1">
            <ChatPanel
              messages={chat.messages}
              streaming={chat.streaming}
              error={chat.error}
              filePaths={flattenFilePaths(sources?.tree ?? [])}
              askPath={askPath}
              askNonce={askNonce}
              onSend={chat.send}
              onStop={chat.stop}
              onCite={tabs.openCitation}
              onOpenRetrieved={tabs.openRetrieved}
            />
          </main>
          {codePaneOpen ? (
            <>
              <ResizeHandle
                width={codePaneWidth}
                minWidth={MIN_CODE_PANE_WIDTH}
                maxWidth={Math.min(MAX_CODE_PANE_WIDTH, window.innerWidth - 600)}
                onResize={setCodePaneWidth}
              />
              <section
                className="hidden min-h-0 shrink-0 overflow-hidden lg:block"
                style={{ width: codePaneWidth }}
              >
                <SourceViewer
                  selection={tabs.selection}
                  tabs={tabs.openSources}
                  onSelectTab={tabs.selectSource}
                  onCloseTab={tabs.closeSource}
                  onCloseAll={tabs.closeAll}
                  onAskAboutFile={(path) => {
                    setAskPath(path);
                    setAskNonce((value) => value + 1);
                  }}
                />
              </section>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
