import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import SearchBar from '@/components/SearchBar';

describe('SearchBar', () => {
  it('renders an input element with the correct placeholder', () => {
    render(<SearchBar onSearch={vi.fn()} isLoading={false} />);
    expect(
      screen.getByPlaceholderText('Ketik pertanyaan hukum Anda...')
    ).toBeInTheDocument();
  });

  it('updates the input value when the user types', () => {
    render(<SearchBar onSearch={vi.fn()} isLoading={false} />);
    const input = screen.getByPlaceholderText('Ketik pertanyaan hukum Anda...') as HTMLInputElement;

    fireEvent.change(input, { target: { value: 'Apa itu NIB?' } });
    expect(input.value).toBe('Apa itu NIB?');
  });

  it('calls onSearch with trimmed query when the form is submitted', () => {
    const mockOnSearch = vi.fn();
    render(<SearchBar onSearch={mockOnSearch} isLoading={false} />);
    const input = screen.getByPlaceholderText('Ketik pertanyaan hukum Anda...');

    fireEvent.change(input, { target: { value: '  Syarat pendirian PT  ' } });
    fireEvent.submit(input.closest('form')!);

    expect(mockOnSearch).toHaveBeenCalledWith('Syarat pendirian PT');
  });

  it('does NOT call onSearch when query is empty', () => {
    const mockOnSearch = vi.fn();
    render(<SearchBar onSearch={mockOnSearch} isLoading={false} />);
    const input = screen.getByPlaceholderText('Ketik pertanyaan hukum Anda...');

    fireEvent.submit(input.closest('form')!);
    expect(mockOnSearch).not.toHaveBeenCalled();
  });

  it('disables input when isLoading is true', () => {
    render(<SearchBar onSearch={vi.fn()} isLoading={true} />);
    const input = screen.getByPlaceholderText('Ketik pertanyaan hukum Anda...');
    expect(input).toBeDisabled();
  });

  it('shows "Mencari..." text when loading', () => {
    render(<SearchBar onSearch={vi.fn()} isLoading={true} />);
    expect(screen.getByText('Mencari...')).toBeInTheDocument();
  });
});
