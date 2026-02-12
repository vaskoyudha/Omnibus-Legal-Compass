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

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    footer: ({ children, ...props }: React.HTMLAttributes<HTMLElement>) => (
      <footer {...props}>{children}</footer>
    ),
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
      <div {...props}>{children}</div>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import Footer from '@/components/Footer';

describe('Footer', () => {
  it('renders without crashing', () => {
    render(<Footer />);
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
  });

  it('contains OMNIBUS branding text', () => {
    render(<Footer />);
    expect(screen.getByText('OMNIBUS')).toBeInTheDocument();
  });

  it('contains legal disclaimer text about not constituting legal advice', () => {
    render(<Footer />);
    expect(
      screen.getByText(/does not constitute legal advice/i)
    ).toBeInTheDocument();
  });

  it('contains copyright text with current year', () => {
    render(<Footer />);
    const year = new Date().getFullYear();
    expect(
      screen.getByText(new RegExp(`© ${year} OMNIBUS`))
    ).toBeInTheDocument();
  });

  it('renders product links (Tanya Jawab, Kepatuhan, Panduan Usaha)', () => {
    render(<Footer />);
    expect(screen.getByText('Tanya Jawab')).toBeInTheDocument();
    expect(screen.getByText('Kepatuhan')).toBeInTheDocument();
    expect(screen.getByText('Panduan Usaha')).toBeInTheDocument();
  });
});
