import { useState, useEffect, useRef, useCallback } from "react";

// Add TypeScript declarations for Web Speech API
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export function useSpeech() {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);

  const recognitionRef = useRef<any>(null);
  const silenceTimerRef = useRef<any>(null);
  const latestTranscriptRef = useRef<string>("");

  // Initialize Speech Synthesis Voices
  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      const loadVoices = () => {
        const availableVoices = window.speechSynthesis.getVoices();
        setVoices(availableVoices);
      };
      loadVoices();
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, []);

  // Initialize Speech Recognition
  useEffect(() => {
    if (typeof window === "undefined") return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition error:", event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    } catch (err) {
      console.warn("Could not initialize SpeechRecognition:", err);
      setSpeechSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {}
      }
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // Clean Markdown and formatting for natural speech synthesis
  const cleanTextForSpeech = (text: string): string => {
    return text
      .replace(/#+\s+/g, "") // Remove headers
      .replace(/\*\*([^*]+)\*\*/g, "$1") // Remove bold
      .replace(/\*([^*]+)\*/g, "$1") // Remove italics
      .replace(/`([^`]+)`/g, "$1") // Remove inline code
      .replace(/```[\s\S]*?```/g, "") // Remove code blocks
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // Remove links, keep text
      .replace(/\|[^\n]+\|/g, "") // Remove table rows
      .replace(/[-*+]\s+/g, "") // Remove bullet points
      .replace(/[\u{1F300}-\u{1FAFF}]/gu, "") // Remove emoji icons
      .replace(/\s+/g, " ")
      .trim();
  };

  // Text to Speech
  const speak = useCallback((text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;

    window.speechSynthesis.cancel(); // Stop any current speech
    const cleanText = cleanTextForSpeech(text);
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    // Pick best English voice if available (e.g. Google US English, Microsoft Jenny/Natural)
    if (voices.length > 0) {
      const preferredVoice = voices.find(
        (v) => (v.name.includes("Natural") || v.name.includes("Google") || v.name.includes("Samantha") || v.name.includes("Jenny")) && v.lang.startsWith("en")
      ) || voices.find((v) => v.lang.startsWith("en"));
      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  }, [voices]);

  // Stop Speech
  const stopSpeaking = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  const stopListening = useCallback(() => {
    clearSilenceTimer();
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
    }
    setIsListening(false);
  }, [clearSilenceTimer]);

  // Toggle Listening with 2-second silence auto-submit detection
  const toggleListening = useCallback((
    onResult: (text: string) => void,
    onSilenceAutoSubmit?: (finalText: string) => void,
    silenceMs: number = 2000
  ) => {
    if (!recognitionRef.current) return;

    if (isListening) {
      stopListening();
    } else {
      // Stop AI speech if user starts speaking
      stopSpeaking();
      clearSilenceTimer();
      latestTranscriptRef.current = "";

      recognitionRef.current.onresult = (event: any) => {
        let fullTranscript = "";
        for (let i = 0; i < event.results.length; i++) {
          fullTranscript += event.results[i][0].transcript + " ";
        }
        const cleanSpoken = fullTranscript.trim();
        if (cleanSpoken) {
          latestTranscriptRef.current = cleanSpoken;
          onResult(cleanSpoken);

          // Reset 2-second silence timer
          if (onSilenceAutoSubmit) {
            clearSilenceTimer();
            silenceTimerRef.current = setTimeout(() => {
              const textToSubmit = latestTranscriptRef.current.trim();
              if (textToSubmit) {
                stopListening();
                onSilenceAutoSubmit(textToSubmit);
              }
            }, silenceMs);
          }
        }
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };

      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.warn("Speech recognition start failed:", err);
      }
    }
  }, [isListening, stopSpeaking, clearSilenceTimer, stopListening]);

  return {
    isListening,
    isSpeaking,
    autoSpeak,
    setAutoSpeak,
    speechSupported,
    speak,
    stopSpeaking,
    stopListening,
    toggleListening,
  };
}
