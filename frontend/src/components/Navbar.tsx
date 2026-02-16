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
  { href: '/knowledge-graph', label: 'Graf Hukum', icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
  { href: '/chat', label: 'Percakapan', icon: 'M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z' },
  { href: '/dashboard', label: 'Dashboard', icon: 'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z' },
];

// Icons
const MenuIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="4" x2="20" y1="12" y2="12" />
    <line x1="4" x2="20" y1="6" y2="6" />
    <line x1="4" x2="20" y1="18" y2="18" />
  </svg>
);

const CloseIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

export default function Navbar() {
  const pathname = usePathname();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Handle scroll effect
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [pathname]);

  // Lock body scroll when mobile menu is open
  useEffect(() => {
    if (isMobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
  }, [isMobileMenuOpen]);

  return (
    <>
      <motion.header
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className={`fixed top-0 left-0 right-0 z-50 no-print will-change-[background-color,box-shadow] transition-[background-color,box-shadow,border-color] duration-300 ${isScrolled
          ? 'bg-[#0A0A0F]/90 backdrop-blur-xl shadow-lg shadow-black/20 border-b border-white/[0.04]'
          : 'bg-transparent backdrop-blur-none border-b border-transparent'
          }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16 sm:h-20">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-3 group">
              <motion.div
                className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl overflow-hidden flex items-center justify-center shadow-lg shadow-[#AAFF00]/20 border border-[#AAFF00]/20"
                whileHover={{ scale: 1.08, rotate: -2 }}
                whileTap={{ scale: 0.95 }}
                transition={{ type: 'spring', stiffness: 400, damping: 15 }}
              >
                <Image
                  src="/logo.png"
                  alt="OMNIBUS Logo"
                  width={44}
                  height={44}
                  className="w-full h-full object-cover"
                />
              </motion.div>
              <span className="hidden sm:block">
                <ShinyText
                  text="OMNIBUS"
                  speed={4}
                  color="#F8FAFC"
                  shineColor="#AAFF00"
                  className="font-bold text-xl tracking-tight"
                />
              </span>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden lg:flex items-center gap-1">
              {navLinks.map((link) => {
                const isActive = pathname === link.href;
                return (
                  <Link key={link.href} href={link.href}>
                    <motion.div
                      className={`relative px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${isActive
                        ? 'text-[#AAFF00]'
                        : 'text-slate-400 hover:text-slate-200'
                        }`}
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <span className="flex items-center gap-2">
                        <svg
                          className={`w-4 h-4 ${isActive ? 'text-[#AAFF00]' : 'text-slate-500'}`}
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
                          layoutId="nav-indicator"
                          className="absolute inset-0 bg-[#AAFF00]/8 border border-[#AAFF00]/20 rounded-xl -z-10"
                          transition={{ type: 'spring', bounce: 0.15, duration: 0.5 }}
                        />
                      )}
                    </motion.div>
                  </Link>
                );
              })}
            </nav>

            {/* Desktop Status + CTA */}
            <div className="hidden lg:flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700/50">
                <div className="w-2 h-2 rounded-full bg-[#4ADE80] animate-pulse-online shadow-[0_0_8px_#4ADE80]" />
                <span className="text-xs text-slate-400 font-medium">Online</span>
              </div>
              <motion.button
                className="px-5 py-2.5 bg-gradient-to-r from-[#AAFF00] to-[#BBFF33] text-slate-900 text-sm font-bold rounded-xl hover:shadow-xl hover:shadow-[#AAFF00]/25 transition-all"
                whileHover={{ scale: 1.03, boxShadow: '0 0 30px rgba(170, 255, 0, 0.3)' }}
                whileTap={{ scale: 0.97 }}
              >
                Mulai Gratis
              </motion.button>
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="lg:hidden p-2 rounded-xl text-slate-300 hover:text-[#AAFF00] hover:bg-slate-800/50 transition-colors"
              aria-label="Toggle menu"
            >
              <motion.div
                animate={{ rotate: isMobileMenuOpen ? 90 : 0 }}
                transition={{ duration: 0.2 }}
              >
                {isMobileMenuOpen ? <CloseIcon /> : <MenuIcon />}
              </motion.div>
            </button>
          </div>
        </div>

        {/* Bottom border with subtle gradient */}
        <div className="h-px bg-gradient-to-r from-transparent via-[rgba(170,255,0,0.15)] to-transparent" />
      </motion.header>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
              onClick={() => setIsMobileMenuOpen(false)}
            />

            {/* Mobile Menu Panel */}
            <motion.div
              initial={{ x: '100%', opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: '100%', opacity: 0 }}
              transition={{ type: 'spring', bounce: 0.15, duration: 0.4 }}
              className="fixed top-0 right-0 bottom-0 w-[280px] bg-[#0A0A0F]/95 backdrop-blur-xl z-50 lg:hidden border-l border-[#AAFF00]/10"
            >
              <div className="flex flex-col h-full pt-20 px-4 pb-6">
                {/* Mobile Logo */}
                <div className="flex items-center gap-3 px-2 mb-6 pb-6 border-b border-slate-800">
                  <div className="w-10 h-10 rounded-xl overflow-hidden flex items-center justify-center border border-[#AAFF00]/20">
                    <Image
                      src="/logo.png"
                      alt="OMNIBUS Logo"
                      width={40}
                      height={40}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <span className="text-lg font-bold text-white">OMNIBUS</span>
                </div>

                {/* Mobile Nav Links */}
                <nav className="flex-1 space-y-1">
                  {navLinks.map((link, index) => {
                    const isActive = pathname === link.href;
                    return (
                      <motion.div
                        key={link.href}
                        initial={{ x: 20, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        transition={{ delay: index * 0.05 }}
                      >
                        <Link href={link.href}>
                          <div
                            className={`flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm font-medium transition-all ${isActive
                              ? 'text-[#AAFF00] bg-[#AAFF00]/10 border border-[#AAFF00]/20'
                              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                              }`}
                          >
                            <svg
                              className={`w-5 h-5 ${isActive ? 'text-[#AAFF00]' : 'text-slate-500'}`}
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={link.icon} />
                            </svg>
                            {link.label}
                          </div>
                        </Link>
                      </motion.div>
                    );
                  })}
                </nav>

                {/* Mobile CTA */}
                <div className="pt-4 mt-4 border-t border-slate-800">
                  <motion.button
                    className="w-full py-3.5 bg-gradient-to-r from-[#AAFF00] to-[#BBFF33] text-slate-900 text-sm font-bold rounded-xl"
                    whileTap={{ scale: 0.98 }}
                  >
                    Mulai Gratis
                  </motion.button>
                  <div className="flex items-center justify-center gap-2 mt-4">
                    <div className="w-2 h-2 rounded-full bg-[#4ADE80] animate-pulse-online" />
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
