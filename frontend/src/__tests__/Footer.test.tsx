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
    const { getAllByText } = render(<Footer />);
    // multiple identical branding nodes may exist (mobile/desktop/layout duplicates)
    // assert at least one exists using the *AllBy* variant to avoid ambiguous failures
    const matches = getAllByText('OMNIBUS');
    expect(matches.length).toBeGreaterThan(0);
  });

  it('contains legal disclaimer text about not constituting legal advice', () => {
    const { getAllByText } = render(<Footer />);
    const matches = getAllByText(/does not constitute legal advice/i);
    expect(matches.length).toBeGreaterThan(0);
  });

  it('contains copyright text with current year', () => {
    const { getAllByText } = render(<Footer />);
    const year = new Date().getFullYear();
    const matches = getAllByText(new RegExp(`© ${year} OMNIBUS`));
    expect(matches.length).toBeGreaterThan(0);
  });

  it('renders product links (Tanya Jawab, Kepatuhan, Panduan Usaha)', () => {
    const { getAllByText } = render(<Footer />);
    expect(getAllByText('Tanya Jawab').length).toBeGreaterThan(0);
    expect(getAllByText('Kepatuhan').length).toBeGreaterThan(0);
    expect(getAllByText('Panduan Usaha').length).toBeGreaterThan(0);
  });
});
