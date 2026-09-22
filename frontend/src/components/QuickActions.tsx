import { useState } from "react";

interface Props {
  onSelect: (query: string) => void;
  disabled: boolean;
}

const QUICK_ACTIONS = [
  { icon: "📋", label: "INC12345 Status", query: "What is the status of INC12345?" },
  { icon: "⏱️", label: "INC12345 Timeline & MTTR", query: "Show me the timeline of events for INC12345" },
  { icon: "🔗", label: "Live Jira Ticket (SCRUM-5)", query: "What is the status of Jira ticket SCRUM-5?" },
  { icon: "📊", label: "Average MTTR Analytics", query: "What is our average MTTR across incidents?" },
  { icon: "🚨", label: "Payment Outage?", query: "Is there an outage affecting the payment service?" },
  { icon: "🔍", label: "Similar Past Incidents", query: "Show me past incidents similar to payment gateway timeout" },
  { icon: "🔧", label: "Troubleshooting Steps", query: "What are the troubleshooting steps for payment issues?" },
  { icon: "🗺️", label: "All Services Status", query: "Show me the status of all services" },
];

export function QuickActions({ onSelect, disabled }: Props) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="px-4 py-2 border-t border-teams-border/70 bg-teams-surface/30">
      {/* Header Toggle */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between text-xs text-teams-text-muted hover:text-teams-text py-1 transition-colors group focus:outline-none"
      >
        <div className="flex items-center gap-1.5">
          <span>💡</span>
          <span className="font-medium">Suggested queries</span>
          <span className="text-[10px] bg-teams-sidebar text-teams-text-muted px-1.5 py-0.5 rounded-full border border-teams-border/50">
            {QUICK_ACTIONS.length}
          </span>
        </div>
        <div className="flex items-center gap-1 text-[11px] text-teams-text-muted group-hover:text-teams-purple transition-colors">
          <span>{isOpen ? "Hide" : "Show"}</span>
          <svg
            className={`w-3.5 h-3.5 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Collapsible Action Pills */}
      {isOpen && (
        <div className="flex flex-wrap gap-2 pt-2 pb-1 transition-all duration-200 animate-fadeIn">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.query}
              onClick={() => onSelect(action.query)}
              disabled={disabled}
              className="text-xs bg-teams-sidebar hover:bg-teams-border border border-teams-border
                         text-teams-text-muted hover:text-teams-text rounded-full px-3 py-1
                         transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
            >
              {action.icon} {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

