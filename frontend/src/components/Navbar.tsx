'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import ShinyText from '@/components/reactbits/ShinyText';

const navLinks = [
  { href: '/', label: 'Tanya Jawab', icon: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
  { href: '/compliance', label: 'Kepatuhan', icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' },
  { href: '/guidance', label: 'Panduan Usaha', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01' },
  { href: '/knowledge-graph', label: 'Graf Hukum', icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <motion.header
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="fixed top-0 left-0 right-0 z-50 glass-strong no-print"
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <motion.div
            className="w-9 h-9 rounded-xl overflow-hidden flex items-center justify-center shadow-md shadow-[#AAFF00]/20"
            whileHover={{ scale: 1.05, rotate: -3 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 400, damping: 15 }}
          >
            <Image
              src="/logo.png"
              alt="OMNIBUS Logo"
              width={36}
              height={36}
              className="w-full h-full object-cover"
            />
          </motion.div>
          <span className="hidden sm:block">
            <ShinyText
              text="OMNIBUS"
              speed={4}
              color="#F1F5F9"
              shineColor="#AAFF00"
              className="font-bold text-lg tracking-tight"
            />
          </span>
        </Link>

        {/* Navigation Links */}
        <nav className="flex items-center gap-1">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link key={link.href} href={link.href}>
                <motion.div
                  className={`relative px-4 py-2 rounded-xl text-sm font-medium transition-colors flex items-center gap-2 ${isActive
                    ? 'text-[#AAFF00]'
                    : 'text-text-secondary hover:text-text-primary'
                    }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <svg
                    className={`w-4 h-4 hidden sm:block ${isActive ? 'text-[#AAFF00]' : 'text-text-muted'}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={link.icon} />
                  </svg>
                  {link.label}
                  {isActive && (
                    <motion.div
                      layoutId="nav-indicator"
                      className="absolute inset-0 bg-[#AAFF00]/10 border border-[#AAFF00]/20 rounded-xl -z-10"
                      transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                </motion.div>
              </Link>
            );
          })}

          {/* Status Dot + CTA */}
          <div className="hidden sm:flex items-center gap-3 ml-3 pl-3 border-l border-border">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-[#4ADE80] animate-pulse-online" />
              <span className="text-[10px] text-text-muted">Online</span>
            </div>
            <motion.button
              className="px-4 py-1.5 bg-gradient-to-r from-[#AAFF00] to-[#88CC00] text-[#0A0A0F] text-xs font-semibold rounded-lg hover:shadow-lg hover:shadow-[#AAFF00]/20 transition-all"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              Mulai Gratis
            </motion.button>
          </div>
        </nav>
      </div>

      {/* Bottom border with subtle gradient */}
      <div className="h-px bg-gradient-to-r from-transparent via-[rgba(255,255,255,0.08)] to-transparent" />
    </motion.header>
  );
}
