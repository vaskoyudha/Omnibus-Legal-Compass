import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import InlineCitation from '@/components/chat/InlineCitation';

describe('InlineCitation', () => {
  it('renders [1] number correctly', () => {
    render(<InlineCitation number={1} citationIndex={0} />);
    expect(screen.getByText('[1]')).toBeInTheDocument();
  });

  it('renders [3] for number=3', () => {
    render(<InlineCitation number={3} citationIndex={2} />);
    expect(screen.getByText('[3]')).toBeInTheDocument();
  });

  it('calls onClick with correct 0-based index when clicked', () => {
    const handleClick = vi.fn();
    render(<InlineCitation number={2} citationIndex={1} onClick={handleClick} />);

    fireEvent.click(screen.getByText('[2]'));
    expect(handleClick).toHaveBeenCalledTimes(1);
    expect(handleClick).toHaveBeenCalledWith(1);
  });

  it('has aria-label for accessibility', () => {
    render(<InlineCitation number={1} citationIndex={0} />);
    expect(screen.getByLabelText('Kutipan 1')).toBeInTheDocument();
  });

  it('shows highlighted styles when isHighlighted=true', () => {
    const { container } = render(
      <InlineCitation number={1} citationIndex={0} isHighlighted />
    );
    const sup = container.querySelector('sup');
    expect(sup).not.toBeNull();
    // Highlighted state adds the glow/brighter background class
    expect(sup!.className).toContain('bg-[#AAFF00]/20');
  });

  it('shows default styles when isHighlighted is false', () => {
    const { container } = render(
      <InlineCitation number={1} citationIndex={0} isHighlighted={false} />
    );
    const sup = container.querySelector('sup');
    expect(sup).not.toBeNull();
    expect(sup!.className).toContain('bg-[#AAFF00]/10');
    expect(sup!.className).not.toContain('bg-[#AAFF00]/20');
  });

  it('is keyboard accessible — triggers onClick on Enter key', () => {
    const handleClick = vi.fn();
    render(<InlineCitation number={1} citationIndex={0} onClick={handleClick} />);

    const element = screen.getByLabelText('Kutipan 1');
    fireEvent.keyDown(element, { key: 'Enter' });
    expect(handleClick).toHaveBeenCalledTimes(1);
    expect(handleClick).toHaveBeenCalledWith(0);
  });

  it('displays title as tooltip when provided', () => {
    render(
      <InlineCitation number={1} citationIndex={0} title="UU No. 40 Tahun 2007" />
    );
    const element = screen.getByLabelText('Kutipan 1');
    expect(element.getAttribute('title')).toBe('UU No. 40 Tahun 2007');
  });
});
