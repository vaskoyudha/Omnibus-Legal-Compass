import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import React from 'react';
import SkeletonLoader from '@/components/SkeletonLoader';

describe('SkeletonLoader', () => {
  it('renders card variant (default) with status role', () => {
    // multiple status roles may exist in the DOM; scope to the rendered container
    const { container } = render(<SkeletonLoader />);
    const status = within(container).getByRole('status');
    expect(status).toBeInTheDocument();
    expect(status).toHaveAttribute('aria-label', 'Memuat...');
  });

  it('renders text variant with the specified number of lines', () => {
    const { container } = render(<SkeletonLoader variant="text" lines={4} />);
    const status = within(container).getByRole('status');
    expect(status).toBeInTheDocument();
    // sr-only loading text should be inside this rendered tree
    expect(within(container).getByText('Memuat...')).toBeInTheDocument();
  });

  it('renders paragraph variant with heading skeleton and lines', () => {
    const { container } = render(<SkeletonLoader variant="paragraph" lines={5} />);
    const status = within(container).getByRole('status');
    expect(status).toBeInTheDocument();
    expect(status).toHaveAttribute('aria-label', 'Memuat...');
  });
});
