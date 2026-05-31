import type { Metadata } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
// @ts-ignore - CSS module import
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-jakarta",
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "RAG Video Analyst — AI-Powered Video Intelligence",
  description:
    "Compare YouTube & Instagram Reels with AI-driven retrieval-augmented generation. Analyze engagement, extract insights, and chat with your video data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${jakarta.variable}`}>
      <body className="min-h-screen bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}