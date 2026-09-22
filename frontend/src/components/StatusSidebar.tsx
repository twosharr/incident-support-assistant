import { useEffect, useState } from "react";
import { incidentsApi, ServiceHealth } from "../api/client";

const STATUS_COLORS = {
  healthy: "bg-green-500",
  degraded: "bg-yellow-500",
  down: "bg-red-500",
};

export function StatusSidebar() {
  const [services, setServices] = useState<ServiceHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await incidentsApi.getAllServicesHealth();
        setServices(data);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 30000); // refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const degraded = services.filter((s) => s.status !== "healthy");
  const healthy = services.filter((s) => s.status === "healthy");
  const overall = services.length === 0 ? "unknown" : degraded.length === 0 ? "healthy" : "degraded";

  return (
    <div className="w-72 flex-shrink-0 bg-teams-sidebar border-r border-teams-border flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-teams-border">
        <h2 className="text-sm font-semibold text-teams-text">📊 Service Status</h2>
        <div className="flex items-center gap-1.5 mt-1">
          <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[overall as keyof typeof STATUS_COLORS] || "bg-gray-500"}`} />
          <span className="text-xs text-teams-text-muted capitalize">{overall === "healthy" ? "All Systems Operational" : `${degraded.length} service(s) affected`}</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3">
        {loading && (
          <div className="text-xs text-teams-text-muted text-center py-4 animate-pulse">Loading status...</div>
        )}

        {error && (
          <div className="text-xs text-red-400 text-center py-4">
            ⚠️ Cannot reach backend.<br />Start the server first.
          </div>
        )}

        {!loading && !error && (
          <>
            {degraded.length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-semibold text-teams-text-muted uppercase tracking-wider mb-2 px-1">
                  Issues Detected
                </p>
                {degraded.map((svc) => (
                  <ServiceRow key={svc.name} service={svc} />
                ))}
              </div>
            )}

            <div>
              <p className="text-xs font-semibold text-teams-text-muted uppercase tracking-wider mb-2 px-1">
                Healthy Services
              </p>
              {healthy.map((svc) => (
                <ServiceRow key={svc.name} service={svc} />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-teams-border">
        <p className="text-xs text-teams-text-muted text-center">
          Auto-refreshes every 30s
        </p>
      </div>
    </div>
  );
}

function ServiceRow({ service: svc }: { service: ServiceHealth }) {
  return (
    <div className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-teams-surface transition-colors mb-0.5">
      <div className="flex items-center gap-2 min-w-0">
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_COLORS[svc.status as keyof typeof STATUS_COLORS]}`} />
        <span className="text-xs text-teams-text truncate">{svc.display_name}</span>
      </div>
      <div className="flex-shrink-0 ml-2">
        {svc.status !== "healthy" ? (
          <span className="text-xs text-yellow-400">{svc.error_rate_percent}% err</span>
        ) : (
          <span className="text-xs text-green-400">{svc.uptime_percent}%</span>
        )}
      </div>
    </div>
  );
}
