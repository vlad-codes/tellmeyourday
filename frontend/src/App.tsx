import { useEffect, useRef, useState } from 'react';
import type { ChatMessage, Mode, SaveResponse } from './types';
import Sidebar from './components/Sidebar';
import Chat from './components/Chat';
import ArchiveModal from './components/ArchiveModal';
import Onboarding, { type AppStatus } from './components/Onboarding';

const API = 'http://localhost:8000';

interface StatusResponse {
  ollama_running: boolean;
  models: string[];
  embedding_ok: boolean;
}

export default function App() {
  const [appStatus, setAppStatus] = useState<AppStatus>('loading');
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [mode, setMode] = useState<Mode>('day');
  const [isSaving, setIsSaving] = useState(false);
  const [alreadySaved, setAlreadySaved] = useState<Record<Mode, boolean>>({ day: false, mind: false });
  const [savedResult, setSavedResult] = useState<Record<Mode, SaveResponse | null>>({ day: null, mind: null });
  const [saveError, setSaveError] = useState<Record<Mode, string | null>>({ day: null, mind: null });
  const [sessionKey, setSessionKey] = useState<Record<Mode, number>>({ day: 0, mind: 0 });
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [archiveTimestamp, setArchiveTimestamp] = useState<string | undefined>(undefined);
  const [isDark, setIsDark] = useState(() => localStorage.getItem('theme') === 'dark');
  const [calendarRefreshKey, setCalendarRefreshKey] = useState(0);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  const historyRef = useRef<Record<Mode, ChatMessage[]>>({ day: [], mind: [] });

  // Poll /status until backend + Ollama are ready
  useEffect(() => {
    if (appStatus === 'ready') return;
    let cancelled = false;

    async function poll() {
      while (!cancelled) {
        try {
          const r = await fetch(`${API}/status`);
          if (!r.ok) throw new Error('not ok');
          const s: StatusResponse = await r.json();
          if (cancelled) return;
          if (!s.ollama_running) { setAppStatus('no-ollama'); return; }
          if (s.models.length === 0) { setAppStatus('no-model'); return; }
          setModels(s.models); setSelectedModel(s.models[0]); setAppStatus('ready'); return;
        } catch {
          await new Promise((res) => setTimeout(res, 1200));
        }
      }
    }

    poll();
    return () => { cancelled = true; };
  }, [appStatus]);

  function handleHistoryChange(m: Mode, history: ChatMessage[]) {
    historyRef.current[m] = history;
  }

  async function handleSave() {
    if (isSaving || alreadySaved[mode]) return;
    setIsSaving(true);
    try {
      const res = await fetch(`${API}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode,
          history: historyRef.current[mode],
          selected_model: selectedModel,
        }),
      });
      if (!res.ok) {
        setSaveError((prev) => ({ ...prev, [mode]: 'Could not save session. Please try again.' }));
        return;
      }
      const result: SaveResponse = await res.json();
      setSavedResult((prev) => ({ ...prev, [mode]: result }));
      setAlreadySaved((prev) => ({ ...prev, [mode]: true }));
      setSaveError((prev) => ({ ...prev, [mode]: null }));
      setCalendarRefreshKey((k) => k + 1);
    } catch {
      setSaveError((prev) => ({ ...prev, [mode]: 'Could not save session. Please try again.' }));
    } finally {
      setIsSaving(false);
    }
  }

  function handleNewSession() {
    setAlreadySaved((prev) => ({ ...prev, [mode]: false }));
    setSavedResult((prev) => ({ ...prev, [mode]: null }));
    setSaveError((prev) => ({ ...prev, [mode]: null }));
    setSessionKey((prev) => ({ ...prev, [mode]: prev[mode] + 1 }));
    historyRef.current[mode] = [];
  }

  function handleDayClick(timestamp: string) {
    setArchiveTimestamp(timestamp);
    setArchiveOpen(true);
  }

  function handleArchiveClose() {
    setArchiveOpen(false);
    setArchiveTimestamp(undefined);
  }

  if (appStatus !== 'ready') {
    return <Onboarding status={appStatus} onRetry={() => setAppStatus('loading')} />;
  }

  return (
    <div className="flex h-screen overflow-hidden w-full">
      <Sidebar
        models={models}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        mode={mode}
        onModeChange={setMode}
        onOpenArchive={() => setArchiveOpen(true)}
        onDayClick={handleDayClick}
        calendarRefreshKey={calendarRefreshKey}
      />
      {archiveOpen && (
        <ArchiveModal
          onClose={handleArchiveClose}
          initialChatTimestamp={archiveTimestamp}
        />
      )}
      <button
        onClick={() => setIsDark((d) => !d)}
        aria-label="Toggle dark mode"
        className="fixed top-1 right-4 z-20
                   w-8 h-8 flex items-center justify-center rounded-lg
                   text-slate-400 dark:text-slate-500
                   hover:text-slate-600 dark:hover:text-slate-300
                   hover:bg-slate-100/70 dark:hover:bg-white/[0.07]
                   transition-all duration-150"
      >
        {isDark ? (
          <svg className="w-[15px] h-[15px]" fill="none" viewBox="0 0 24 24"
               stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M12 3v2m0 14v2M5.636 5.636l1.414 1.414m9.9 9.9 1.414 1.414M3 12h2m14 0h2M5.636 18.364l1.414-1.414m9.9-9.9 1.414-1.414M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />
          </svg>
        ) : (
          <svg className="w-[15px] h-[15px]" fill="none" viewBox="0 0 24 24"
               stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        )}
      </button>
      <main className="flex-1 overflow-hidden chat-bg">
        <Chat
          key={`${mode}-${sessionKey[mode]}`}
          mode={mode}
          selectedModel={selectedModel}
          isSaving={isSaving}
          alreadySaved={alreadySaved[mode]}
          savedResult={savedResult[mode]}
          saveError={saveError[mode]}
          onHistoryChange={(h) => handleHistoryChange(mode, h)}
          onSave={handleSave}
          onNewSession={handleNewSession}
        />
      </main>
    </div>
  );
}
