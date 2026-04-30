import type { ChatMessage as ChatMessageType } from '../types';

interface Props {
  message: ChatMessageType;
  isStreaming?: boolean;
}

export default function ChatMessageBubble({ message, isStreaming }: Props) {
  const isUser = message.role === 'user';

  return (
    <div className={`msg-enter flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full shrink-0 mr-2.5 mt-0.5
                        bg-gradient-to-br from-indigo-400 to-indigo-600
                        dark:from-indigo-500 dark:to-indigo-700
                        flex items-center justify-center
                        shadow-sm shadow-indigo-500/25 text-[11px] font-bold text-white">
          T
        </div>
      )}
      <div
        className={`max-w-[76%] text-[14px] leading-relaxed
          ${isUser
            ? `rounded-2xl rounded-br-md px-4 py-3
               bg-gradient-to-br from-indigo-500 to-indigo-700
               dark:from-indigo-500 dark:to-indigo-600
               text-white shadow-md shadow-indigo-500/20`
            : `rounded-2xl rounded-bl-md px-4 py-3
               bg-white/85 dark:bg-slate-800/70
               border border-slate-200/70 dark:border-white/[0.09]
               text-slate-800 dark:text-slate-100
               shadow-sm shadow-black/5 dark:shadow-black/20
               backdrop-blur-sm`
          }`}
      >
        <span style={{ whiteSpace: 'pre-wrap' }}>{message.content}</span>
        {isStreaming && (
          <span className="cursor-blink inline-block w-[2px] h-[14px] bg-current ml-1 align-middle rounded-full" />
        )}
      </div>
    </div>
  );
}
