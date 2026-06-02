"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface Club {
  name: string;
  description: string;
  category?: string;
  website?: string;
  source_url: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  Technical: "#3b82f6",
  Cultural: "#8b5cf6",
  Sports: "#10b981",
  Literary: "#f59e0b",
  Social: "#06b6d4",
  Science: "#6366f1",
  Management: "#ec4899",
  Other: "#6b7280",
};

const CATEGORY_ICONS: Record<string, string> = {
  Technical: "💻",
  Cultural: "🎭",
  Sports: "⚽",
  Literary: "📚",
  Social: "🤝",
  Science: "🔬",
  Management: "📊",
  Other: "🏛️",
};

const API_URL =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

export default function ClubsPage() {
  const [clubs, setClubs] = useState<Club[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState("All");

  useEffect(() => {
    async function fetchClubs() {
      try {
        const res = await fetch(`${API_URL}/api/clubs?t=${Date.now()}`, {
          cache: "no-store",
        });
        if (!res.ok) throw new Error("Failed to fetch clubs");
        const data = await res.json();
        setClubs(data);
      } catch {
        setClubs([
          {
            name: "Microsoft Student Chapter",
            description: "A community of tech enthusiasts exploring Microsoft technologies and building innovative solutions.",
            category: "Technical",
            source_url: "https://vitap.ac.in/clubs-and-chapters/",
          },
          {
            name: "IEEE Student Branch",
            description: "Fostering technological innovation and excellence for the benefit of humanity through IEEE.",
            category: "Technical",
            source_url: "https://vitap.ac.in/clubs-and-chapters/",
          },
          {
            name: "Google Developer Student Club",
            description: "Bridge the gap between theory and practice through Google developer tools and technologies.",
            category: "Technical",
            source_url: "https://vitap.ac.in/clubs-and-chapters/",
          },
          {
            name: "Literary Club",
            description: "Promoting reading, writing, and literary arts among students at VIT-AP University.",
            category: "Literary",
            source_url: "https://vitap.ac.in/clubs-and-chapters/",
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    }
    fetchClubs();
  }, []);

  const categories = ["All", ...Array.from(new Set(clubs.map((c) => c.category || "Other"))).sort()];
  const filtered = filter === "All" ? clubs : clubs.filter((c) => (c.category || "Other") === filter);

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#0a0a0a",
        color: "#e0e0e0",
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        padding: "24px 16px 60px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      {/* Top nav */}
      <div style={{ width: "100%", maxWidth: 960, marginBottom: 24 }}>
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
      <div style={{ textAlign: "center", marginBottom: 36, width: "100%", maxWidth: 960 }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 52,
            height: 52,
            borderRadius: 14,
            background: "#8b5cf622",
            border: "1px solid #8b5cf633",
            marginBottom: 14,
            fontSize: 22,
          }}
        >
          🏛️
        </div>
        <h1
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: "#fff",
            margin: "0 0 8px",
            letterSpacing: "-0.5px",
          }}
        >
          Clubs &amp; Chapters
        </h1>
        <p style={{ fontSize: 14, color: "#555", margin: 0 }}>
          Explore vibrant student life at VIT-AP University
        </p>
      </div>

      {/* Category filter */}
      {!isLoading && clubs.length > 0 && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 6,
            marginBottom: 24,
            width: "100%",
            maxWidth: 960,
          }}
        >
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              style={{
                fontSize: 11,
                fontWeight: 500,
                padding: "4px 12px",
                borderRadius: 20,
                border: filter === cat ? "1px solid #3a3a3a" : "1px solid #222",
                background: filter === cat ? "#1e1e1e" : "transparent",
                color: filter === cat ? "#ccc" : "#555",
                cursor: "pointer",
                transition: "all 0.15s",
                fontFamily: "inherit",
              }}
            >
              {cat !== "All" && CATEGORY_ICONS[cat] ? `${CATEGORY_ICONS[cat]} ` : ""}{cat}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: 12,
            width: "100%",
            maxWidth: 960,
          }}
        >
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              style={{
                height: 150,
                borderRadius: 14,
                background: "linear-gradient(90deg, #141414 25%, #1a1a1a 50%, #141414 75%)",
                backgroundSize: "200% 100%",
                animation: "shimmer 1.5s infinite",
              }}
            />
          ))}
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: 12,
            width: "100%",
            maxWidth: 960,
          }}
        >
          {filtered.map((club, idx) => {
            const cat = club.category || "Other";
            const color = CATEGORY_COLORS[cat] || "#6b7280";
            const icon = CATEGORY_ICONS[cat] || "🏛️";
            return (
              <a
                key={idx}
                href={club.source_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  background: "#0f0f0f",
                  border: "1px solid #1a1a1a",
                  borderRadius: 14,
                  padding: "18px",
                  textDecoration: "none",
                  color: "inherit",
                  transition: "all 0.15s",
                }}
                onMouseOver={(e) => {
                  const el = e.currentTarget as HTMLAnchorElement;
                  el.style.background = "#141414";
                  el.style.borderColor = "#2a2a2a";
                  el.style.transform = "translateY(-2px)";
                  el.style.boxShadow = "0 8px 24px rgba(0,0,0,0.3)";
                }}
                onMouseOut={(e) => {
                  const el = e.currentTarget as HTMLAnchorElement;
                  el.style.background = "#0f0f0f";
                  el.style.borderColor = "#1a1a1a";
                  el.style.transform = "translateY(0)";
                  el.style.boxShadow = "none";
                }}
              >
                {/* Icon + badge row */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                  <div
                    style={{
                      width: 42,
                      height: 42,
                      borderRadius: 12,
                      background: color + "22",
                      border: `1px solid ${color}33`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 19,
                    }}
                  >
                    {icon}
                  </div>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      padding: "2px 8px",
                      borderRadius: 20,
                      background: color + "22",
                      border: `1px solid ${color}33`,
                      color: color,
                      letterSpacing: "0.2px",
                    }}
                  >
                    {cat}
                  </span>
                </div>

                {/* Club name */}
                <h3 style={{ fontSize: 13, fontWeight: 600, color: "#e0e0e0", margin: "0 0 6px", lineHeight: 1.4 }}>
                  {club.name}
                </h3>

                {/* Description */}
                <p style={{ fontSize: 11, color: "#555", margin: "0 0 14px", lineHeight: 1.6, flex: 1 }}>
                  {club.description.length > 110 ? club.description.slice(0, 110) + "…" : club.description}
                </p>

                {/* Learn more */}
                <span style={{ fontSize: 11, color: color, letterSpacing: "0.2px" }}>
                  Learn More →
                </span>
              </a>
            );
          })}
        </div>
      )}
      {/* Developer Credit */}
      <div style={{ marginTop: 48, display: "flex", flexDirection: "column", alignItems: "center", gap: 4, opacity: 0.6, paddingBottom: 24 }}>
        <span style={{ fontSize: 8, color: "#3f3f46", textTransform: "uppercase", letterSpacing: "1px", fontWeight: 500 }}>Developed by</span>
        <span style={{ fontSize: 10, fontWeight: 600, color: "#71717a", background: "linear-gradient(135deg, #71717a 0%, #a1a1aa 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", letterSpacing: "0.2px" }}>Hemasai Vattikuti</span>
      </div>
    </main>
  );
}
