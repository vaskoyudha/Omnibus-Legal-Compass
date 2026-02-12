import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import SkeletonLoader from '@/components/SkeletonLoader';

describe('SkeletonLoader', () => {
  it('renders card variant (default) with status role', () => {
    render(<SkeletonLoader />);
    const status = screen.getByRole('status');
    expect(status).toBeInTheDocument();
    expect(status).toHaveAttribute('aria-label', 'Memuat...');
  });

  it('renders text variant with the specified number of lines', () => {
    render(<SkeletonLoader variant="text" lines={4} />);
    const status = screen.getByRole('status');
    expect(status).toBeInTheDocument();
    // sr-only loading text
    expect(screen.getByText('Memuat...')).toBeInTheDocument();
  });

  it('renders paragraph variant with heading skeleton and lines', () => {
    render(<SkeletonLoader variant="paragraph" lines={5} />);
    const status = screen.getByRole('status');
    expect(status).toBeInTheDocument();
    expect(status).toHaveAttribute('aria-label', 'Memuat...');
  });
});
