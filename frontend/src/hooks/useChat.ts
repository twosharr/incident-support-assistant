import { useState, useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { chatApi } from "../api/client";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  sources?: Array<{ type: string; id?: string; title?: string; service?: string }>;
  tools_used?: string[];
  isLoading?: boolean;
}

const CONVERSATION_ID_KEY = "incident-assistant-conv-id";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: `## 👋 Welcome to AI Incident Support Assistant!

I can help you with:
- 📋 **Incident Status** — *"What is the status of INC12345?"*
- 🚨 **Active Outages** — *"Is there an outage affecting the payment service?"*
- 🔍 **Past Incidents** — *"How was a similar incident resolved in the past?"*
- 🔧 **Troubleshooting** — *"What are the troubleshooting steps for database issues?"*
- 📊 **Service Health** — *"Show me the status of all services"*
- 📚 **Knowledge Base** — *"How do I manage database connection pools?"*

What can I help you with today?`,
      timestamp: new Date().toISOString(),
    },
  ]);

  const [isLoading, setIsLoading] = useState(false);
  const conversationId = useRef(
    localStorage.getItem(CONVERSATION_ID_KEY) || uuidv4()
  );

  // Persist conversation ID
  localStorage.setItem(CONVERSATION_ID_KEY, conversationId.current);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: Message = {
      id: uuidv4(),
      role: "user",
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };

    const loadingMessage: Message = {
      id: "loading",
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setIsLoading(true);

    try {
      const response = await chatApi.sendMessage(content, conversationId.current);

      const assistantMessage: Message = {
        id: uuidv4(),
        role: "assistant",
        content: response.response,
        timestamp: new Date().toISOString(),
        sources: response.sources,
        tools_used: response.tools_used,
      };

      setMessages((prev) =>
        prev.filter((m) => m.id !== "loading").concat(assistantMessage)
      );
    } catch (error) {
      const errorMessage: Message = {
        id: uuidv4(),
        role: "assistant",
        content: "⚠️ **Connection Error**\n\nI couldn't connect to the backend. Please make sure the server is running at `http://localhost:8000`.",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) =>
        prev.filter((m) => m.id !== "loading").concat(errorMessage)
      );
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clearConversation = useCallback(() => {
    const newId = uuidv4();
    conversationId.current = newId;
    localStorage.setItem(CONVERSATION_ID_KEY, newId);
    setMessages([]);
  }, []);

  return { messages, isLoading, sendMessage, clearConversation };
}
