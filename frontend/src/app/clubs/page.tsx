"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, Users } from "lucide-react";

interface Club {
  name: string;
  description: string;
  category?: string;
  website?: string;
  source_url: string;
}

export default function ClubsPage() {
  const [clubs, setClubs] = useState<Club[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchClubs() {
      try {
        const res = await fetch("http://localhost:8000/api/clubs");
        if (!res.ok) throw new Error("Failed to fetch clubs");
        const data = await res.json();
        setClubs(data);
      } catch (error) {
        console.error(error);
        // Fallback for MVP demonstration if backend is down
        setClubs([
          {
            name: "Microsoft Student Chapter",
            description: "A community of tech enthusiasts exploring Microsoft technologies.",
            category: "Technical",
            source_url: "https://vitap.ac.in/clubs-and-chapters/"
          },
          {
            name: "IEEE Student Branch",
            description: "Fostering technological innovation and excellence for the benefit of humanity.",
            category: "Technical",
            source_url: "https://vitap.ac.in/clubs-and-chapters/"
          }
        ]);
      } finally {
        setIsLoading(false);
      }
    }
    fetchClubs();
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center p-8 md:p-24 bg-slate-50 dark:bg-slate-950">
      <div className="w-full max-w-4xl mb-6">
        <Link href="/" className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition-colors">
          <ArrowLeft size={16} className="mr-1" /> Back to Home
        </Link>
      </div>

      <div className="w-full text-center mb-12">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">Clubs & Chapters</h1>
        <p className="text-slate-500 mt-2">Explore the vibrant student life at VIT-AP.</p>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full max-w-5xl">
          {clubs.map((club, idx) => (
            <div key={idx} className="bg-white dark:bg-slate-900 p-6 rounded-xl border dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
              <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-4">
                <Users size={20} />
              </div>
              <h3 className="text-lg font-semibold mb-2">{club.name}</h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-4 line-clamp-3">
                {club.description}
              </p>
              <a 
                href={club.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:underline"
              >
                Learn More
              </a>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
