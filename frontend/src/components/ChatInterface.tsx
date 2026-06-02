"use client";

import { useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
  error?: boolean;
}

const API_URL =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hi! I'm vitap-UniOs — your intelligent VIT-AP assistant. Ask me about fees, clubs, events, placements, or anything about campus life.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = input.trim();
    if (!query || isLoading) return;

    const userMsg: Message = { role: "user", content: query };
    const assistantPlaceholder: Message = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, userMsg, assistantPlaceholder]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (!res.ok) throw new Error(await res.text() || "Server error");
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let accumulated = "";

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunkStr = decoder.decode(value, { stream: true });
          for (const line of chunkStr.split("\n")) {
            const trimmed = line.trim();
            if (trimmed.startsWith("data: ")) {
              try {
                const data = JSON.parse(trimmed.slice(6));
                if (data.text) {
                  accumulated += data.text;
                  setMessages((prev) => {
                    const next = [...prev];
                    const last = next[next.length - 1];
                    if (last?.role === "assistant") last.content = accumulated;
                    return next;
                  });
                }
                if (data.citations) {
                  const cites = data.citations;
                  setMessages((prev) => {
                    const next = [...prev];
                    const last = next[next.length - 1];
                    if (last?.role === "assistant") last.citations = cites;
                    return next;
                  });
                }
              } catch { /* ignore parse errors */ }
            }
          }
        }
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant" && last.content === "") {
          next[next.length - 1] = {
            role: "assistant",
            content: `⚠️ Could not reach the backend.\n\nError: ${msg}`,
            error: true,
          };
        }
        return next;
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "70vh",
        width: "100%",
        maxWidth: 720,
        background: "#0f0f0f",
        border: "1px solid #1e1e1e",
        borderRadius: 16,
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid #1a1a1a",
          display: "flex",
          alignItems: "center",
          gap: 10,
          background: "#111",
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo.png" alt="vitap-UniOs" width={22} height={22} style={{ borderRadius: 6 }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: "#ccc" }}>vitap-UniOs Chat</span>
        <span
          style={{
            marginLeft: "auto",
            fontSize: 10,
            color: "#10b981",
            background: "#10b98122",
            border: "1px solid #10b98133",
            padding: "2px 8px",
            borderRadius: 20,
          }}
        >
          ● Live
        </span>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "20px 16px",
          display: "flex",
          flexDirection: "column",
          gap: 16,
          scrollbarWidth: "thin",
          scrollbarColor: "#1e1e1e transparent",
        }}
      >
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              display: "flex",
              gap: 10,
              flexDirection: msg.role === "user" ? "row-reverse" : "row",
              alignItems: "flex-start",
            }}
          >
            {/* Avatar */}
            <div
              style={{
                width: 26,
                height: 26,
                borderRadius: "50%",
                background: "#161616",
                border: "1px solid #242424",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                overflow: "hidden",
              }}
            >
              {msg.role === "assistant" ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src="/logo.png" alt="bot" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              ) : (
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <circle cx="7" cy="5" r="2.5" stroke="#888" strokeWidth="1.2" />
                  <path d="M2 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="#888" strokeWidth="1.2" strokeLinecap="round" />
                </svg>
              )}
            </div>

            {/* Bubble */}
            <div
              style={
                msg.role === "user"
                  ? {
                      background: "#181818",
                      border: "1px solid #242424",
                      borderRadius: "16px 16px 4px 16px",
                      padding: "10px 14px",
                      maxWidth: "72%",
                    }
                  : msg.error
                  ? {
                      background: "#150f0f",
                      border: "1px solid #2d1515",
                      borderRadius: 12,
                      padding: "10px 14px",
                      maxWidth: "88%",
                      flex: 1,
                    }
                  : {
                      background: "transparent",
                      maxWidth: "88%",
                      flex: 1,
                    }
              }
            >
              <p
                style={{
                  margin: 0,
                  fontSize: 14,
                  lineHeight: 1.7,
                  color: "#d0d0d0",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {msg.content}
              </p>
              {msg.citations && msg.citations.length > 0 && (
                <div
                  style={{
                    marginTop: 10,
                    paddingTop: 8,
                    borderTop: "1px solid #222",
                    display: "flex",
                    flexDirection: "column",
                    gap: 3,
                  }}
                >
                  <span style={{ fontSize: 10, color: "#444", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                    Sources
                  </span>
                  {msg.citations.map((c, i) => (
                    <a
                      key={i}
                      href={c}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: 11, color: "#555", wordBreak: "break-all", lineHeight: 1.4, textDecoration: "none" }}
                    >
                      [{i + 1}] {c.length > 60 ? c.slice(0, 60) + "…" : c}
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading &&
          messages.length > 0 &&
          messages[messages.length - 1].role === "assistant" &&
          messages[messages.length - 1].content === "" && (
            <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              <div
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: "50%",
                  background: "#161616",
                  border: "1px solid #242424",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  overflow: "hidden",
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/logo.png" alt="bot" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>
              <div style={{ display: "flex", gap: 4, padding: "8px 0" }}>
                {[0, 160, 320].map((delay) => (
                  <span
                    key={delay}
                    style={{
                      display: "inline-block",
                      width: 6,
                      height: 6,
                      borderRadius: "50%",
                      background: "#444",
                      animation: "bounce 1.2s ease-in-out infinite",
                      animationDelay: `${delay}ms`,
                    }}
                  />
                ))}
              </div>
            </div>
          )}
      </div>

      {/* Input */}
      <form
        onSubmit={sendMessage}
        style={{
          padding: "12px 14px 14px",
          borderTop: "1px solid #161616",
          background: "#0a0a0a",
          display: "flex",
          gap: 8,
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about clubs, fees, events, campus life..."
          disabled={isLoading}
          style={{
            flex: 1,
            background: "#111",
            border: "1px solid #222",
            borderRadius: 10,
            padding: "10px 14px",
            fontSize: 14,
            color: "#e0e0e0",
            outline: "none",
            fontFamily: "inherit",
          }}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          style={{
            background: !input.trim() || isLoading ? "#1a1a1a" : "#e0e0e0",
            border: "none",
            borderRadius: 10,
            width: 40,
            height: 40,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: !input.trim() || isLoading ? "not-allowed" : "pointer",
            color: !input.trim() || isLoading ? "#333" : "#0a0a0a",
            flexShrink: 0,
            transition: "all 0.15s",
          }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 13V3M8 3L3.5 7.5M8 3l4.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </form>
    </div>
  );
}
