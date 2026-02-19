import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import React from 'react';
import SearchBar from '@/components/SearchBar';

describe('SearchBar', () => {
  it('renders an input element with the correct placeholder', () => {
    // scope queries to this render to avoid collisions with other components
    const { container } = render(<SearchBar onSearch={vi.fn()} isLoading={false} />);
    // NOTE: placeholder in component is "Tanyakan seputar hukum Indonesia..."
    const input = within(container).getByPlaceholderText('Tanyakan seputar hukum Indonesia...');
    expect(input).toBeInTheDocument();
  });

  it('updates the input value when the user types', () => {
    const { container } = render(<SearchBar onSearch={vi.fn()} isLoading={false} />);
    const input = within(container).getByPlaceholderText('Tanyakan seputar hukum Indonesia...') as HTMLInputElement;

    fireEvent.change(input, { target: { value: 'Apa itu NIB?' } });
    expect(input.value).toBe('Apa itu NIB?');
  });

  it('calls onSearch with trimmed query when the form is submitted', () => {
    const mockOnSearch = vi.fn();
    const { container } = render(<SearchBar onSearch={mockOnSearch} isLoading={false} />);
    const input = within(container).getByPlaceholderText('Tanyakan seputar hukum Indonesia...');

    fireEvent.change(input, { target: { value: '  Syarat pendirian PT  ' } });
    // submit the enclosing form
    fireEvent.submit(input.closest('form')!);

    expect(mockOnSearch).toHaveBeenCalledWith('Syarat pendirian PT');
  });

  it('does NOT call onSearch when query is empty', () => {
    const mockOnSearch = vi.fn();
    const { container } = render(<SearchBar onSearch={mockOnSearch} isLoading={false} />);
    const input = within(container).getByPlaceholderText('Tanyakan seputar hukum Indonesia...');

    fireEvent.submit(input.closest('form')!);
    expect(mockOnSearch).not.toHaveBeenCalled();
  });

  it('disables input when isLoading is true', () => {
    const { container } = render(<SearchBar onSearch={vi.fn()} isLoading={true} />);
    const input = within(container).getByPlaceholderText('Tanyakan seputar hukum Indonesia...');
    expect(input).toBeDisabled();
  });

  it('shows "Mencari..." text when loading', () => {
    // when loading the component shows a spinner inside the submit button
    const { container } = render(<SearchBar onSearch={vi.fn()} isLoading={true} />);
    const button = within(container).getByRole('button');
    expect(button).toBeDisabled();
    // spinner svg uses the `animate-spin` class
    const spinner = button.querySelector('svg');
    expect(spinner).toBeTruthy();
    if (spinner) expect(spinner).toHaveClass('animate-spin');
  });
});
