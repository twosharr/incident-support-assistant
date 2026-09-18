import { useEffect, useRef, useState } from "react";
import { MessageBubble } from "./MessageBubble";
import { QuickActions } from "./QuickActions";
import { useChat } from "../hooks/useChat";

export function ChatWindow() {
  const { messages, isLoading, sendMessage, clearConversation } = useChat();
  const [inputValue, setInputValue] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const msg = inputValue.trim();
    if (!msg || isLoading) return;
    setInputValue("");
    await sendMessage(msg);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuickAction = (query: string) => {
    setInputValue(query);
    sendMessage(query);
  };

  return (
    <div className="flex flex-col h-screen bg-teams-bg">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 bg-teams-surface border-b border-teams-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-teams-purple flex items-center justify-center text-lg">🤖</div>
          <div>
            <h1 className="text-sm font-semibold text-teams-text">AI Incident Support Assistant</h1>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-xs text-teams-text-muted">Online • Mock LLM Mode</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-teams-text-muted hover:text-teams-text border border-teams-border px-2.5 py-1 rounded-md transition-colors"
          >
            📖 API Docs
          </a>
          <button
            onClick={clearConversation}
            className="text-xs text-teams-text-muted hover:text-teams-text border border-teams-border px-2.5 py-1 rounded-md transition-colors"
          >
            🗑️ Clear
          </button>
        </div>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Quick actions */}
      <QuickActions onSelect={handleQuickAction} disabled={isLoading} />

      {/* Input area */}
      <div className="px-4 py-3 bg-teams-surface border-t border-teams-border">
        <div className="flex items-end gap-2 bg-teams-bg rounded-xl border border-teams-border px-3 py-2">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about incidents, outages, or troubleshooting steps... (Enter to send)"
            rows={1}
            disabled={isLoading}
            className="flex-1 bg-transparent text-sm text-teams-text placeholder-teams-text-muted resize-none
                       focus:outline-none min-h-[36px] max-h-[120px] py-1.5 disabled:opacity-60"
            style={{ lineHeight: "1.5" }}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !inputValue.trim()}
            className="flex-shrink-0 w-9 h-9 bg-teams-purple hover:bg-teams-purple-dark
                       disabled:opacity-40 disabled:cursor-not-allowed rounded-lg
                       flex items-center justify-center transition-colors"
          >
            <svg className="w-4 h-4 text-white rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <p className="text-xs text-teams-text-muted mt-1.5 text-center">
          AI responses are generated from mock data. Always verify critical information with your ITSM system.
        </p>
      </div>
    </div>
  );
}
