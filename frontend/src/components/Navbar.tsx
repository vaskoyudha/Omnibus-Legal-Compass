'use client';

import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import ShinyText from '@/components/reactbits/ShinyText';

const navLinks = [
  { href: '/', label: 'Beranda', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1' },
  { href: '/compliance', label: 'Kepatuhan', icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' },
  { href: '/guidance', label: 'Panduan', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01' },
  { href: '/regulations', label: 'Regulasi', icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253' },
  { href: '/knowledge-graph', label: 'Graf Hukum', icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
  { href: '/chat', label: 'Percakapan', icon: 'M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z' },
  { href: '/dashboard', label: 'Dashboard', icon: 'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z' },
];

const MenuIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="4" x2="20" y1="12" y2="12" />
    <line x1="4" x2="20" y1="6" y2="6" />
    <line x1="4" x2="20" y1="18" y2="18" />
  </svg>
);

const CloseIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

export default function Navbar() {
  const pathname = usePathname();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 40);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = isMobileMenuOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [isMobileMenuOpen]);

  return (
    <>
      {/*
        Strategy: The outer wrapper is always fixed top-0 left-0 right-0.
        We animate its padding to create the floating pill "inset" effect.
        The inner card handles background/border/radius changes.
        This avoids any layout/overflow conflicts.
      */}
      <motion.div
        className="fixed top-0 left-0 right-0 z-50 no-print"
        initial={{ y: -80, opacity: 0 }}
        animate={{
          y: 0,
          opacity: 1,
          paddingTop: isScrolled ? 10 : 0,
          paddingLeft: isScrolled ? 16 : 0,
          paddingRight: isScrolled ? 16 : 0,
        }}
        transition={{
          y: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
          opacity: { duration: 0.5 },
          paddingTop: { duration: 0.4, ease: [0.4, 0, 0.2, 1] },
          paddingLeft: { duration: 0.4, ease: [0.4, 0, 0.2, 1] },
          paddingRight: { duration: 0.4, ease: [0.4, 0, 0.2, 1] },
        }}
      >
        {/* The nav card — background/border/radius transition */}
        <motion.div
          animate={{
            borderRadius: isScrolled ? 16 : 0,
            borderWidth: isScrolled ? 1 : 0,
            boxShadow: isScrolled
              ? '0 8px 32px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3)'
              : '0 0 0 rgba(0,0,0,0)',
          }}
          transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
          style={{
            background: isScrolled ? 'rgba(10, 10, 15, 0.88)' : 'rgba(10, 10, 15, 0.55)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            borderColor: 'rgba(255,255,255,0.08)',
            borderStyle: 'solid',
            borderBottomColor: isScrolled ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.05)',
            borderBottomWidth: isScrolled ? 1 : 1,
          }}
        >
          {/* Nav content */}
          <div className="flex items-center justify-between h-14 px-4 sm:px-5">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2.5 flex-shrink-0">
              <motion.div
                className="w-9 h-9 rounded-xl overflow-hidden flex-shrink-0 border border-[#AAFF00]/20"
                whileHover={{ scale: 1.06 }}
                whileTap={{ scale: 0.95 }}
                transition={{ type: 'spring', stiffness: 400, damping: 20 }}
              >
                <Image src="/logo.png" alt="OMNIBUS Logo" width={36} height={36} className="w-full h-full object-cover" />
              </motion.div>
              <span className="hidden sm:block">
                <ShinyText
                  text="OMNIBUS"
                  speed={4}
                  color="#F8FAFC"
                  shineColor="#AAFF00"
                  className="font-bold text-base tracking-tight"
                />
              </span>
            </Link>

            {/* Desktop Navigation — centered, min-width 0 to prevent overflow */}
            <nav className="hidden lg:flex items-center gap-0.5 flex-1 justify-center min-w-0 px-4">
              {navLinks.map((link) => {
                const isActive = pathname === link.href;
                return (
                  <Link key={link.href} href={link.href} className="flex-shrink-0">
                    <motion.div
                      className={`relative px-3 py-2 rounded-lg text-sm font-medium cursor-pointer select-none transition-colors duration-200 ${isActive ? 'text-[#AAFF00]' : 'text-slate-400 hover:text-slate-100'
                        }`}
                      whileTap={{ scale: 0.97 }}
                    >
                      <span className="flex items-center gap-1.5 whitespace-nowrap">
                        <svg
                          className={`w-3.5 h-3.5 flex-shrink-0 transition-colors duration-200 ${isActive ? 'text-[#AAFF00]' : 'text-slate-500'}`}
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={link.icon} />
                        </svg>
                        {link.label}
                      </span>

                      {isActive && (
                        <motion.div
                          layoutId="nav-pill"
                          className="absolute inset-0 rounded-lg -z-10"
                          style={{
                            background: 'rgba(170, 255, 0, 0.08)',
                            border: '1px solid rgba(170, 255, 0, 0.18)',
                          }}
                          transition={{ type: 'spring', bounce: 0.15, duration: 0.4 }}
                        />
                      )}
                    </motion.div>
                  </Link>
                );
              })}
            </nav>

            {/* Right side — Status + CTA, always flex-shrink-0 */}
            <div className="hidden lg:flex items-center gap-3 flex-shrink-0">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/8">
                <div className="w-1.5 h-1.5 rounded-full bg-[#4ADE80] animate-pulse-online" />
                <span className="text-xs text-slate-400 font-medium">Online</span>
              </div>

              <motion.button
                className="px-4 py-2 bg-[#AAFF00] text-[#0A0A0F] text-sm font-bold rounded-xl flex-shrink-0 whitespace-nowrap"
                whileHover={{ scale: 1.04, boxShadow: '0 0 20px rgba(170, 255, 0, 0.35)' }}
                whileTap={{ scale: 0.96 }}
                transition={{ type: 'spring', stiffness: 400, damping: 20 }}
              >
                Mulai Gratis
              </motion.button>
            </div>

            {/* Mobile hamburger */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="lg:hidden flex-shrink-0 p-2 rounded-lg text-slate-300 hover:text-[#AAFF00] hover:bg-white/5 transition-colors"
              aria-label="Toggle menu"
            >
              <motion.div animate={{ rotate: isMobileMenuOpen ? 90 : 0 }} transition={{ duration: 0.2 }}>
                {isMobileMenuOpen ? <CloseIcon /> : <MenuIcon />}
              </motion.div>
            </button>
          </div>
        </motion.div>
      </motion.div>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
              onClick={() => setIsMobileMenuOpen(false)}
            />

            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', bounce: 0.1, duration: 0.35 }}
              className="fixed top-0 right-0 bottom-0 w-72 bg-[#0A0A0F]/95 backdrop-blur-xl z-50 lg:hidden border-l border-white/8"
            >
              <div className="flex flex-col h-full pt-20 px-4 pb-6">
                <div className="flex items-center gap-3 px-2 mb-6 pb-6 border-b border-white/8">
                  <div className="w-9 h-9 rounded-xl overflow-hidden border border-[#AAFF00]/20 flex-shrink-0">
                    <Image src="/logo.png" alt="OMNIBUS Logo" width={36} height={36} className="w-full h-full object-cover" />
                  </div>
                  <span className="text-base font-bold text-white">OMNIBUS</span>
                </div>

                <nav className="flex-1 space-y-1">
                  {navLinks.map((link, index) => {
                    const isActive = pathname === link.href;
                    return (
                      <motion.div
                        key={link.href}
                        initial={{ x: 16, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        transition={{ delay: index * 0.04, duration: 0.25 }}
                      >
                        <Link href={link.href}>
                          <div className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${isActive
                              ? 'text-[#AAFF00] bg-[#AAFF00]/8 border border-[#AAFF00]/15'
                              : 'text-slate-400 hover:text-white hover:bg-white/5'
                            }`}>
                            <svg className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-[#AAFF00]' : 'text-slate-500'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={link.icon} />
                            </svg>
                            {link.label}
                          </div>
                        </Link>
                      </motion.div>
                    );
                  })}
                </nav>

                <div className="pt-4 mt-4 border-t border-white/8">
                  <button className="w-full py-3 bg-[#AAFF00] text-[#0A0A0F] text-sm font-bold rounded-xl">
                    Mulai Gratis
                  </button>
                  <div className="flex items-center justify-center gap-2 mt-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#4ADE80] animate-pulse-online" />
                    <span className="text-xs text-slate-500">Sistem Online</span>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
