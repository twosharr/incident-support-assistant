import { useState, useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { chatApi } from "../api/client";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  displayContent?: string;  // animated portion shown so far
  isLoading?: boolean;
  isTyping?: boolean;       // currently in typewriter animation
  timestamp: string;
  sources?: Array<{ type: string; id?: string; title?: string; service?: string }>;
  tools_used?: string[];
}

const CONVERSATION_ID_KEY = "incident-assistant-conv-id";
const TYPING_CHARS_PER_TICK = 4; // chars revealed per tick
const TYPING_SPEED_MS = 8;       // ms between ticks (~40ms per word)

const WELCOME_MSG = `## 👋 Welcome to AI Incident Support Assistant!\n\nI can help you with:\n- 📋 **Incident Status** — *"What is the status of INC12345?"*\n- 🚨 **Active Outages** — *"Is there an outage affecting the payment service?"*\n- 🔍 **Past Incidents** — *"How was a similar incident resolved in the past?"*\n- 🔧 **Troubleshooting** — *"What are the troubleshooting steps for database issues?"*\n- 📊 **Service Health** — *"Show me the status of all services"*\n- 📚 **Knowledge Base** — *"How do I manage database connection pools?"*\n\nWhat can I help you with today?`;

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: WELCOME_MSG,
      displayContent: WELCOME_MSG, // welcome shown immediately, no animation
      timestamp: new Date().toISOString(),
    },
  ]);

  const [isLoading, setIsLoading] = useState(false);
  const conversationId = useRef(
    localStorage.getItem(CONVERSATION_ID_KEY) || uuidv4()
  );
  const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Persist conversation ID
  localStorage.setItem(CONVERSATION_ID_KEY, conversationId.current);

  /** Animate displayContent char-by-char for the given message id */
  const animateTyping = useCallback((msgId: string, fullText: string) => {
    if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
    let index = 0;

    const tick = () => {
      index = Math.min(index + TYPING_CHARS_PER_TICK, fullText.length);
      const slice = fullText.slice(0, index);
      const done = index >= fullText.length;

      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? { ...m, displayContent: slice, isTyping: !done }
            : m
        )
      );

      if (!done) {
        typingTimerRef.current = setTimeout(tick, TYPING_SPEED_MS);
      }
    };

    tick();
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      const userMessage: Message = {
        id: uuidv4(),
        role: "user",
        content: content.trim(),
        displayContent: content.trim(),
        timestamp: new Date().toISOString(),
      };

      const loadingMessage: Message = {
        id: "loading",
        role: "assistant",
        content: "",
        displayContent: "",
        timestamp: new Date().toISOString(),
        isLoading: true,
      };

      setMessages((prev) => [...prev, userMessage, loadingMessage]);
      setIsLoading(true);

      try {
        const response = await chatApi.sendMessage(content, conversationId.current);

        const newId = uuidv4();
        const assistantMessage: Message = {
          id: newId,
          role: "assistant",
          content: response.response,
          displayContent: "",   // starts empty — typewriter fills it in
          isTyping: true,
          timestamp: new Date().toISOString(),
          sources: response.sources,
          tools_used: response.tools_used,
        };

        // Swap loading bubble → real message instantly
        setMessages((prev) =>
          prev.filter((m) => m.id !== "loading").concat(assistantMessage)
        );

        // Kick off typewriter immediately (tiny settle delay)
        setTimeout(() => animateTyping(newId, response.response), 20);
      } catch (error) {
        const errText =
          "⚠️ **Connection Error**\n\nI couldn't connect to the backend. Please make sure the server is running at `http://localhost:8000`.";
        const errorMessage: Message = {
          id: uuidv4(),
          role: "assistant",
          content: errText,
          displayContent: errText,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) =>
          prev.filter((m) => m.id !== "loading").concat(errorMessage)
        );
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, animateTyping]
  );

  const uploadImage = useCallback(
    async (file: File) => {
      if (!file || isLoading) return;

      const loadingMessage: Message = {
        id: "loading",
        role: "assistant",
        content: "",
        displayContent: "",
        timestamp: new Date().toISOString(),
        isLoading: true,
      };

      setMessages((prev) => [...prev, loadingMessage]);
      setIsLoading(true);

      try {
        const response = await chatApi.uploadImage(file, conversationId.current);

        const newId = uuidv4();
        const assistantMessage: Message = {
          id: newId,
          role: "assistant",
          content: response.response,
          displayContent: "",
          isTyping: true,
          timestamp: new Date().toISOString(),
          sources: response.sources,
          tools_used: response.tools_used,
        };

        setMessages((prev) =>
          prev.filter((m) => m.id !== "loading").concat(assistantMessage)
        );

        setTimeout(() => animateTyping(newId, response.response), 20);
      } catch (error) {
        const errText =
          "⚠️ **Image Analysis Failed**\n\nThe screenshot could not be processed. Please try a clearer image or a PNG/JPG/WebP file.";
        const errorMessage: Message = {
          id: uuidv4(),
          role: "assistant",
          content: errText,
          displayContent: errText,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) =>
          prev.filter((m) => m.id !== "loading").concat(errorMessage)
        );
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, animateTyping]
  );

  const clearConversation = useCallback(() => {
    if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
    const newId = uuidv4();
    conversationId.current = newId;
    localStorage.setItem(CONVERSATION_ID_KEY, newId);
    setMessages([]);
  }, []);

  return { messages, isLoading, sendMessage, uploadImage, clearConversation };
}
