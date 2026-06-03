import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "vitap-UniOs — VIT-AP Assistant",
  description: "Your intelligent campus assistant for VIT-AP University",
  manifest: "/manifest.json",
  icons: {
    icon: "/logo.png",
    shortcut: "/logo.png",
    apple: "/logo.png",
  },
  openGraph: {
    title: "vitap-UniOs — VIT-AP Assistant",
    description: "Your intelligent campus assistant for VIT-AP University",
    url: "https://vitap-rag.vercel.app/",
    siteName: "vitap-UniOs",
    type: "website",
    images: [
      {
        url: "https://vitap-rag.vercel.app/logo.png",
        width: 512,
        height: 512,
        alt: "vitap-UniOs Logo",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "vitap-UniOs — VIT-AP Assistant",
    description: "Your intelligent campus assistant for VIT-AP University",
    images: ["https://vitap-rag.vercel.app/logo.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body style={{ margin: 0, padding: 0, background: "#0a0a0a", color: "#e8e8e8", fontFamily: "'Google Sans', 'Segoe UI', system-ui, sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
