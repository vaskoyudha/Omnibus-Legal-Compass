import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import "@fontsource-variable/plus-jakarta-sans";
import "./globals.css";
import LayoutShell from "@/components/LayoutShell";

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
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  );
}
