import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Omnibus Legal Compass - Sistem Tanya Jawab Hukum Indonesia",
  description: "Sistem RAG (Retrieval-Augmented Generation) untuk menjawab pertanyaan tentang peraturan perundang-undangan Indonesia dengan kutipan sumber yang akurat.",
  keywords: ["hukum indonesia", "peraturan", "undang-undang", "legal", "omnibus", "tanya jawab hukum"],
  authors: [{ name: "Omnibus Legal Compass Team" }],
  openGraph: {
    title: "Omnibus Legal Compass",
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
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
