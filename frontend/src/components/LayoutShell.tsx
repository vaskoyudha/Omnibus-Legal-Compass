'use client';

import { usePathname } from 'next/navigation';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import PageTransition from '@/components/PageTransition';
import AmbientBackground from '@/components/AmbientBackground';
import ErrorBoundary from '@/components/ErrorBoundary';
import { Toaster } from 'sonner';

export default function LayoutShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isChatRoute = pathname.startsWith('/chat');

    if (isChatRoute) {
        // Chat route gets a clean, full-screen layout — no Navbar, Footer, or padding
        return (
            <>
                <ErrorBoundary>
                    {children}
                </ErrorBoundary>
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
            </>
        );
    }

    // Default layout with Navbar, Footer, etc.
    return (
        <>
            <AmbientBackground />
            <Navbar />
            <main className="pt-16 sm:pt-20 min-h-screen">
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
        </>
    );
}
