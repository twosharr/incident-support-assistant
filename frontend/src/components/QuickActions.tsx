interface Props {
  onSelect: (query: string) => void;
  disabled: boolean;
}

const QUICK_ACTIONS = [
  { icon: "📋", label: "INC12345 Status", query: "What is the status of INC12345?" },
  { icon: "🚨", label: "Payment Outage?", query: "Is there an outage affecting the payment service?" },
  { icon: "🔍", label: "Similar Past Incidents", query: "Show me past incidents similar to payment gateway timeout" },
  { icon: "🔧", label: "Troubleshooting Steps", query: "What are the troubleshooting steps for payment issues?" },
  { icon: "📊", label: "All Services Status", query: "Show me the status of all services" },
  { icon: "📚", label: "DB Connection Guide", query: "How do I manage database connection pools?" },
];

export function QuickActions({ onSelect, disabled }: Props) {
  return (
    <div className="px-4 py-2 border-t border-teams-border">
      <p className="text-xs text-teams-text-muted mb-2">💡 Suggested queries:</p>
      <div className="flex flex-wrap gap-2">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.query}
            onClick={() => onSelect(action.query)}
            disabled={disabled}
            className="text-xs bg-teams-sidebar hover:bg-teams-border border border-teams-border
                       text-teams-text-muted hover:text-teams-text rounded-full px-3 py-1
                       transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {action.icon} {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}
