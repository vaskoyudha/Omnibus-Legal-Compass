import { describe, it, expect } from 'vitest';
import { parseInlineCitations, TextSegment } from '@/lib/citation-parser';

describe('parseInlineCitations', () => {
  it('parse_single_citation — parses "text [1] more" into 3 segments', () => {
    const result = parseInlineCitations('text [1] more', 1);
    expect(result).toEqual<TextSegment[]>([
      { type: 'text', content: 'text ' },
      { type: 'citation', content: '1', citationIndex: 0 },
      { type: 'text', content: ' more' },
    ]);
  });

  it('parse_multiple_citations — parses "[1] and [2]" into 3 segments', () => {
    const result = parseInlineCitations('[1] and [2]', 2);
    expect(result).toEqual<TextSegment[]>([
      { type: 'citation', content: '1', citationIndex: 0 },
      { type: 'text', content: ' and ' },
      { type: 'citation', content: '2', citationIndex: 1 },
    ]);
  });

  it('parse_consecutive_citations — parses "text [1][2]" with no empty text between', () => {
    const result = parseInlineCitations('text [1][2]', 2);
    expect(result).toEqual<TextSegment[]>([
      { type: 'text', content: 'text ' },
      { type: 'citation', content: '1', citationIndex: 0 },
      { type: 'citation', content: '2', citationIndex: 1 },
    ]);
  });

  it('parse_no_citations — returns single text segment for plain text', () => {
    const result = parseInlineCitations('plain text', 3);
    expect(result).toEqual<TextSegment[]>([
      { type: 'text', content: 'plain text' },
    ]);
  });

  it('parse_empty_text — returns single text segment with empty content', () => {
    const result = parseInlineCitations('', 5);
    expect(result).toEqual<TextSegment[]>([
      { type: 'text', content: '' },
    ]);
  });

  it('parse_out_of_range — treats [5] as literal text when citationCount=2', () => {
    const result = parseInlineCitations('text [5] more', 2);
    expect(result).toEqual<TextSegment[]>([
      { type: 'text', content: 'text [5] more' },
    ]);
  });

  it('parse_zero_citations — returns full text as single segment even with [1]', () => {
    const result = parseInlineCitations('text [1] here', 0);
    expect(result).toEqual<TextSegment[]>([
      { type: 'text', content: 'text [1] here' },
    ]);
  });

  it('parse_mixed — only valid citations are parsed, out-of-range kept as literal', () => {
    const result = parseInlineCitations('See [1] and also [3]', 2);
    expect(result).toEqual<TextSegment[]>([
      { type: 'text', content: 'See ' },
      { type: 'citation', content: '1', citationIndex: 0 },
      { type: 'text', content: ' and also [3]' },
    ]);
  });

  it('handles text with brackets that are not citation patterns', () => {
    const result = parseInlineCitations('array[0] and [abc] test', 1);
    expect(result).toEqual<TextSegment[]>([
      { type: 'text', content: 'array[0] and [abc] test' },
    ]);
  });

  it('handles citation at the very end of text', () => {
    const result = parseInlineCitations('see this [2]', 3);
    expect(result).toEqual<TextSegment[]>([
      { type: 'text', content: 'see this ' },
      { type: 'citation', content: '2', citationIndex: 1 },
    ]);
  });
});
