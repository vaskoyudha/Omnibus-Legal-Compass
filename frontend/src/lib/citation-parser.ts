export interface TextSegment {
  type: 'text' | 'citation';
  content: string;
  citationIndex?: number; // 0-based index into citations array
}

/**
 * Parse answer text containing [1], [2], [3] markers into segments.
 *
 * Example:
 *   input: "Menurut UU [1], hal ini diatur dalam Pasal 5 [2]."
 *   output: [
 *     { type: 'text', content: 'Menurut UU ' },
 *     { type: 'citation', content: '1', citationIndex: 0 },
 *     { type: 'text', content: ', hal ini diatur dalam Pasal 5 ' },
 *     { type: 'citation', content: '2', citationIndex: 1 },
 *     { type: 'text', content: '.' },
 *   ]
 *
 * Rules:
 * - Match pattern: \[(\d+)\]
 * - Citation numbers are 1-based in text, converted to 0-based index
 * - Only match if citation number <= citationCount
 * - Ignore [N] where N > citationCount (treat as literal text)
 * - Handle consecutive citations: [1][2] → two separate citation segments
 * - Handle edge cases: empty text, no citations, text with [brackets] that aren't citations
 */
export function parseInlineCitations(text: string, citationCount: number): TextSegment[] {
  if (!text) return [{ type: 'text', content: '' }];
  if (citationCount <= 0) return [{ type: 'text', content: text }];

  const segments: TextSegment[] = [];
  const regex = /\[(\d+)\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    const num = parseInt(match[1], 10);
    if (num < 1 || num > citationCount) {
      // Not a valid citation — treat as text, continue
      continue;
    }

    // Push preceding text segment (if any)
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: text.slice(lastIndex, match.index) });
    }

    // Push citation segment
    segments.push({
      type: 'citation',
      content: match[1],
      citationIndex: num - 1, // convert to 0-based
    });

    lastIndex = match.index + match[0].length;
  }

  // Push remaining text
  if (lastIndex < text.length) {
    segments.push({ type: 'text', content: text.slice(lastIndex) });
  }

  // If no segments were produced (e.g., all [N] had N > citationCount), return full text
  if (segments.length === 0) {
    return [{ type: 'text', content: text }];
  }

  return segments;
}
