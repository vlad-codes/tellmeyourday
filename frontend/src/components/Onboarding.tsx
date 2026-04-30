import { useState } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';

export type AppStatus = 'loading' | 'no-ollama' | 'no-model' | 'ready';

interface Props {
  status: AppStatus;
  onRetry: () => void;
}

const MODELS = [
  { ram: '8 GB',  model: 'llama3.2:3b',   size: '2.0 GB' },
  { ram: '16 GB', model: 'llama3.1:8b',   size: '4.7 GB' },
  { ram: '32 GB', model: 'qwen2.5:32b',   size: '20 GB'  },
];

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  }

  return (
    <div className="relative group mt-3">
      <pre className="bg-slate-900/90 dark:bg-black/60 text-slate-100
                      text-[12px] font-mono rounded-xl px-4 py-3
                      border border-white/[0.08] leading-relaxed overflow-x-auto">
        {code}
      </pre>
      <button
        onClick={copy}
        className="absolute top-2 right-2 text-[10px] px-2 py-1 rounded-lg
                   bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white
                   transition-all duration-150 opacity-0 group-hover:opacity-100"
      >
        {copied ? '✓ Copied' : 'Copy'}
      </button>
    </div>
  );
}

export default function Onboarding({ status, onRetry }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col">
      {/* Drag region */}
      <div
        className="h-10 shrink-0 cursor-default"
        onMouseDown={() => getCurrentWindow().startDragging()}
      />

      {/* Centered card */}
      <div className="flex-1 flex items-center justify-center px-8 pb-10">
        <div className="w-full max-w-sm fade-in">

          {/* Logo */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl
                            bg-indigo-500/15 border border-indigo-400/20 mb-4">
              <span className="text-2xl">📓</span>
            </div>
            <h1 className="text-[22px] font-semibold tracking-tight
                           text-slate-800 dark:text-slate-100">
              Telmi
            </h1>
            <p className="text-[13px] text-slate-400 dark:text-slate-500 mt-1">
              Your private journal AI
            </p>
          </div>

          {/* State-dependent content */}
          {status === 'loading' && <LoadingScreen />}
          {status === 'no-ollama' && <NoOllamaScreen onRetry={onRetry} />}
          {status === 'no-model' && <NoModelScreen onRetry={onRetry} />}
        </div>
      </div>
    </div>
  );
}

function LoadingScreen() {
  return (
    <div className="text-center">
      <div className="inline-flex items-center gap-2.5 text-[13px] text-slate-500 dark:text-slate-400">
        <span className="w-4 h-4 border-2 border-indigo-400/30 border-t-indigo-500
                         rounded-full animate-spin shrink-0" />
        Connecting to backend…
      </div>
      <p className="text-[11px] text-slate-400/60 dark:text-slate-600 mt-3">
        This may take a few seconds on first launch.
      </p>
    </div>
  );
}

function NoOllamaScreen({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-start gap-3 mb-4">
        <span className="text-[18px] leading-none mt-0.5">⚠️</span>
        <div>
          <h2 className="text-[15px] font-semibold text-slate-800 dark:text-slate-100 leading-snug">
            Ollama not found
          </h2>
          <p className="text-[12px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
            Telmi needs Ollama to run AI models locally. Install and start it once.
          </p>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400
                        uppercase tracking-wider mb-1">
            1. Install (Homebrew)
          </p>
          <CodeBlock code="brew install ollama" />
        </div>
        <div>
          <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400
                        uppercase tracking-wider mb-1">
            2. Start
          </p>
          <CodeBlock code="ollama serve" />
        </div>
        <p className="text-[11px] text-slate-400/70 dark:text-slate-600">
          Alternativ:{' '}
          <a
            href="https://ollama.com/download"
            target="_blank"
            rel="noreferrer"
            className="text-indigo-500 dark:text-indigo-400 hover:underline"
          >
            ollama.com/download
          </a>
          {' '}→ Install the desktop app (starts automatically).
        </p>
      </div>

      <button
        onClick={onRetry}
        className="mt-6 w-full text-[13px] font-medium text-white
                   bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700
                   rounded-xl px-4 py-2.5 transition-all duration-150
                   shadow-sm shadow-indigo-500/30"
      >
        Try again
      </button>
    </div>
  );
}

function NoModelScreen({ onRetry }: { onRetry: () => void }) {
  const [selectedModel, setSelectedModel] = useState(MODELS[0].model);

  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-start gap-3 mb-4">
        <span className="text-[18px] leading-none mt-0.5">📦</span>
        <div>
          <h2 className="text-[15px] font-semibold text-slate-800 dark:text-slate-100 leading-snug">
            No model installed
          </h2>
          <p className="text-[12px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
            Choose a model that fits your RAM and download it.
          </p>
        </div>
      </div>

      {/* Model picker */}
      <div className="space-y-1.5 mb-4">
        {MODELS.map((m) => (
          <button
            key={m.model}
            onClick={() => setSelectedModel(m.model)}
            className={`w-full text-left rounded-xl px-3.5 py-2.5 flex items-center justify-between
                        transition-all duration-150 border
                        ${selectedModel === m.model
                          ? 'bg-indigo-500/10 dark:bg-indigo-400/15 border-indigo-300/40 dark:border-indigo-400/20'
                          : 'bg-white/40 dark:bg-white/[0.04] border-slate-200/60 dark:border-white/[0.07] hover:bg-white/60 dark:hover:bg-white/[0.08]'
                        }`}
          >
            <div>
              <span className="text-[13px] font-medium text-slate-700 dark:text-slate-200 font-mono">
                {m.model}
              </span>
              <span className="text-[11px] text-slate-400 dark:text-slate-500 ml-2">
                {m.size}
              </span>
            </div>
            <span className="text-[11px] text-slate-400 dark:text-slate-500">
              {m.ram}
            </span>
          </button>
        ))}
      </div>

      <CodeBlock code={`ollama pull ${selectedModel}`} />

      {/* Embedding model hint */}
      <div className="mt-4 px-3.5 py-2.5 rounded-xl bg-slate-100/60 dark:bg-white/[0.04]
                      border border-slate-200/50 dark:border-white/[0.06]">
        <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
          <span className="font-semibold text-slate-600 dark:text-slate-300">Recommended:</span>
          {' '}For semantic search (from 15 entries on), also pull{' '}
          <span className="font-mono text-[10.5px]">nomic-embed-text</span>:
        </p>
        <CodeBlock code="ollama pull nomic-embed-text" />
      </div>

      <button
        onClick={onRetry}
        className="mt-5 w-full text-[13px] font-medium text-white
                   bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700
                   rounded-xl px-4 py-2.5 transition-all duration-150
                   shadow-sm shadow-indigo-500/30"
      >
        Model ready — continue →
      </button>
    </div>
  );
}
