"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, Calendar } from "lucide-react";

interface Event {
  title: string;
  date: string;
  club_name?: string;
  location?: string;
  description: string;
  source_url: string;
}

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchEvents() {
      try {
        const res = await fetch("http://localhost:8000/api/events");
        if (!res.ok) throw new Error("Failed to fetch events");
        const data = await res.json();
        setEvents(data);
      } catch (error) {
        console.error(error);
        // Fallback for MVP demonstration if backend is down
        setEvents([
          {
            title: "Tech Hackathon 2026",
            date: "June 15, 2026",
            club_name: "Microsoft Student Chapter",
            location: "Academic Block 1",
            description: "A 48-hour hackathon focused on building AI solutions.",
            source_url: "https://vitap.ac.in/events/"
          },
          {
            title: "Cyber Security Workshop",
            date: "June 20, 2026",
            club_name: "CSI",
            location: "Virtual",
            description: "Learn the basics of network security and ethical hacking.",
            source_url: "https://vitap.ac.in/events/"
          }
        ]);
      } finally {
        setIsLoading(false);
      }
    }
    fetchEvents();
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center p-8 md:p-24 bg-slate-50 dark:bg-slate-950">
      <div className="w-full max-w-4xl mb-6">
        <Link href="/" className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition-colors">
          <ArrowLeft size={16} className="mr-1" /> Back to Home
        </Link>
      </div>

      <div className="w-full text-center mb-12">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">Campus Events</h1>
        <p className="text-slate-500 mt-2">Discover what is happening at VIT-AP.</p>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-4xl">
          {events.map((event, idx) => (
            <div key={idx} className="bg-white dark:bg-slate-900 p-6 rounded-xl border dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 shrink-0 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex flex-col items-center justify-center">
                  <Calendar size={20} className="mb-1" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-1">{event.title}</h3>
                  <div className="text-xs font-medium text-blue-600 dark:text-blue-400 mb-2">
                    {event.date} • {event.location || "TBA"}
                  </div>
                  <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                    {event.description}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-md font-medium text-slate-600 dark:text-slate-400">
                      {event.club_name || "Campus Event"}
                    </span>
                    <a 
                      href={event.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:underline"
                    >
                      Details
                    </a>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
