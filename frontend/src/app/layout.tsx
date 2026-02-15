import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import "@fontsource-variable/plus-jakarta-sans";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import PageTransition from "@/components/PageTransition";
import AmbientBackground from "@/components/AmbientBackground";
import ErrorBoundary from "@/components/ErrorBoundary";
import { Toaster } from "sonner";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "OMNIBUS - The Whole Law, Harmonized",
  description: "Sistem RAG (Retrieval-Augmented Generation) tercanggih untuk harmonisasi dan analisis peraturan perundang-undangan Indonesia.",
  keywords: ["hukum indonesia", "peraturan", "undang-undang", "legal", "omnibus", "ai legal", "regulatory harmonization"],
  authors: [{ name: "OMNIBUS Team" }],
  openGraph: {
    title: "OMNIBUS - Legal Intelligence",
    description: "Sistem Tanya Jawab Hukum Indonesia dengan AI",
    type: "website",
    locale: "id_ID",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" suppressHydrationWarning>
      <body className={`${geistMono.variable} antialiased`}>
        <AmbientBackground />
        <Navbar />
        <main className="pt-16 min-h-screen">
          <PageTransition>
            <ErrorBoundary>
              {children}
            </ErrorBoundary>
          </PageTransition>
        </main>
        <Footer />
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: 'rgba(17, 17, 24, 0.95)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              boxShadow: '0 10px 15px -3px rgba(0,0,0,0.4), 0 4px 6px -4px rgba(0,0,0,0.3)',
              color: '#F1F5F9',
            },
          }}
          richColors
          closeButton
        />
      </body>
    </html>
  );
}
