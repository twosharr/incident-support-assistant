import { useState } from "react";
import { StatusSidebar } from "./components/StatusSidebar";
import { ChatWindow } from "./components/ChatWindow";
import { KanbanBoard } from "./components/KanbanBoard";

export default function App() {
  const [activeTab, setActiveTab] = useState<"chat" | "kanban">("chat");
  const [pendingQuery, setPendingQuery] = useState<string | null>(null);

  const handleAskAIFromKanban = (query: string) => {
    setPendingQuery(query);
    setActiveTab("chat");
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-teams-bg select-none">
      {/* Left sidebar: service status panel */}
      <StatusSidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden">
        {/* Unified Top Navigation Header */}
        <header className="bg-teams-surface border-b border-teams-border px-6 py-2.5 flex items-center justify-between shrink-0 z-10 shadow-sm">
          {/* Brand & Status */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-teams-purple flex items-center justify-center text-base shadow-sm">
              🤖
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold text-teams-text tracking-tight">AI Incident Support Assistant</h1>
                <span className="text-[10px] bg-green-500/20 text-green-400 border border-green-500/30 px-2 py-0.2 rounded-full font-medium">
                  Live
                </span>
              </div>
              <p className="text-[11px] text-teams-text-muted">
                {activeTab === "chat" ? "Conversational Incident Triage & Support" : "Visual Incident Lifecycle Management"}
              </p>
            </div>
          </div>

          {/* Central Segmented View Switcher */}
          <div className="flex items-center bg-teams-bg p-1 rounded-xl border border-teams-border shadow-inner">
            <button
              onClick={() => setActiveTab("chat")}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "chat"
                  ? "bg-teams-purple text-white shadow-md"
                  : "text-teams-text-muted hover:text-teams-text hover:bg-teams-surface"
              }`}
            >
              💬 AI Assistant Chat
            </button>
            <button
              onClick={() => setActiveTab("kanban")}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "kanban"
                  ? "bg-teams-purple text-white shadow-md"
                  : "text-teams-text-muted hover:text-teams-text hover:bg-teams-surface"
              }`}
            >
              📋 Incident Kanban Board
            </button>
          </div>

          {/* Right Action Info */}
          <div className="flex items-center gap-2">
            <a
              href="https://incidentsupportdemo.atlassian.net/jira/software/projects/SCRUM/boards/1"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-teams-text-muted hover:text-teams-text border border-teams-border hover:border-teams-purple px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
            >
              🔗 Jira Cloud
            </a>
          </div>
        </header>

        {/* View Component Container */}
        <main className="flex-1 min-h-0 h-full overflow-hidden relative">
          {activeTab === "chat" ? (
            <ChatWindow
              pendingQuery={pendingQuery}
              onClearPendingQuery={() => setPendingQuery(null)}
            />
          ) : (
            <KanbanBoard onAskAI={handleAskAIFromKanban} />
          )}
        </main>
      </div>
    </div>
  );
}
