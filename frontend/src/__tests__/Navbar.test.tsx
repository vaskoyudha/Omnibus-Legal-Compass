import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import React from 'react';

// Mock Next.js modules
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock('next/image', () => ({
  default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => <img {...props} />,
}));

vi.mock('next/navigation', () => ({
  usePathname: () => '/',
}));

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    header: ({ children, ...props }: React.HTMLAttributes<HTMLElement>) => (
      <header {...props}>{children}</header>
    ),
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
      <div {...props}>{children}</div>
    ),
    button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
      <button {...props}>{children}</button>
    ),
    span: ({ children, ...props }: React.HTMLAttributes<HTMLSpanElement>) => (
      <span {...props}>{children}</span>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useMotionValue: () => ({ set: vi.fn(), get: () => 0 }),
  useAnimationFrame: () => {},
  useTransform: () => '0% center',
}));

// Mock ShinyText — renders the text prop as plain text
vi.mock('@/components/reactbits/ShinyText', () => ({
  default: ({ text, className }: { text: string; className?: string }) => (
    <span className={className}>{text}</span>
  ),
}));

import Navbar from '@/components/Navbar';

describe('Navbar', () => {
  it('renders without crashing', () => {
    render(<Navbar />);
    expect(screen.getByRole('banner')).toBeInTheDocument();
  });

  it('contains OMNIBUS brand name', () => {
    render(<Navbar />);
    // banner may be rendered more than once (layout variants). Use getAllByRole
    const banners = screen.getAllByRole('banner');
    expect(banners.length).toBeGreaterThan(0);
    // ensure at least one banner contains the OMNIBUS text
    const found = banners.some(b => {
      try {
        return within(b).getAllByText('OMNIBUS').length > 0;
      } catch {
        return false;
      }
    });
    expect(found).toBe(true);
  });

  it('contains navigation links: Beranda, Kepatuhan, Panduan', () => {
    render(<Navbar />);
    const banners = screen.getAllByRole('banner');
    const foundNav = banners.some(b => {
      try {
        const w = within(b);
        return (
          w.getAllByText('Beranda').length > 0 &&
          w.getAllByText('Kepatuhan').length > 0 &&
          w.getAllByText('Panduan').length > 0
        );
      } catch {
        return false;
      }
    });
    expect(foundNav).toBe(true);
  });

  it('renders the CTA button "Mulai Gratis"', () => {
    render(<Navbar />);
    const banners = screen.getAllByRole('banner');
    const foundCTA = banners.some(b => {
      try {
        return within(b).getAllByRole('button', { name: /Mulai Gratis/i }).length > 0;
      } catch {
        return false;
      }
    });
    expect(foundCTA).toBe(true);
  });
});
