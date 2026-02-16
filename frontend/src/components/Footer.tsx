'use client';

import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';

const footerLinks = {
    product: [
        { label: 'Tanya Jawab', href: '/' },
        { label: 'Kepatuhan', href: '/compliance' },
        { label: 'Panduan Usaha', href: '/guidance' },
    ],
    resources: [
        { label: 'Dokumentasi', href: '#' },
        { label: 'API Reference', href: '#' },
        { label: 'Blog', href: '#' },
    ],
    legal: [
        { label: 'Privacy Policy', href: '#' },
        { label: 'Terms of Service', href: '#' },
        { label: 'Cookie Policy', href: '#' },
    ],
    company: [
        { label: 'About Us', href: '#' },
        { label: 'Contact', href: '#' },
        { label: 'Careers', href: '#' },
    ],
};

export default function Footer() {
    return (
        <motion.footer
            className="relative z-10 border-t border-border mt-auto bg-[#0A0A0F]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.5 }}
        >
            <div className="max-w-6xl mx-auto px-6 py-12">
                {/* Top Section — Logo + Columns */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-8 mb-10">
                    {/* Brand Column */}
                    <div className="col-span-2 sm:col-span-1">
                        <Link href="/" className="flex items-center gap-2 mb-3 group">
                            <div className="w-8 h-8 rounded-lg overflow-hidden flex items-center justify-center shadow-md shadow-[#AAFF00]/15">
                                <Image
                                    src="/logo.png"
                                    alt="OMNIBUS Logo"
                                    width={32}
                                    height={32}
                                    className="w-full h-full object-cover"
                                />
                            </div>
                            <span className="font-bold text-text-primary tracking-tight">OMNIBUS</span>
                        </Link>
                        <p className="text-xs text-text-muted leading-relaxed mb-4 max-w-[200px]">
                            Platform Harmonisasi & Intelijen Hukum Indonesia.
                        </p>
                        {/* AI Powered badge */}
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#AAFF00]/10 border border-[#AAFF00]/20">
                            <div className="w-1.5 h-1.5 rounded-full bg-[#4ADE80] animate-pulse-online" />
                            <span className="text-[10px] font-medium text-[#AAFF00]">AI Online</span>
                        </div>
                    </div>

                    {/* Product */}
                    <div>
                        <h4 className="text-xs font-semibold text-text-primary uppercase tracking-widest mb-3">Product</h4>
                        <ul className="space-y-2">
                            {footerLinks.product.map((link) => (
                                <li key={link.label}>
                                    <Link href={link.href} className="text-sm text-text-muted hover:text-[#AAFF00] transition-colors">
                                        {link.label}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Resources */}
                    <div>
                        <h4 className="text-xs font-semibold text-text-primary uppercase tracking-widest mb-3">Resources</h4>
                        <ul className="space-y-2">
                            {footerLinks.resources.map((link) => (
                                <li key={link.label}>
                                    <Link href={link.href} className="text-sm text-text-muted hover:text-[#AAFF00] transition-colors">
                                        {link.label}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Legal */}
                    <div>
                        <h4 className="text-xs font-semibold text-text-primary uppercase tracking-widest mb-3">Legal</h4>
                        <ul className="space-y-2">
                            {footerLinks.legal.map((link) => (
                                <li key={link.label}>
                                    <Link href={link.href} className="text-sm text-text-muted hover:text-[#AAFF00] transition-colors">
                                        {link.label}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Company */}
                    <div>
                        <h4 className="text-xs font-semibold text-text-primary uppercase tracking-widest mb-3">Company</h4>
                        <ul className="space-y-2">
                            {footerLinks.company.map((link) => (
                                <li key={link.label}>
                                    <Link href={link.href} className="text-sm text-text-muted hover:text-[#AAFF00] transition-colors">
                                        {link.label}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                {/* Legal Disclaimer */}
                <div className="mb-6 px-4 py-3 rounded-lg bg-white/[0.02] border border-border">
                    <p className="text-[11px] text-text-muted/70 leading-relaxed text-center">
                        <span className="font-medium text-text-muted/90">Disclaimer:</span>{' '}
                        This tool provides informational guidance only and does not constitute legal advice.
                        Always consult a qualified attorney for legal matters. OMNIBUS is not a law firm and
                        does not provide legal representation.
                    </p>
                </div>

                {/* Bottom Bar */}
                <div className="pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-3">
                    <p className="text-xs text-text-muted">
                        © {new Date().getFullYear()} OMNIBUS. All rights reserved.
                    </p>
                    <div className="flex items-center gap-4">
                        <span className="text-xs text-text-muted/60">v2.0.0</span>
                        <span className="text-xs text-text-muted/40">•</span>
                        <span className="text-xs text-text-muted/60">Powered by AI</span>
                    </div>
                </div>
            </div>
        </motion.footer>
    );
}
