import { useEffect, useState } from "react";
import { Incident } from "../api/client";

interface Props {
  onAskAI: (query: string) => void;
}

const COLUMNS = [
  { id: "open", title: "Open / Active", emoji: "🔴", color: "border-red-500/50 bg-red-950/10" },
  { id: "in_progress", title: "In Progress", emoji: "🔄", color: "border-blue-500/50 bg-blue-950/10" },
  { id: "monitoring", title: "Monitoring", emoji: "👀", color: "border-yellow-500/50 bg-yellow-950/10" },
  { id: "resolved", title: "Resolved / Closed", emoji: "✅", color: "border-green-500/50 bg-green-950/10" },
];

const PRIORITY_BADGES: Record<string, string> = {
  P1: "bg-red-500/20 text-red-400 border-red-500/40",
  Critical: "bg-red-500/20 text-red-400 border-red-500/40",
  Highest: "bg-red-500/20 text-red-400 border-red-500/40",
  P2: "bg-orange-500/20 text-orange-400 border-orange-500/40",
  High: "bg-orange-500/20 text-orange-400 border-orange-500/40",
  P3: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
  Medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
  P4: "bg-blue-500/20 text-blue-400 border-blue-500/40",
  Low: "bg-blue-500/20 text-blue-400 border-blue-500/40",
};

export function KanbanBoard({ onAskAI }: Props) {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [filterService, setFilterService] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const loadIncidents = async () => {
    setLoading(true);
    try {
      // Fetch mock incidents + live Jira tickets in parallel
      const [mockRes, jiraRes] = await Promise.allSettled([
        fetch("/api/incidents"),
        fetch("/api/incidents/jira"),
      ]);

      let combined: Incident[] = [];

      if (mockRes.status === "fulfilled" && mockRes.value.ok) {
        const mockData = await mockRes.value.json();
        combined = [...combined, ...mockData];
      }

      if (jiraRes.status === "fulfilled" && jiraRes.value.ok) {
        const jiraData = await jiraRes.value.json();
        combined = [...combined, ...jiraData];
      }

      setIncidents(combined);
    } catch (e) {
      console.error("Failed to load incidents:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, []);

  const getColumnIncidents = (colId: string) => {
    return incidents.filter((inc) => {
      // Filter by search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const match =
          inc.id.toLowerCase().includes(q) ||
          inc.title.toLowerCase().includes(q) ||
          (inc.service && inc.service.toLowerCase().includes(q)) ||
          (inc.assigned_to && inc.assigned_to.toLowerCase().includes(q));
        if (!match) return false;
      }

      // Filter by service
      if (filterService !== "all" && inc.service?.toLowerCase() !== filterService.toLowerCase()) {
        return false;
      }

      const st = inc.status?.toLowerCase() || "";
      if (colId === "open") return st === "open" || st === "active" || st === "to do";
      if (colId === "in_progress") return st === "in progress" || st === "triaging";
      if (colId === "monitoring") return st === "monitoring" || st === "in review" || st === "scheduled";
      if (colId === "resolved") return st === "resolved" || st === "done" || st === "closed";
      return false;
    });
  };

  const services = Array.from(new Set(incidents.map((i) => i.service).filter(Boolean)));

  return (
    <div className="flex flex-col h-full bg-teams-bg overflow-hidden">
      {/* Top Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-3.5 bg-teams-surface border-b border-teams-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-teams-purple flex items-center justify-center text-lg">📋</div>
          <div>
            <h1 className="text-sm font-semibold text-teams-text">Incident Kanban Board & Lifecycle</h1>
            <p className="text-xs text-teams-text-muted">Real-time incident workflow & status tracking</p>
          </div>
        </div>

        {/* Filter & Search */}
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tickets, services, assignees..."
            className="text-xs bg-teams-bg border border-teams-border text-teams-text rounded-lg px-3 py-1.5 w-56 focus:outline-none focus:border-teams-purple"
          />

          <select
            value={filterService}
            onChange={(e) => setFilterService(e.target.value)}
            className="text-xs bg-teams-bg border border-teams-border text-teams-text rounded-lg px-2.5 py-1.5 focus:outline-none"
          >
            <option value="all">All Services ({incidents.length})</option>
            {services.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <button
            onClick={loadIncidents}
            className="text-xs bg-teams-sidebar hover:bg-teams-border border border-teams-border text-teams-text px-3 py-1.5 rounded-lg transition-colors"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Kanban Columns Grid */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden p-6">
        {loading ? (
          <div className="flex items-center justify-center h-full text-teams-text-muted text-sm">
            Loading incidents...
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-4 h-full min-w-[1000px]">
            {COLUMNS.map((col) => {
              const colIncidents = getColumnIncidents(col.id);
              return (
                <div
                  key={col.id}
                  className={`flex flex-col h-full rounded-xl border ${col.color} bg-teams-sidebar/50 p-3 overflow-hidden`}
                >
                  {/* Column Header */}
                  <div className="flex items-center justify-between pb-3 border-b border-teams-border mb-3 px-1">
                    <div className="flex items-center gap-2">
                      <span>{col.emoji}</span>
                      <h2 className="text-xs font-semibold text-teams-text uppercase tracking-wider">{col.title}</h2>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-teams-surface text-teams-text-muted font-mono">
                      {colIncidents.length}
                    </span>
                  </div>

                  {/* Cards list */}
                  <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
                    {colIncidents.length === 0 ? (
                      <div className="text-center py-8 text-xs text-teams-text-muted/60 italic">
                        No incidents in this state
                      </div>
                    ) : (
                      colIncidents.map((inc) => (
                        <div
                          key={inc.id}
                          onClick={() => setSelectedIncident(inc)}
                          className="bg-teams-surface hover:border-teams-purple border border-teams-border rounded-xl p-3.5 cursor-pointer transition-all shadow-sm hover:shadow-md group"
                        >
                          {/* Top row: ID + Priority */}
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="text-xs font-bold font-mono text-teams-purple group-hover:text-purple-400">
                              {inc.id}
                            </span>
                            <span
                              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                                PRIORITY_BADGES[inc.priority] || "bg-gray-500/20 text-gray-300 border-gray-500/40"
                              }`}
                            >
                              {inc.priority}
                            </span>
                          </div>

                          {/* Title */}
                          <h3 className="text-xs font-medium text-teams-text line-clamp-2 mb-2 leading-relaxed">
                            {inc.title}
                            {inc.category === "jira" && (
                              <span className="ml-1.5 text-[9px] bg-blue-500/20 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded-full font-semibold align-middle">
                                🎫 Jira
                              </span>
                            )}
                          </h3>

                          {/* Metadata row */}
                          <div className="flex items-center justify-between text-[11px] text-teams-text-muted pt-2 border-t border-teams-border/60">
                            <span className="truncate max-w-[110px] bg-teams-bg px-1.5 py-0.5 rounded text-[10px]">
                              🏷️ {inc.service || "general"}
                            </span>
                            <span>⏱️ {inc.duration_text || "Active"}</span>
                          </div>

                          {/* Quick AI Action on hover */}
                          <div className="mt-2.5 pt-2 border-t border-teams-border/40 flex items-center justify-between opacity-80 group-hover:opacity-100">
                            <span className="text-[10px] text-teams-text-muted truncate">
                              👤 {inc.assigned_to?.split(" ")[0] || "Unassigned"}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onAskAI(`What is the status and timeline of ${inc.id}?`);
                              }}
                              className="text-[10px] text-teams-purple hover:text-white bg-teams-purple/20 hover:bg-teams-purple px-2 py-0.5 rounded transition-colors font-medium"
                            >
                              💬 Ask AI
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Ticket Detail Modal */}
      {selectedIncident && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-teams-surface border border-teams-border rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="flex items-start justify-between p-6 border-b border-teams-border bg-teams-sidebar">
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-sm font-mono font-bold text-teams-purple">{selectedIncident.id}</span>
                  <span
                    className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
                      PRIORITY_BADGES[selectedIncident.priority] || "bg-gray-500/20 text-gray-300 border-gray-500/40"
                    }`}
                  >
                    {selectedIncident.priority} • {selectedIncident.status}
                  </span>
                  {selectedIncident.jira_url && (
                    <a
                      href={selectedIncident.jira_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-400 hover:underline flex items-center gap-1 ml-1"
                    >
                      🔗 Open in Jira
                    </a>
                  )}
                </div>
                <h2 className="text-base font-semibold text-teams-text">{selectedIncident.title}</h2>
              </div>
              <button
                onClick={() => setSelectedIncident(null)}
                className="text-teams-text-muted hover:text-teams-text text-xl p-1 rounded-lg hover:bg-teams-surface"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4 text-sm text-teams-text">
              {/* Info Grid */}
              <div className="grid grid-cols-2 gap-3 bg-teams-bg p-3.5 rounded-xl border border-teams-border text-xs">
                <div>
                  <span className="text-teams-text-muted">Assigned Team:</span>
                  <p className="font-medium text-teams-text mt-0.5">{selectedIncident.assigned_to || "Unassigned"}</p>
                </div>
                <div>
                  <span className="text-teams-text-muted">Service / Component:</span>
                  <p className="font-medium text-teams-text mt-0.5">{selectedIncident.service || "General"}</p>
                </div>
                <div>
                  <span className="text-teams-text-muted">Created / Started:</span>
                  <p className="font-medium text-teams-text mt-0.5">
                    {selectedIncident.created_at ? selectedIncident.created_at.replace("T", " ").substring(0, 16) : "N/A"}
                  </p>
                </div>
                <div>
                  <span className="text-teams-text-muted">Duration (MTTR):</span>
                  <p className="font-medium text-green-400 mt-0.5">{selectedIncident.duration_text || "Ongoing"}</p>
                </div>
              </div>

              {/* Description */}
              <div>
                <h4 className="text-xs font-semibold text-teams-text-muted uppercase tracking-wider mb-1">
                  Description
                </h4>
                <p className="text-xs bg-teams-bg p-3 rounded-lg border border-teams-border leading-relaxed">
                  {selectedIncident.description}
                </p>
              </div>

              {/* Workaround */}
              {selectedIncident.workaround && (
                <div className="bg-yellow-950/20 border border-yellow-500/30 p-3 rounded-lg">
                  <h4 className="text-xs font-semibold text-yellow-400 mb-1">🔧 Active Workaround</h4>
                  <p className="text-xs text-yellow-200/90">{selectedIncident.workaround}</p>
                </div>
              )}

              {/* Root Cause & Resolution if resolved */}
              {selectedIncident.resolution && (
                <div className="bg-green-950/20 border border-green-500/30 p-3 rounded-lg">
                  <h4 className="text-xs font-semibold text-green-400 mb-1">✅ Resolution & Root Cause</h4>
                  <p className="text-xs text-green-200/90">{selectedIncident.resolution}</p>
                  {selectedIncident.root_cause && (
                    <p className="text-xs text-green-300/70 mt-1">Root Cause: {selectedIncident.root_cause}</p>
                  )}
                </div>
              )}

              {/* Timeline */}
              {selectedIncident.timeline && selectedIncident.timeline.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-teams-text-muted uppercase tracking-wider mb-2">
                    ⏱️ Event Timeline
                  </h4>
                  <div className="space-y-1.5">
                    {selectedIncident.timeline.map((ev, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-3 text-xs bg-teams-bg px-3 py-2 rounded-lg border border-teams-border/60"
                      >
                        <span className="font-mono text-teams-text-muted shrink-0">{ev.time}</span>
                        <span className="text-teams-text">{ev.event}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-teams-border bg-teams-sidebar flex items-center justify-between">
              <button
                onClick={() => {
                  const id = selectedIncident.id;
                  setSelectedIncident(null);
                  onAskAI(`Show me the troubleshooting steps and timeline for ${id}`);
                }}
                className="text-xs bg-teams-purple hover:bg-teams-purple-dark text-white font-medium px-4 py-2 rounded-lg transition-colors flex items-center gap-1.5"
              >
                💬 Ask Assistant About This Ticket
              </button>
              <button
                onClick={() => setSelectedIncident(null)}
                className="text-xs bg-teams-surface hover:bg-teams-border border border-teams-border text-teams-text px-4 py-2 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
