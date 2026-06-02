"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface Event {
  title: string;
  date: string;
  club_name?: string;
  location?: string;
  description: string;
  source_url: string;
}

const API_URL =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchEvents() {
      try {
        const res = await fetch(`${API_URL}/api/events?t=${Date.now()}`, {
          cache: "no-store",
        });
        if (!res.ok) throw new Error("Failed to fetch events");
        const data = await res.json();
        setEvents(data);
      } catch {
        setEvents([
          {
            title: "Tech Hackathon 2026",
            date: "June 15, 2026",
            club_name: "Microsoft Student Chapter",
            location: "Academic Block 1",
            description: "A 48-hour hackathon focused on building AI solutions for real-world problems.",
            source_url: "https://vitap.ac.in/events/",
          },
          {
            title: "Cyber Security Workshop",
            date: "June 20, 2026",
            club_name: "CSI",
            location: "Virtual",
            description: "Learn the basics of network security and ethical hacking from industry experts.",
            source_url: "https://vitap.ac.in/events/",
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    }
    fetchEvents();
  }, []);

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
      <div style={{ width: "100%", maxWidth: 900, marginBottom: 24 }}>
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
      <div style={{ textAlign: "center", marginBottom: 40, width: "100%", maxWidth: 900 }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 52,
            height: 52,
            borderRadius: 14,
            background: "#3b82f622",
            border: "1px solid #3b82f633",
            marginBottom: 14,
            fontSize: 22,
          }}
        >
          🎉
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
          Campus Events
        </h1>
        <p style={{ fontSize: 14, color: "#555", margin: 0 }}>
          Discover what&apos;s happening at VIT-AP University
        </p>
      </div>

      {/* Content */}
      {isLoading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, width: "100%", maxWidth: 900 }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              style={{
                height: 120,
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
            gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))",
            gap: 14,
            width: "100%",
            maxWidth: 900,
          }}
        >
          {events.map((event, idx) => (
            <a
              key={idx}
              href={event.source_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "block",
                background: "#0f0f0f",
                border: "1px solid #1a1a1a",
                borderRadius: 14,
                padding: "18px 20px",
                textDecoration: "none",
                color: "inherit",
                transition: "all 0.15s",
              }}
              onMouseOver={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.background = "#141414";
                (e.currentTarget as HTMLAnchorElement).style.borderColor = "#2a2a2a";
                (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(-1px)";
              }}
              onMouseOut={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.background = "#0f0f0f";
                (e.currentTarget as HTMLAnchorElement).style.borderColor = "#1a1a1a";
                (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(0)";
              }}
            >
              <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
                {/* Icon */}
                <div
                  style={{
                    width: 44,
                    height: 44,
                    flexShrink: 0,
                    borderRadius: 12,
                    background: "#3b82f622",
                    border: "1px solid #3b82f633",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 20,
                  }}
                >
                  🗓️
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 10, color: "#3b82f6", fontWeight: 600, marginBottom: 4, letterSpacing: "0.4px", textTransform: "uppercase" }}>
                    {event.date}
                    {event.location ? ` · ${event.location}` : ""}
                  </div>
                  <h3 style={{ fontSize: 14, fontWeight: 600, color: "#e0e0e0", margin: "0 0 6px", lineHeight: 1.4 }}>
                    {event.title}
                  </h3>
                  <p style={{ fontSize: 12, color: "#555", margin: "0 0 10px", lineHeight: 1.6 }}>
                    {event.description}
                  </p>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span
                      style={{
                        fontSize: 10,
                        padding: "2px 8px",
                        borderRadius: 20,
                        background: "#1a1a1a",
                        border: "1px solid #222",
                        color: "#666",
                      }}
                    >
                      {event.club_name || "Campus Event"}
                    </span>
                    <span style={{ fontSize: 11, color: "#3b82f6" }}>
                      View Details →
                    </span>
                  </div>
                </div>
              </div>
            </a>
          ))}
        </div>
      )}
    </main>
  );
}
