import { getCurrentWindow } from '@tauri-apps/api/window';
import type { Mode } from '../types';
import LifeDashboard from './LifeDashboard';

interface SidebarProps {
  models: string[];
  selectedModel: string;
  onModelChange: (model: string) => void;
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  onSave: () => void;
  isSaving: boolean;
  alreadySaved: boolean;
  onNewSession: () => void;
  onOpenArchive: () => void;
  onDayClick: (timestamp: string) => void;
  isDark: boolean;
  onToggleDark: () => void;
  calendarRefreshKey: number;
}

export default function Sidebar({
  models,
  selectedModel,
  onModelChange,
  mode,
  onModeChange,
  onSave,
  isSaving,
  alreadySaved,
  onNewSession,
  onOpenArchive,
  onDayClick,
  isDark,
  onToggleDark,
  calendarRefreshKey,
}: SidebarProps) {
  return (
    <aside className="glass-sidebar w-60 shrink-0 flex flex-col h-full">
      {/* Traffic-light drag region */}
      <div
        className="h-10 shrink-0 cursor-default"
        onMouseDown={() => getCurrentWindow().startDragging()}
      />

      {/* App identity */}
      <div className="px-5 pb-4 flex items-end justify-between shrink-0">
        <div>
          <h1 className="text-[15px] font-semibold tracking-tight text-slate-800 dark:text-slate-100 leading-none">
            Telmi
          </h1>
          <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-1 leading-none">
            Your private journal AI
          </p>
        </div>
        <button
          onClick={onToggleDark}
          aria-label="Toggle dark mode"
          className="text-sm text-slate-400 dark:text-slate-500
                     hover:text-slate-600 dark:hover:text-slate-300
                     transition-colors duration-150 leading-none mb-0.5"
        >
          {isDark ? '○' : '●'}
        </button>
      </div>

      {/* Scrollable main content */}
      <div className="flex flex-col gap-4 px-3 py-3 flex-1 min-h-0 overflow-y-auto">

        {/* Mode selector */}
        <div>
          <span className="block text-[10px] font-semibold text-slate-400 dark:text-slate-500
                           uppercase tracking-widest px-2 mb-2">
            Mode
          </span>
          <div className="flex flex-col gap-1">
            <ModeButton
              active={mode === 'day'}
              onClick={() => onModeChange('day')}
              icon="📓"
              label="Tell me your day"
            />
            <ModeButton
              active={mode === 'mind'}
              onClick={() => onModeChange('mind')}
              icon="🧠"
              label="Tell me your mind"
            />
          </div>
        </div>

        {/* Divider */}
        <div className="h-px bg-slate-200/60 dark:bg-white/[0.06] mx-2" />

        {/* Model selector */}
        <div>
          <label className="block text-[10px] font-semibold text-slate-400 dark:text-slate-500
                            uppercase tracking-widest px-2 mb-2">
            Model
          </label>
          <div className="relative">
            <select
              value={selectedModel}
              onChange={(e) => onModelChange(e.target.value)}
              disabled={models.length === 0}
              className="w-full appearance-none rounded-xl px-3 py-2 pr-8 text-[13px]
                         bg-white/60 dark:bg-white/[0.06]
                         border border-slate-200/80 dark:border-white/[0.08]
                         text-slate-700 dark:text-slate-200
                         focus:outline-none focus:ring-2 focus:ring-indigo-400/40
                         disabled:opacity-50 cursor-pointer
                         transition-all duration-150"
            >
              {models.length === 0 ? (
                <option value="">Connecting…</option>
              ) : (
                models.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))
              )}
            </select>
            <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2
                             text-slate-400 dark:text-slate-500 text-[10px]">
              ▾
            </span>
          </div>
        </div>

        {/* Divider */}
        <div className="h-px bg-slate-200/60 dark:bg-white/[0.06] mx-2" />

        {/* Archive search */}
        <button
          onClick={onOpenArchive}
          className="w-full text-left text-[13px] rounded-xl px-3 py-2.5
                     flex items-center gap-2.5 group
                     text-slate-500 dark:text-slate-400
                     hover:bg-white/50 dark:hover:bg-white/[0.06]
                     border border-transparent
                     hover:border-slate-200/60 dark:hover:border-white/[0.08]
                     transition-all duration-150"
        >
          <svg
            className="w-4 h-4 text-slate-400 dark:text-slate-500 group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}
          >
            <circle cx="11" cy="11" r="7" />
            <path strokeLinecap="round" d="m21 21-4.35-4.35" />
          </svg>
          <span>Search archive</span>
        </button>

        {/* Save / New session — pushed to bottom */}
        <div className="mt-auto">
          {alreadySaved ? (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-1.5 px-2 text-[13px] text-emerald-600 dark:text-emerald-400 font-medium">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <span>Session saved</span>
              </div>
              <button
                onClick={onNewSession}
                className="w-full text-[13px] text-slate-600 dark:text-slate-300
                           bg-slate-100/80 dark:bg-white/[0.07]
                           hover:bg-slate-200/70 dark:hover:bg-white/[0.12]
                           border border-slate-200/60 dark:border-white/[0.08]
                           rounded-xl px-3 py-2.5 transition-all duration-150 text-left"
              >
                New session
              </button>
            </div>
          ) : (
            <button
              onClick={onSave}
              disabled={isSaving}
              className="w-full text-[13px] font-medium
                         bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700
                         dark:bg-indigo-500 dark:hover:bg-indigo-400
                         text-white rounded-xl px-3 py-2.5
                         transition-all duration-150
                         shadow-sm shadow-indigo-500/30
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Saving…
                </span>
              ) : (
                'End & save session'
              )}
            </button>
          )}
        </div>
      </div>

      {/* Life Dashboard — pinned at bottom */}
      <LifeDashboard onDayClick={onDayClick} refreshKey={calendarRefreshKey} />
    </aside>
  );
}

function ModeButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: string;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left text-[13px] rounded-xl px-3 py-2.5
        flex items-center gap-2.5 transition-all duration-150
        ${active
          ? 'bg-indigo-500/10 dark:bg-indigo-400/15 text-indigo-700 dark:text-indigo-300 font-medium border border-indigo-300/40 dark:border-indigo-400/20'
          : 'text-slate-600 dark:text-slate-300 hover:bg-white/50 dark:hover:bg-white/[0.06] border border-transparent hover:border-slate-200/60 dark:hover:border-white/[0.08]'
        }`}
    >
      <span className="text-base leading-none">{icon}</span>
      <span>{label}</span>
    </button>
  );
}
