import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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
    expect(screen.getByText('OMNIBUS')).toBeInTheDocument();
  });

  it('contains navigation links: Beranda, Kepatuhan, Panduan', () => {
    render(<Navbar />);
    expect(screen.getByText('Beranda')).toBeInTheDocument();
    expect(screen.getByText('Kepatuhan')).toBeInTheDocument();
    expect(screen.getByText('Panduan')).toBeInTheDocument();
  });

  it('renders the CTA button "Mulai Gratis"', () => {
    render(<Navbar />);
    expect(screen.getByText('Mulai Gratis')).toBeInTheDocument();
  });
});
