import { useEffect, useRef, useState } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import type { KeyboardEvent } from 'react';
import type { ChatMessage, Mode, SaveResponse } from '../types';
import ChatMessageBubble from './ChatMessage';

const API = 'http://localhost:8000';

export const INTRO: Record<Mode, string> = {
  day:
    "Hey, I'm Telmi.\n\nJust tell me what's been on your mind — big or small, good or bad. I'm here to listen.",
  mind:
    "Hey, I'm Telmi.\n\nThis mode is for going a little deeper — a specific situation, a thought you keep returning to, something you haven't quite worked out. Pick one thing and we'll look at it.",
};

interface ChatProps {
  mode: Mode;
  selectedModel: string;
  isSaving: boolean;
  alreadySaved: boolean;
  savedResult: SaveResponse | null;
  saveError: string | null;
  onHistoryChange: (history: ChatMessage[]) => void;
}

export default function Chat({
  mode,
  selectedModel,
  isSaving,
  alreadySaved,
  savedResult,
  saveError,
  onHistoryChange,
}: ChatProps) {
  const initialHistory: ChatMessage[] = [{ role: 'assistant', content: INTRO[mode] }];
  const [history, setHistory] = useState<ChatMessage[]>(initialHistory);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    onHistoryChange(history);
  }, [history]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history]);

  async function sendMessage(text: string) {
    if (!text.trim() || isStreaming || alreadySaved) return;
    setError(null);

    const userMsg: ChatMessage = { role: 'user', content: text.trim() };
    const nextHistory = [...history, userMsg];
    setHistory(nextHistory);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    setHistory((h) => [...h, { role: 'assistant', content: '' }]);
    setIsStreaming(true);

    abortRef.current = new AbortController();

    try {
      const res = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_input: userMsg.content,
          mode,
          history: nextHistory,
          selected_model: selectedModel,
        }),
        signal: abortRef.current.signal,
      });

      if (!res.ok) throw new Error(`Server error ${res.status}`);

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        accumulated += decoder.decode(value, { stream: true });
        setHistory((h) => [
          ...h.slice(0, -1),
          { role: 'assistant', content: accumulated },
        ]);
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes('fetch') || msg.includes('NetworkError') || msg.includes('Failed')) {
        setError('Cannot reach the backend. Is `uvicorn api:app` running on port 8000?');
      } else {
        setError(msg);
      }
      setHistory((h) => h.slice(0, -1));
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  function handleInputChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  }

  const inputDisabled = isStreaming || isSaving || alreadySaved;
  const modeLabel = mode === 'day' ? 'Tell me your day' : 'Tell me your mind';
  const modeIcon = mode === 'day' ? '📓' : '🧠';

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header — also serves as drag region for the chat-side title bar */}
      <div
        className="shrink-0 px-6 flex items-center gap-2.5
                   border-b border-slate-200/50 dark:border-white/[0.07]
                   bg-white/30 dark:bg-white/[0.03] backdrop-blur-sm"
        style={{ paddingTop: '12px', paddingBottom: '12px' }}
        onMouseDown={() => getCurrentWindow().startDragging()}
      >
        <span className="text-base leading-none">{modeIcon}</span>
        <h2 className="text-[13px] font-semibold text-slate-700 dark:text-slate-200 tracking-tight">
          {modeLabel}
        </h2>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="max-w-2xl mx-auto">
          {history.map((msg, i) => {
            const isLast = i === history.length - 1;
            const isStreamingThis = isLast && isStreaming && msg.role === 'assistant';
            return (
              <ChatMessageBubble
                key={i}
                message={msg}
                isStreaming={isStreamingThis}
              />
            );
          })}

          {/* Save result card */}
          {alreadySaved && savedResult && (
            <div className="fade-in mt-3 rounded-2xl
                            bg-white/80 dark:bg-slate-800/60
                            border border-emerald-200/60 dark:border-emerald-500/20
                            shadow-sm backdrop-blur-sm p-4 text-[13px]">
              <p className="flex items-center gap-1.5 font-semibold text-emerald-600 dark:text-emerald-400 mb-2.5">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                Session saved
              </p>
              <p className="font-semibold text-slate-800 dark:text-slate-100">{savedResult.title}</p>
              <p className="text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">{savedResult.summary}</p>
              {savedResult.profile_update && (
                <div className="mt-3 pt-3 border-t border-slate-100 dark:border-white/[0.08]">
                  <p className="text-[11px] font-semibold text-indigo-500 dark:text-indigo-400 mb-1 uppercase tracking-widest">
                    Profile updated
                  </p>
                  <p className="text-slate-500 dark:text-slate-400 leading-relaxed">{savedResult.profile_update}</p>
                </div>
              )}
            </div>
          )}

          {saveError && !alreadySaved && (
            <div className="fade-in mt-3 rounded-2xl
                            bg-red-50/80 dark:bg-red-900/20
                            border border-red-200/60 dark:border-red-700/40
                            text-red-700 dark:text-red-400 text-[13px] p-3.5 leading-relaxed
                            backdrop-blur-sm">
              {saveError}
            </div>
          )}

          {error && (
            <div className="fade-in mt-3 rounded-2xl
                            bg-red-50/80 dark:bg-red-900/20
                            border border-red-200/60 dark:border-red-700/40
                            text-red-700 dark:text-red-400 text-[13px] p-3.5 leading-relaxed
                            backdrop-blur-sm">
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Floating input */}
      <div className="shrink-0 px-4 pb-4 pt-2">
        <div className="max-w-2xl mx-auto">
          <div
            className="input-float flex items-end gap-2 rounded-2xl
                       bg-white/90 dark:bg-slate-800/80
                       border border-slate-200/70 dark:border-white/[0.09]
                       backdrop-blur-md
                       focus-within:ring-2 focus-within:ring-indigo-400/30
                       focus-within:border-indigo-300/60 dark:focus-within:border-indigo-500/40
                       px-4 py-3 transition-all duration-200"
          >
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              disabled={inputDisabled}
              placeholder={
                alreadySaved
                  ? 'Start a new session to continue…'
                  : mode === 'day'
                  ? 'How was your day?'
                  : "What's on your mind?"
              }
              className="flex-1 resize-none bg-transparent text-[14px]
                         text-slate-800 dark:text-slate-100
                         placeholder-slate-400 dark:placeholder-slate-500
                         focus:outline-none leading-relaxed
                         min-h-[22px] max-h-40
                         disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || inputDisabled}
              aria-label="Send"
              className="shrink-0 w-8 h-8 rounded-xl
                         bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700
                         dark:bg-indigo-500 dark:hover:bg-indigo-400
                         text-white flex items-center justify-center
                         transition-all duration-150 mb-0.5
                         shadow-sm shadow-indigo-500/30
                         disabled:opacity-30 disabled:cursor-not-allowed
                         disabled:shadow-none"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18" />
              </svg>
            </button>
          </div>
          <p className="text-[11px] text-slate-400/70 dark:text-slate-500/70 mt-1.5 text-center tracking-tight">
            Return to send · Shift+Return for new line
          </p>
        </div>
      </div>
    </div>
  );
}
