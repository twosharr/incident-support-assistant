import { useEffect, useRef, useState } from "react";
import { MessageBubble } from "./MessageBubble";
import { QuickActions } from "./QuickActions";
import { useChat } from "../hooks/useChat";
import { useSpeech } from "../hooks/useSpeech";

interface Props {
  pendingQuery?: string | null;
  onClearPendingQuery?: () => void;
}

export function ChatWindow({ pendingQuery, onClearPendingQuery }: Props) {
  const { messages, isLoading, sendMessage, clearConversation } = useChat();
  const {
    isListening,
    isSpeaking,
    autoSpeak,
    setAutoSpeak,
    speechSupported,
    speak,
    stopSpeaking,
    toggleListening,
  } = useSpeech();

  const [inputValue, setInputValue] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle auto-speak for new assistant messages — only after typewriter finishes
  useEffect(() => {
    if (autoSpeak && messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === "assistant" && !lastMessage.isLoading && !lastMessage.isTyping) {
        speak(lastMessage.content);
      }
    }
  }, [messages, autoSpeak, speak]);

  useEffect(() => {
    if (pendingQuery && !isLoading) {
      sendMessage(pendingQuery);
      if (onClearPendingQuery) onClearPendingQuery();
    }
  }, [pendingQuery, isLoading, sendMessage, onClearPendingQuery]);

  const handleSend = async () => {
    const msg = inputValue.trim();
    if (!msg || isLoading) return;
    if (isListening) {
      toggleListening(() => {});
    }
    stopSpeaking();
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
    stopSpeaking();
    setInputValue(query);
    sendMessage(query);
  };

  const handleVoiceInput = () => {
    toggleListening(
      (text) => {
        setInputValue(text);
      },
      async (finalText) => {
        if (finalText.trim() && !isLoading) {
          setInputValue("");
          await sendMessage(finalText.trim());
        }
      },
      2000
    );
  };

  return (
    <div className="flex flex-col h-full bg-teams-bg overflow-hidden">
      {/* Sub-bar with Clear chat and voice controls */}
      <div className="flex items-center justify-between px-6 py-2 bg-teams-surface/50 border-b border-teams-border/60">
        <span className="text-xs text-teams-text-muted flex items-center gap-1.5">
          <span>💬</span>
          <span>Ask in natural language or speak via microphone (auto-sends on 2s silence).</span>
        </span>
        <div className="flex items-center gap-2">
          {/* Global Voice Readout Toggle */}
          <button
            onClick={() => {
              if (isSpeaking) stopSpeaking();
              setAutoSpeak(!autoSpeak);
            }}
            title={autoSpeak ? "Auto voice response is ON (Click to mute)" : "Auto voice response is OFF (Click to unmute)"}
            className={`text-xs flex items-center gap-1 px-2.5 py-1 rounded-md border transition-all ${
              autoSpeak
                ? "bg-teams-purple/20 border-teams-purple text-teams-purple"
                : "text-teams-text-muted hover:text-teams-text hover:bg-teams-surface border-teams-border"
            }`}
          >
            <span>{autoSpeak ? "🔊 Voice: ON" : "🔇 Voice: OFF"}</span>
          </button>

          {/* Clear Chat */}
          <button
            onClick={() => {
              stopSpeaking();
              clearConversation();
            }}
            className="text-xs text-teams-text-muted hover:text-teams-text hover:bg-teams-surface border border-teams-border px-2.5 py-1 rounded-md transition-colors"
          >
            🗑️ Clear Chat
          </button>
        </div>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            onSpeak={speak}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Quick actions */}
      <QuickActions onSelect={handleQuickAction} disabled={isLoading} />

      {/* Input area */}
      <div className="px-4 py-3 bg-teams-surface border-t border-teams-border">
        {/* Live Listening Banner Indicator */}
        {isListening && (
          <div className="flex items-center justify-between bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-1.5 mb-2 animate-pulse">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
              <span className="text-xs font-medium text-red-400">
                🎙️ Listening... Speak naturally (Auto-submits after 2 seconds of silence)
              </span>
            </div>
            <button
              onClick={handleSend}
              disabled={!inputValue.trim()}
              className="text-[11px] text-red-400 hover:text-red-300 font-semibold underline disabled:opacity-40"
            >
              Send Now ↵
            </button>
          </div>
        )}

        {/* AI Speaking Indicator */}
        {isSpeaking && (
          <div className="flex items-center justify-between bg-teams-purple/10 border border-teams-purple/30 rounded-lg px-3 py-1 mb-2">
            <div className="flex items-center gap-2 text-xs text-teams-purple">
              <span className="animate-bounce">🔊</span>
              <span>AI is reading response aloud...</span>
            </div>
            <button
              onClick={stopSpeaking}
              className="text-[11px] text-teams-purple hover:underline font-medium"
            >
              Stop Audio ⏹️
            </button>
          </div>
        )}

        <div className={`flex items-end gap-2 bg-teams-bg rounded-xl border px-3 py-2 transition-all ${
          isListening ? "border-red-500/60 ring-2 ring-red-500/20" : "border-teams-border focus-within:border-teams-purple"
        }`}>
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isListening ? "Listening to your voice..." : "Ask about incidents, outages, or troubleshooting steps... (Enter to send)"}
            rows={1}
            disabled={isLoading}
            className="flex-1 bg-transparent text-sm text-teams-text placeholder-teams-text-muted resize-none
                       focus:outline-none min-h-[36px] max-h-[120px] py-1.5 disabled:opacity-60"
            style={{ lineHeight: "1.5" }}
          />

          {/* Right-side Action Button Group (Copilot Style) */}
          <div className="flex items-center gap-1 pb-0.5">
            {/* Speech Recognition (Microphone) Button */}
            {speechSupported && (
              <button
                type="button"
                onClick={handleVoiceInput}
                disabled={isLoading}
                title={isListening ? "Click to stop listening" : "Click to speak with your voice (Voice-to-Text)"}
                className={`flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-all ${
                  isListening
                    ? "bg-red-500 hover:bg-red-600 text-white animate-pulse shadow-lg shadow-red-500/30"
                    : "bg-teams-surface hover:bg-teams-sidebar text-teams-text-muted hover:text-teams-text border border-teams-border"
                }`}
              >
                {isListening ? (
                  <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                )}
              </button>
            )}

            {/* Audio Speech Readout / Mute Toggle */}
            <button
              type="button"
              onClick={() => {
                if (isSpeaking) {
                  stopSpeaking();
                } else if (messages.length > 0) {
                  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant" && !m.isLoading);
                  if (lastAssistantMsg) speak(lastAssistantMsg.content);
                }
              }}
              title={isSpeaking ? "Stop AI voice playback" : "Read last AI response aloud"}
              className={`flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-all ${
                isSpeaking
                  ? "bg-teams-purple text-white animate-pulse"
                  : "bg-teams-surface hover:bg-teams-sidebar text-teams-text-muted hover:text-teams-text border border-teams-border"
              }`}
            >
              {isSpeaking ? (
                <span className="text-xs font-bold">⏹️</span>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                </svg>
              )}
            </button>

            {/* Send Button */}
            <button
              onClick={handleSend}
              disabled={isLoading || !inputValue.trim()}
              title="Send message (Enter)"
              className="flex-shrink-0 w-9 h-9 bg-teams-purple hover:bg-teams-purple-dark
                         disabled:opacity-40 disabled:cursor-not-allowed rounded-lg
                         flex items-center justify-center transition-colors shadow-md shadow-teams-purple/20"
            >
              <svg className="w-4 h-4 text-white rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
        <p className="text-[11px] text-teams-text-muted mt-1.5 text-center flex items-center justify-center gap-2">
          <span>🎙️ Voice recognition enabled</span>
          <span>•</span>
          <span>🔊 Natural Speech Synthesis</span>
          <span>•</span>
          <span>Connected to live ITSM & Jira Cloud</span>
        </p>
      </div>
    </div>
  );
}

