"use client";

import { useState, useRef, useEffect, useCallback } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
  error?: boolean;
}

interface FeedItem {
  title: string;
  description: string;
  category: string;
  source_url: string;
  date_str: string;
  source: string;
  fetched_at: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  Event: "#3b82f6",
  Workshop: "#8b5cf6",
  Hackathon: "#f59e0b",
  Club: "#10b981",
  Internship: "#06b6d4",
  Placement: "#ec4899",
  Research: "#6366f1",
  News: "#64748b",
  Admission: "#f97316",
  Opportunity: "#14b8a6",
  Other: "#6b7280",
};

const CATEGORY_ICONS: Record<string, string> = {
  Event: "🎉",
  Workshop: "🛠️",
  Hackathon: "💻",
  Club: "🏛️",
  Internship: "💼",
  Placement: "🎓",
  Research: "🔬",
  News: "📰",
  Admission: "📋",
  Opportunity: "⚡",
  Other: "📌",
};

const API_URL =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Feed state
  const [feedItems, setFeedItems] = useState<FeedItem[]>([]);
  const [feedLoading, setFeedLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState("All");
  const [feedCategories, setFeedCategories] = useState<string[]>(["All"]);
  const [feedMeta, setFeedMeta] = useState<{ last_updated?: string; total?: number } | null>(null);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [mobileFeedOpen, setMobileFeedOpen] = useState(false);

  // PWA Install Prompt State
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [showInstallBtn, setShowInstallBtn] = useState(false);

  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowInstallBtn(true);
    };
    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);

    // Show Install option on iOS/Android browsers (as a fallback guide)
    if (typeof window !== "undefined" && typeof navigator !== "undefined") {
      const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
      const isAndroid = /Android/.test(navigator.userAgent);
      const isStandalone = window.matchMedia("(display-mode: standalone)").matches;
      if ((isIOS || isAndroid) && !isStandalone) {
        setShowInstallBtn(true);
      }
    }

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === "accepted") {
        setDeferredPrompt(null);
        setShowInstallBtn(false);
      }
    } else {
      alert(
        "To install vitap-UniOs as a Mobile Web App:\n\n" +
        "• iOS (Safari): Tap the Share button (square with arrow up) at the bottom, then scroll down and tap 'Add to Home Screen'.\n" +
        "• Android (Chrome): Tap the three dots menu at the top right, then tap 'Install app' or 'Add to Home screen'."
      );
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
    }
  }, [input]);

  // Load feed
  const loadFeed = useCallback(async (category = "All") => {
    setFeedLoading(true);
    try {
      const cat = category === "All" ? "all" : category;
      const res = await fetch(`${API_URL}/api/feed?category=${cat}&limit=40&t=${Date.now()}`, {
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        setFeedItems(data.items || []);
        setFeedMeta(data.meta || null);

        // Extract unique categories from items
        const cats = Array.from(
          new Set((data.items || []).map((i: FeedItem) => i.category))
        ).sort() as string[];
        setFeedCategories(["All", ...cats]);
      }
    } catch (e) {
      console.error("Feed load failed:", e);
    } finally {
      setFeedLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFeed();
    // Refresh feed every 30 mins
    const interval = setInterval(() => loadFeed(activeCategory), 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, [loadFeed]);

  const handleCategoryChange = (cat: string) => {
    setActiveCategory(cat);
    loadFeed(cat);
  };

  const sendMessage = async (text?: string) => {
    const query = (text ?? input).trim();
    if (!query || isLoading) return;

    setStarted(true);
    const userMsg: Message = { role: "user", content: query };
    const assistantMsg: Message = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, history }),
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
              } catch { }
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
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatTime = (iso: string) => {
    try {
      const d = new Date(iso);
      const diff = Math.floor((Date.now() - d.getTime()) / 60000);
      if (diff < 1) return "just now";
      if (diff < 60) return `${diff}m ago`;
      if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
      return `${Math.floor(diff / 1440)}d ago`;
    } catch { return ""; }
  };

  return (
    <div style={s.root}>
      {/* ── Sidebar ── */}
      <aside className={`desktop-sidebar ${mobileSidebarOpen ? "open" : ""}`} style={s.sidebar}>
        <div style={s.logo}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="vitap-UniOs Logo" width="28" height="28" style={{ borderRadius: 6, objectFit: "cover" }} />
          <span style={s.logoText}>vitap-UniOs</span>
          <button
            className="mobile-close-btn"
            onClick={() => setMobileSidebarOpen(false)}
            style={s.drawerCloseBtn}
            aria-label="Close Sidebar"
          >
            ✕
          </button>
        </div>

        <button
          style={s.newChatBtn}
          onClick={() => { setMessages([]); setStarted(false); setInput(""); }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          New Chat
        </button>

        <div style={s.sidebarDivider} />

        <div style={s.sidebarSection}>
          <div style={s.sidebarLabel}>Campus</div>
          <div style={s.sidebarInfo}>
            <span style={s.sidebarDot} />
            VIT-AP University
          </div>
          {feedMeta && (
            <div style={s.sidebarInfo}>
              <span style={{ ...s.sidebarDot, background: "#10b981" }} />
              {feedMeta.total ?? 0} feed items
            </div>
          )}
        </div>

        <div style={{ marginTop: "auto" }}>
          {showInstallBtn && (
            <button
              onClick={handleInstallClick}
              className="install-btn"
              style={s.installBtn}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
              </svg>
              Install App
            </button>
          )}
          <div style={s.sidebarBadge}>Powered by Groq + Qdrant</div>
          <div style={{ fontSize: 9, color: "#444", textAlign: "center", paddingTop: 4, letterSpacing: "0.2px" }}>
            Developed by Hemasai Vattikuti
          </div>
        </div>
      </aside>

      {/* ── Main Chat Area ── */}
      <main style={s.main}>
        {/* Mobile Header */}
        <header className="mobile-header" style={s.mobileHeader}>
          <button
            onClick={() => setMobileSidebarOpen(true)}
            style={s.mobileHeaderBtn}
            aria-label="Open Menu"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
          
          <div style={s.mobileHeaderTitle}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="vitap-UniOs Logo" width="22" height="22" style={{ borderRadius: 5 }} />
            <span>vitap-UniOs</span>
          </div>
          
          <button
            onClick={() => setMobileFeedOpen(true)}
            style={s.mobileHeaderBtn}
            aria-label="Open Feed"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M4 6h12M4 10h12M4 14h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </header>

        {mobileSidebarOpen && (
          <div
            className="overlay"
            onClick={() => setMobileSidebarOpen(false)}
            style={s.backdrop}
          />
        )}
        {mobileFeedOpen && (
          <div
            className="overlay"
            onClick={() => setMobileFeedOpen(false)}
            style={s.backdrop}
          />
        )}

        {!started ? (
          <div style={s.welcome}>
            <div style={s.welcomeGlow} />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="vitap-UniOs Logo" width="80" height="80" style={{ borderRadius: 16, marginBottom: 12, boxShadow: "0 8px 30px rgba(0,0,0,0.5)" }} />
            <h1 style={s.welcomeTitle}>
              Hello, I&apos;m <span style={s.accent}>vitap-UniOs</span>
            </h1>
            <p style={s.welcomeSub}>Ask me anything about VIT-AP University</p>
            <div style={s.quickChips}>
              {["Fee structure", "Clubs at VIT-AP", "Who is dean of SCOPE", "Placement stats"].map((q) => (
                <button key={q} className="chip" style={s.chip} onClick={() => sendMessage(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div style={s.chatArea}>
            {messages.map((msg, idx) => (
              <div key={idx} style={msg.role === "user" ? s.userRow : s.assistantRow}>
                {msg.role === "assistant" && (
                  <div style={s.avatar}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src="/logo.png" alt="vitap-UniOs" style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }} />
                  </div>
                )}
                <div
                  style={
                    msg.role === "user"
                      ? s.userBubble
                      : msg.error
                        ? s.errorBubble
                        : s.assistantBubble
                  }
                >
                  <p style={s.msgText}>{msg.content}</p>
                  {msg.citations && msg.citations.length > 0 && (
                    <div style={s.citations}>
                      <span style={s.citationsLabel}>Sources</span>
                      {msg.citations.map((c, i) => (
                        <a key={i} href={c} target="_blank" rel="noopener noreferrer" style={s.citationLink}>
                          [{i + 1}] {c.length > 55 ? c.slice(0, 55) + "…" : c}
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
                <div style={s.assistantRow}>
                  <div style={s.avatar}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src="/logo.png" alt="vitap-UniOs" style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }} />
                  </div>
                  <div style={s.assistantBubble}>
                    <div style={s.dotsWrapper}>
                      <span style={{ ...s.dot, animationDelay: "0ms" }} />
                      <span style={{ ...s.dot, animationDelay: "160ms" }} />
                      <span style={{ ...s.dot, animationDelay: "320ms" }} />
                    </div>
                  </div>
                </div>
              )}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Input bar */}
        <div style={s.inputWrapper}>
          <div style={s.inputBox}>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask anything about VIT-AP..."
              rows={1}
              style={s.textarea}
              disabled={isLoading}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isLoading}
              style={
                !input.trim() || isLoading
                  ? { ...s.sendBtn, ...s.sendBtnDisabled }
                  : s.sendBtn
              }
              aria-label="Send message"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M8 13V3M8 3L3.5 7.5M8 3l4.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
          <p style={s.disclaimer}>vitap-UniOs may make mistakes. Verify on the official VIT-AP portal.</p>
        </div>
      </main>

      {/* ── Feed Panel (Right) ── */}
      <aside className={`desktop-feed ${mobileFeedOpen ? "open" : ""}`} style={s.feedPanel}>
        {/* Feed header */}
        <div style={s.feedHeader}>
          <div style={s.feedHeaderTop}>
            <span style={s.feedTitle}>Campus Feed</span>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <button
                style={s.refreshBtn}
                onClick={() => loadFeed(activeCategory)}
                title="Refresh feed"
              >
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <path d="M11 6.5A4.5 4.5 0 1 1 6.5 2a4.5 4.5 0 0 1 3.18 1.32M9.68 1v2.32H12" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              <button
                className="mobile-close-btn"
                onClick={() => setMobileFeedOpen(false)}
                style={s.drawerCloseBtn}
                aria-label="Close Feed"
              >
                ✕
              </button>
            </div>
          </div>
          {feedMeta?.last_updated && (
            <div style={s.feedLastUpdated}>
              Updated {formatTime(feedMeta.last_updated)}
            </div>
          )}
        </div>

        {/* Category filter pills */}
        <div style={s.feedCats}>
          {feedCategories.slice(0, 6).map((cat) => (
            <button
              key={cat}
              className="cat-pill"
              style={{
                ...s.catPill,
                ...(activeCategory === cat ? s.catPillActive : {}),
              }}
              onClick={() => handleCategoryChange(cat)}
            >
              {cat !== "All" && CATEGORY_ICONS[cat] ? CATEGORY_ICONS[cat] + " " : ""}
              {cat}
            </button>
          ))}
        </div>

        {/* Feed items */}
        <div className="feed-list" style={s.feedList}>
          {feedLoading ? (
            <div style={s.feedLoading}>
              {[1, 2, 3, 4].map((i) => (
                <div key={i} style={s.feedSkeleton} />
              ))}
            </div>
          ) : feedItems.length === 0 ? (
            <div style={s.feedEmpty}>
              <div style={{ fontSize: 28 }}>📭</div>
              <div>No items found</div>
            </div>
          ) : (
            feedItems.map((item, idx) => (
              <a
                key={idx}
                href={item.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="feed-card-hover"
                style={s.feedCard}
              >
                <div style={s.feedCardTop}>
                  <span
                    style={{
                      ...s.feedBadge,
                      background:
                        (CATEGORY_COLORS[item.category] || "#6b7280") + "22",
                      color: CATEGORY_COLORS[item.category] || "#6b7280",
                      borderColor:
                        (CATEGORY_COLORS[item.category] || "#6b7280") + "44",
                    }}
                  >
                    {CATEGORY_ICONS[item.category] || "📌"} {item.category}
                  </span>
                  {item.fetched_at && (
                    <span style={s.feedTime}>{formatTime(item.fetched_at)}</span>
                  )}
                </div>
                <div style={s.feedCardTitle}>{item.title}</div>
                {item.description && (
                  <div style={s.feedCardDesc}>
                    {item.description.slice(0, 100)}
                    {item.description.length > 100 ? "…" : ""}
                  </div>
                )}
              </a>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}

/* ─── Styles ─────────────────────────────────────────────── */
const s: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    height: "100vh",
    width: "100vw",
    background: "#0a0a0a",
    overflow: "hidden",
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  },

  /* Sidebar */
  sidebar: {
    width: 220,
    flexShrink: 0,
    background: "#0f0f0f",
    borderRight: "1px solid #1a1a1a",
    display: "flex",
    flexDirection: "column",
    padding: "20px 14px",
    gap: 8,
  },
  logo: {
    display: "flex",
    alignItems: "center",
    gap: 9,
    marginBottom: 16,
    padding: "0 2px",
  },
  logoText: {
    fontSize: 15,
    fontWeight: 600,
    color: "#ffffff",
    letterSpacing: "-0.3px",
  },
  newChatBtn: {
    display: "flex",
    alignItems: "center",
    gap: 7,
    background: "transparent",
    border: "1px solid #222",
    borderRadius: 9,
    color: "#aaa",
    fontSize: 13,
    fontWeight: 500,
    padding: "8px 12px",
    cursor: "pointer",
    transition: "all 0.15s",
    width: "100%",
  },
  sidebarDivider: {
    height: 1,
    background: "#1a1a1a",
    margin: "8px 0",
  },
  sidebarSection: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  sidebarLabel: {
    fontSize: 10,
    color: "#444",
    letterSpacing: "0.8px",
    textTransform: "uppercase",
    marginBottom: 2,
    padding: "0 2px",
  },
  sidebarInfo: {
    display: "flex",
    alignItems: "center",
    gap: 7,
    fontSize: 12,
    color: "#666",
    padding: "0 2px",
  },
  sidebarDot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: "#3b82f6",
    flexShrink: 0,
  },
  sidebarBadge: {
    fontSize: 10,
    color: "#333",
    textAlign: "center" as const,
    padding: "8px 4px",
    borderTop: "1px solid #1a1a1a",
  },
  installBtn: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    background: "#161616",
    border: "1px solid #222",
    borderRadius: 9,
    color: "#aaa",
    fontSize: 12,
    fontWeight: 500,
    padding: "8px 12px",
    cursor: "pointer",
    transition: "all 0.15s",
    width: "100%",
    marginBottom: 10,
  },

  /* Main */
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    overflow: "hidden",
    position: "relative",
    borderRight: "1px solid #1a1a1a",
  },

  /* Welcome */
  welcome: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "0 32px",
    gap: 14,
    position: "relative",
  },
  welcomeGlow: {
    position: "absolute",
    width: 300,
    height: 300,
    borderRadius: "50%",
    background: "radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)",
    animation: "glow-pulse 4s ease-in-out infinite",
    pointerEvents: "none",
  },
  welcomeTitle: {
    fontSize: 36,
    fontWeight: 400,
    color: "#e0e0e0",
    margin: 0,
    textAlign: "center",
    letterSpacing: "-0.8px",
    position: "relative",
  },
  accent: {
    color: "#ffffff",
    fontWeight: 700,
    background: "linear-gradient(135deg, #fff 0%, #a5b4fc 100%)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
  },
  welcomeSub: {
    fontSize: 15,
    color: "#555",
    margin: 0,
    textAlign: "center",
    position: "relative",
  },
  quickChips: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
    justifyContent: "center",
    marginTop: 8,
    maxWidth: 520,
    position: "relative",
  },
  chip: {
    background: "#111",
    border: "1px solid #222",
    borderRadius: 20,
    color: "#999",
    fontSize: 12,
    padding: "7px 14px",
    cursor: "pointer",
    transition: "all 0.15s",
  },

  /* Chat */
  chatArea: {
    flex: 1,
    overflowY: "auto",
    padding: "28px 20px 16px",
    display: "flex",
    flexDirection: "column",
    gap: 20,
    maxWidth: 680,
    width: "100%",
    margin: "0 auto",
    scrollbarWidth: "thin",
    scrollbarColor: "#1e1e1e transparent",
  },
  userRow: { display: "flex", justifyContent: "flex-end" },
  assistantRow: { display: "flex", gap: 10, alignItems: "flex-start" },
  avatar: {
    width: 26,
    height: 26,
    borderRadius: "50%",
    background: "#161616",
    border: "1px solid #242424",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
    marginTop: 2,
  },
  userBubble: {
    background: "#181818",
    border: "1px solid #242424",
    borderRadius: "16px 16px 4px 16px",
    padding: "10px 14px",
    maxWidth: "72%",
  },
  assistantBubble: {
    background: "transparent",
    maxWidth: "88%",
    flex: 1,
  },
  errorBubble: {
    background: "#150f0f",
    border: "1px solid #2d1515",
    borderRadius: 12,
    padding: "10px 14px",
    maxWidth: "88%",
    flex: 1,
  },
  msgText: {
    margin: 0,
    fontSize: 14,
    lineHeight: 1.7,
    color: "#d0d0d0",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  citations: {
    marginTop: 10,
    paddingTop: 8,
    borderTop: "1px solid #222",
    display: "flex",
    flexDirection: "column",
    gap: 3,
  },
  citationsLabel: {
    fontSize: 10,
    color: "#444",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    marginBottom: 3,
  },
  citationLink: {
    fontSize: 11,
    color: "#555",
    wordBreak: "break-all",
    lineHeight: 1.4,
  },
  dotsWrapper: { display: "flex", gap: 4, padding: "6px 0" },
  dot: {
    display: "inline-block",
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: "#444",
    animation: "bounce 1.2s ease-in-out infinite",
  },

  /* Input */
  inputWrapper: {
    padding: "12px 20px 16px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 6,
    borderTop: "1px solid #161616",
    background: "#0a0a0a",
  },
  inputBox: {
    display: "flex",
    alignItems: "flex-end",
    gap: 0,
    background: "#111",
    border: "1px solid #222",
    borderRadius: 14,
    padding: "10px 10px 10px 16px",
    width: "100%",
    maxWidth: 640,
    transition: "border-color 0.15s",
  },
  textarea: {
    flex: 1,
    background: "transparent",
    border: "none",
    outline: "none",
    resize: "none",
    fontSize: 14,
    color: "#e0e0e0",
    lineHeight: 1.6,
    fontFamily: "inherit",
    minHeight: 22,
    maxHeight: 200,
    overflow: "auto",
  },
  sendBtn: {
    background: "#e0e0e0",
    border: "none",
    borderRadius: 9,
    width: 32,
    height: 32,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    color: "#0a0a0a",
    flexShrink: 0,
    transition: "all 0.15s",
    marginLeft: 8,
  },
  sendBtnDisabled: { opacity: 0.25, cursor: "not-allowed" },
  disclaimer: {
    fontSize: 10,
    color: "#2d2d2d",
    margin: 0,
    textAlign: "center",
  },

  /* ── Feed Panel ── */
  feedPanel: {
    width: 300,
    flexShrink: 0,
    background: "#0c0c0c",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  feedHeader: {
    padding: "16px 14px 10px",
    borderBottom: "1px solid #161616",
    flexShrink: 0,
  },
  feedHeaderTop: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  feedTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: "#ccc",
    letterSpacing: "-0.2px",
  },
  refreshBtn: {
    background: "transparent",
    border: "1px solid #1e1e1e",
    borderRadius: 6,
    padding: "4px 6px",
    cursor: "pointer",
    color: "#555",
    display: "flex",
    alignItems: "center",
    transition: "all 0.15s",
  },
  feedLastUpdated: {
    fontSize: 10,
    color: "#333",
    marginTop: 4,
  },
  feedCats: {
    display: "flex",
    flexWrap: "wrap",
    gap: 5,
    padding: "10px 14px 8px",
    borderBottom: "1px solid #161616",
    flexShrink: 0,
  },
  catPill: {
    fontSize: 10,
    fontWeight: 500,
    padding: "3px 8px",
    borderRadius: 20,
    border: "1px solid #222",
    background: "transparent",
    color: "#666",
    cursor: "pointer",
    transition: "all 0.15s",
    whiteSpace: "nowrap",
  },
  catPillActive: {
    background: "#1e1e1e",
    border: "1px solid #3a3a3a",
    color: "#ccc",
  },
  feedList: {
    flex: 1,
    overflowY: "auto",
    padding: "8px 10px",
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  feedLoading: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    padding: "4px 0",
  },
  feedSkeleton: {
    height: 72,
    borderRadius: 10,
    background: "linear-gradient(90deg, #141414 25%, #1a1a1a 50%, #141414 75%)",
    backgroundSize: "200% 100%",
    animation: "shimmer 1.5s infinite",
  },
  feedEmpty: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    color: "#333",
    fontSize: 13,
    paddingTop: 60,
  },
  feedCard: {
    display: "block",
    background: "#111",
    border: "1px solid #1a1a1a",
    borderRadius: 10,
    padding: "10px 12px",
    cursor: "pointer",
    transition: "all 0.15s",
    color: "inherit",
  },
  feedCardTop: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 5,
    gap: 6,
  },
  feedBadge: {
    fontSize: 10,
    fontWeight: 600,
    padding: "2px 7px",
    borderRadius: 20,
    border: "1px solid",
    letterSpacing: "0.2px",
    whiteSpace: "nowrap",
  },
  feedTime: {
    fontSize: 10,
    color: "#333",
    whiteSpace: "nowrap",
    flexShrink: 0,
  },
  feedCardTitle: {
    fontSize: 12,
    fontWeight: 500,
    color: "#bbb",
    lineHeight: 1.5,
    marginBottom: 4,
  },
  feedCardDesc: {
    fontSize: 11,
    color: "#444",
    lineHeight: 1.5,
  },
  mobileHeader: {
    display: "none",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "10px 16px",
    background: "#0f0f0f",
    borderBottom: "1px solid #1a1a1a",
    height: 50,
    width: "100%",
    flexShrink: 0,
  },
  mobileHeaderBtn: {
    background: "transparent",
    border: "none",
    color: "#ccc",
    cursor: "pointer",
    padding: 6,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  mobileHeaderTitle: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 14,
    fontWeight: 600,
    color: "#fff",
  },
  backdrop: {
    display: "none",
    position: "fixed",
    left: 0,
    top: 0,
    width: "100vw",
    height: "100vh",
    background: "rgba(0,0,0,0.6)",
    zIndex: 90,
  },
  drawerCloseBtn: {
    display: "none",
    background: "transparent",
    border: "none",
    color: "#555",
    cursor: "pointer",
    fontSize: 14,
    padding: 4,
    marginLeft: "auto",
  },
};
