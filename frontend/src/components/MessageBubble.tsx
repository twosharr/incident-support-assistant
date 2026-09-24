import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Message } from "../hooks/useChat";

interface Props {
  message: Message;
  onSpeak?: (text: string) => void;
  isSpeaking?: boolean;
}

const TOOL_LABELS: Record<string, { icon: string; label: string }> = {
  get_incident: { icon: "📋", label: "Incident Lookup" },
  list_active_incidents: { icon: "🚨", label: "Active Incidents" },
  get_service_health: { icon: "📊", label: "Service Health" },
  find_similar_incidents: { icon: "🔍", label: "Historical Search" },
  get_troubleshooting_steps: { icon: "🔧", label: "Playbook" },
  get_comprehensive_troubleshooting: { icon: "🧠", label: "Smart Investigation" },
  get_incident_timeline: { icon: "⏱️", label: "Timeline & MTTR" },
  get_mttr_metrics: { icon: "📈", label: "MTTR Analytics" },
  search_knowledge_base: { icon: "📚", label: "Knowledge Base" },
  get_all_services_status: { icon: "🗺️", label: "System Status" },
};

const markdownComponents: Components = {
  code({ className, children, ...props }) {
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
};

export function MessageBubble({ message, onSpeak }: Props) {
  const isUser = message.role === "user";

  if (message.isLoading) {
    return (
      <div className="flex items-start gap-3 mb-4">
        <div className="w-8 h-8 rounded-full bg-teams-purple flex items-center justify-center text-sm flex-shrink-0">
          🤖
        </div>
        <div className="bg-teams-surface rounded-2xl rounded-tl-none px-4 py-3 max-w-2xl">
          <div className="flex gap-1.5 items-center py-1">
            <div className="w-2 h-2 rounded-full bg-teams-purple animate-bounce" style={{ animationDelay: "0ms" }} />
            <div className="w-2 h-2 rounded-full bg-teams-purple animate-bounce" style={{ animationDelay: "150ms" }} />
            <div className="w-2 h-2 rounded-full bg-teams-purple animate-bounce" style={{ animationDelay: "300ms" }} />
            <span className="text-teams-text-muted text-xs ml-1">AI is thinking...</span>
          </div>
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="flex items-start gap-3 mb-4 flex-row-reverse">
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm flex-shrink-0 font-bold">
          U
        </div>
        <div className="bg-teams-purple rounded-2xl rounded-tr-none px-4 py-2.5 max-w-xl">
          <p className="text-white text-sm">{message.content}</p>
        </div>
      </div>
    );
  }

  const toolInfo = message.tools_used?.[0]
    ? TOOL_LABELS[message.tools_used[0]]
    : null;

  return (
    <div className="flex items-start gap-3 mb-4 group">
      <div className="w-8 h-8 rounded-full bg-teams-purple-dark flex items-center justify-center text-sm flex-shrink-0">
        🤖
      </div>
      <div className="flex-1 max-w-3xl">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            {toolInfo && (
              <span className="text-xs text-teams-text-muted bg-teams-sidebar px-2 py-0.5 rounded-full border border-teams-border">
                {toolInfo.icon} {toolInfo.label}
              </span>
            )}
          </div>
          {onSpeak && (
            <button
              onClick={() => onSpeak(message.content)}
              title="Read aloud with AI voice"
              className="text-xs text-teams-text-muted hover:text-teams-purple hover:bg-teams-surface px-2 py-0.5 rounded transition-all opacity-80 group-hover:opacity-100 flex items-center gap-1 border border-transparent hover:border-teams-border"
            >
              <span>🔊</span>
              <span className="text-[11px]">Listen</span>
            </button>
          )}
        </div>
        <div className="bg-teams-surface rounded-2xl rounded-tl-none px-4 py-3 border border-teams-border">
          <div className="prose-teams text-sm text-teams-text">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {message.displayContent ?? message.content}
            </ReactMarkdown>
            {message.isTyping && (
              <span
                className="inline-block w-[2px] h-4 bg-teams-purple ml-0.5 align-middle"
                style={{ animation: "blink 0.7s step-end infinite" }}
              />
            )}
          </div>
          {message.sources && message.sources.length > 0 && (
            <div className="mt-3 pt-2 border-t border-teams-border">
              <p className="text-xs text-teams-text-muted mb-1">📎 Sources:</p>
              <div className="flex flex-wrap gap-1.5">
                {message.sources.slice(0, 4).map((s, i) => (
                  <span
                    key={i}
                    className="text-xs bg-teams-sidebar border border-teams-border px-2 py-0.5 rounded-full text-teams-text-muted"
                  >
                    {s.id || s.service || s.title || s.type}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
        <p className="text-xs text-teams-text-muted mt-1 ml-1">
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}

