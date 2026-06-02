import ChatInterface from "@/components/ChatInterface";
import Link from "next/link";

export default function ChatPage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#0a0a0a",
        color: "#e0e0e0",
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "24px 16px 40px",
      }}
    >
      {/* Back link */}
      <div style={{ width: "100%", maxWidth: 720, marginBottom: 20 }}>
        <Link
          href="/"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 13,
            color: "#555",
            textDecoration: "none",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M9 11L5 7l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Back to Home
        </Link>
      </div>

      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/logo.png"
          alt="vitap-UniOs"
          width={52}
          height={52}
          style={{ borderRadius: 12, marginBottom: 14, boxShadow: "0 6px 24px rgba(0,0,0,0.5)" }}
        />
        <h1
          style={{
            fontSize: 26,
            fontWeight: 700,
            color: "#fff",
            margin: "0 0 6px",
            letterSpacing: "-0.5px",
          }}
        >
          Ask <span style={{ background: "linear-gradient(135deg,#fff 0%,#a5b4fc 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>vitap-UniOs</span>
        </h1>
        <p style={{ fontSize: 13, color: "#555", margin: 0 }}>
          Instant answers about VIT-AP University
        </p>
      </div>

      <ChatInterface />
    </main>
  );
}
