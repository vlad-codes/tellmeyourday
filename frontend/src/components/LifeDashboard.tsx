import { useEffect, useMemo, useState } from 'react';
import type { CalendarDay } from '../types';

const API = 'http://localhost:8000';

const WEEKDAY_LABELS = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];
const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

interface Props {
  onDayClick: (timestamp: string) => void;
  refreshKey: number;
}

function computeStreak(days: CalendarDay[]): number {
  const dates = new Set(days.map((d) => d.date));
  const cursor = new Date();
  let streak = 0;
  while (true) {
    const key = cursor.toISOString().slice(0, 10);
    if (!dates.has(key)) break;
    streak++;
    cursor.setDate(cursor.getDate() - 1);
  }
  return streak;
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfWeek(year: number, month: number): number {
  // Monday = 0 … Sunday = 6
  return (new Date(year, month, 1).getDay() + 6) % 7;
}

function toDateKey(year: number, month: number, day: number): string {
  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

export default function LifeDashboard({ onDayClick, refreshKey }: Props) {
  const today = useMemo(() => new Date(), []);
  const todayKey = useMemo(() => today.toISOString().slice(0, 10), [today]);

  const [calDays, setCalDays] = useState<CalendarDay[]>([]);
  const [fetchError, setFetchError] = useState(false);
  const [currentMonth, setCurrentMonth] = useState<Date>(
    new Date(today.getFullYear(), today.getMonth(), 1),
  );
  const [hoveredDate, setHoveredDate] = useState<string | null>(null);
  const [hoverPos, setHoverPos] = useState<{ top: number; left: number } | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    setFetchError(false);
    fetch(`${API}/calendar-data`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: unknown) => {
        if (!Array.isArray(data)) return;
        setCalDays(data as CalendarDay[]);
      })
      .catch(() => setFetchError(true));
  }, [refreshKey]);

  // Keep last entry per date (chronological order → last wins)
  const entriesByDate = useMemo(() => {
    const map = new Map<string, CalendarDay>();
    for (const d of calDays) map.set(d.date, d);
    return map;
  }, [calDays]);

  const streak = useMemo(() => computeStreak(calDays), [calDays]);

  const thisMonthCount = useMemo(() => {
    const prefix = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
    return calDays.filter((d) => d.date.startsWith(prefix)).length;
  }, [calDays, today]);

  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  const daysInMonth = getDaysInMonth(year, month);
  const firstDow = getFirstDayOfWeek(year, month);
  const isCurrentMonth = year === today.getFullYear() && month === today.getMonth();

  function prevMonth() {
    setCurrentMonth(new Date(year, month - 1, 1));
  }
  function nextMonth() {
    setCurrentMonth(new Date(year, month + 1, 1));
  }

  function handleDayEnter(date: string, e: React.MouseEvent) {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setHoverPos({ top: rect.top - 8, left: rect.right + 10 });
    setHoveredDate(date);
  }
  function handleDayLeave() {
    setHoveredDate(null);
    setHoverPos(null);
  }

  const hoveredEntry = hoveredDate ? (entriesByDate.get(hoveredDate) ?? null) : null;

  // Build grid: leading empty cells + day numbers
  const cells: (number | null)[] = [];
  for (let i = 0; i < firstDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  return (
    <div className="border-t border-slate-200/60 dark:border-white/[0.06]">
      {/* Header toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="w-full px-4 pt-3 pb-2 flex items-center justify-between
                   hover:bg-white/30 dark:hover:bg-white/[0.03] transition-colors duration-150"
      >
        <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500
                         uppercase tracking-widest">
          Life Dashboard
        </span>
        <span
          className={`text-[11px] text-slate-400 dark:text-slate-500
                      transition-transform duration-200 leading-none
                      ${collapsed ? '' : 'rotate-180'}`}
        >
          ▾
        </span>
      </button>

      {/* Stats strip — always visible */}
      <div className="px-4 pb-3 flex items-center gap-3 flex-wrap">
        {fetchError ? (
          <span className="text-[10px] text-slate-400/60 dark:text-slate-600 italic">
            Backend unreachable
          </span>
        ) : (
          <>
            {streak > 0 ? (
              <div className="flex items-center gap-1 text-[11px]">
                <span className="text-[13px] leading-none">🔥</span>
                <span className="font-semibold text-slate-700 dark:text-slate-200">{streak}</span>
                <span className="text-slate-400 dark:text-slate-500">
                  {streak === 1 ? 'day' : 'days'}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-1 text-[11px] text-slate-400 dark:text-slate-500">
                <span className="text-[12px] leading-none">✦</span>
                <span>Start a streak</span>
              </div>
            )}
            <div className="flex items-center gap-1 text-[11px]">
              <span className="text-[11px] leading-none">📅</span>
              <span className="font-semibold text-slate-700 dark:text-slate-200">{thisMonthCount}</span>
              <span className="text-slate-400 dark:text-slate-500">this month</span>
            </div>
            {calDays.length > 0 && (
              <div className="ml-auto text-[10px] text-slate-400/70 dark:text-slate-600 tabular-nums">
                {calDays.length} total
              </div>
            )}
          </>
        )}
      </div>

      {/* Calendar — collapsible */}
      {!collapsed && (
        <div className="px-3 pb-4 fade-in">
          {/* Month navigation */}
          <div className="flex items-center justify-between mb-2 px-0.5">
            <button
              onClick={prevMonth}
              className="w-6 h-6 flex items-center justify-center rounded-lg
                         text-slate-400 dark:text-slate-500
                         hover:text-indigo-500 dark:hover:text-indigo-400
                         hover:bg-indigo-50/60 dark:hover:bg-indigo-900/30
                         transition-colors duration-100 text-[13px] leading-none"
            >
              ‹
            </button>
            <span className="text-[11px] font-medium text-slate-600 dark:text-slate-300 tabular-nums">
              {MONTH_NAMES[month]} {year}
            </span>
            <button
              onClick={nextMonth}
              disabled={isCurrentMonth}
              className="w-6 h-6 flex items-center justify-center rounded-lg
                         text-slate-400 dark:text-slate-500
                         hover:text-indigo-500 dark:hover:text-indigo-400
                         hover:bg-indigo-50/60 dark:hover:bg-indigo-900/30
                         transition-colors duration-100 text-[13px] leading-none
                         disabled:opacity-20 disabled:cursor-default disabled:hover:bg-transparent
                         disabled:hover:text-slate-400"
            >
              ›
            </button>
          </div>

          {/* Weekday headers */}
          <div className="grid grid-cols-7 mb-1">
            {WEEKDAY_LABELS.map((d) => (
              <div
                key={d}
                className="text-center text-[9px] font-semibold
                           text-slate-400/70 dark:text-slate-600 py-0.5 uppercase tracking-wide"
              >
                {d}
              </div>
            ))}
          </div>

          {/* Day cells */}
          <div className="grid grid-cols-7 gap-y-0.5">
            {cells.map((day, i) => {
              if (!day) return <div key={`e-${i}`} />;

              const dateKey = toDateKey(year, month, day);
              const hasEntry = entriesByDate.has(dateKey);
              const isToday = dateKey === todayKey;
              const entry = entriesByDate.get(dateKey);

              return (
                <div
                  key={dateKey}
                  onMouseEnter={hasEntry ? (e) => handleDayEnter(dateKey, e) : undefined}
                  onMouseLeave={hasEntry ? handleDayLeave : undefined}
                  onClick={hasEntry && entry ? () => onDayClick(entry.timestamp) : undefined}
                  className={[
                    'relative flex flex-col items-center justify-start',
                    'pt-0.5 pb-1.5 rounded-lg select-none',
                    'text-[11px] tabular-nums leading-5',
                    'transition-colors duration-100',
                    isToday
                      ? 'ring-1 ring-indigo-400/50 dark:ring-indigo-400/35 bg-indigo-50/60 dark:bg-indigo-900/25'
                      : '',
                    hasEntry
                      ? 'cursor-pointer font-medium text-slate-700 dark:text-slate-200 hover:bg-indigo-50/80 dark:hover:bg-indigo-900/30'
                      : 'text-slate-400/60 dark:text-slate-600',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  {day}
                  {hasEntry && (
                    <span className="absolute bottom-0.5 w-[5px] h-[5px] rounded-full
                                     bg-indigo-500 dark:bg-indigo-400" />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Hover popup — fixed, appears to the right of the sidebar */}
      {hoveredEntry && hoverPos && (
        <div
          className="glass-popup fixed z-[200] w-52 rounded-2xl p-3.5 pointer-events-none"
          style={{ top: hoverPos.top, left: hoverPos.left }}
        >
          <div className="text-[10px] font-semibold text-indigo-500 dark:text-indigo-400
                          uppercase tracking-wider mb-1.5">
            {new Date(`${hoveredDate}T12:00:00`).toLocaleDateString('en-GB', {
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            })}
          </div>
          <div className="text-[13px] font-semibold text-slate-800 dark:text-slate-100
                          mb-1.5 leading-snug">
            {hoveredEntry.title || '—'}
          </div>
          <div className="text-[11px] text-slate-500 dark:text-slate-400
                          leading-relaxed line-clamp-4">
            {hoveredEntry.summary}
          </div>
          <div className="mt-2.5 text-[10px] text-indigo-400/60 dark:text-indigo-500/60
                          flex items-center gap-1">
            <span>Open chat</span>
            <span>→</span>
          </div>
        </div>
      )}
    </div>
  );
}
