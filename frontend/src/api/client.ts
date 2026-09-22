import axios from "axios";

const API_BASE = "/api";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ChatResponse {
  response: string;
  sources: Array<{ type: string; id?: string; title?: string; service?: string; status?: string }>;
  tools_used: string[];
  conversation_id: string;
}

export interface Incident {
  id: string;
  title: string;
  status: string;
  priority: string;
  severity: string;
  service: string;
  assigned_to: string;
  created_at: string;
  updated_at: string;
  estimated_resolution?: string;
  description: string;
  impact: string;
  workaround?: string;
  tags: string[];
  root_cause?: string;
  resolution?: string;
  category: string;
  environment: string;
  resolved_at?: string;
  mttr_minutes?: number;
  duration_text?: string;
  timeline?: Array<{ time: string; event: string }>;
  jira_url?: string;
}

export interface ServiceHealth {
  name: string;
  display_name: string;
  status: "healthy" | "degraded" | "down";
  uptime_percent: number;
  error_rate_percent: number;
  p99_latency_ms?: number;
  active_incidents: string[];
  team: string;
}

export const chatApi = {
  sendMessage: async (
    message: string,
    conversationId: string
  ): Promise<ChatResponse> => {
    const response = await axios.post(`${API_BASE}/chat`, {
      message,
      conversation_id: conversationId,
    });
    return response.data;
  },
};

export const incidentsApi = {
  listActive: async (): Promise<Incident[]> => {
    const response = await axios.get(`${API_BASE}/incidents/active`);
    return response.data;
  },
  getAllServicesHealth: async (): Promise<ServiceHealth[]> => {
    const response = await axios.get(`${API_BASE}/incidents/services/health`);
    return response.data;
  },
};
