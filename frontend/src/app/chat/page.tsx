import ChatInterface from "@/components/ChatInterface";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function ChatPage() {
  return (
    <main className="flex min-h-screen flex-col items-center p-8 md:p-24 bg-slate-50 dark:bg-slate-950">
      <div className="w-full max-w-4xl mb-6">
        <Link href="/" className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition-colors">
          <ArrowLeft size={16} className="mr-1" /> Back to Home
        </Link>
      </div>
      
      <div className="w-full text-center mb-8">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">Ask CampusOS</h1>
        <p className="text-slate-500 mt-2">Get instant answers based on VIT-AP public data.</p>
      </div>

      <ChatInterface />
    </main>
  );
}
