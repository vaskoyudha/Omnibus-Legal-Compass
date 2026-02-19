import '@testing-library/jest-dom/vitest';
import { JSDOM } from 'jsdom';

// Bootstrap a minimal DOM for test environments (used by Bun when preload'd)
const dom = new JSDOM('<!doctype html><html><body></body></html>', {
  url: 'http://localhost'
});

// Expose common globals expected by tests
// @ts-ignore
(globalThis as any).window = dom.window;
// @ts-ignore
(globalThis as any).document = dom.window.document;
// @ts-ignore
(globalThis as any).navigator = dom.window.navigator;

// Copy window properties to globalThis (like window.HTMLElement, etc.)
Object.getOwnPropertyNames(dom.window).forEach((prop) => {
  if (prop === 'localStorage' || prop === 'sessionStorage') return;
  // @ts-ignore
  if (typeof (globalThis as any)[prop] === 'undefined') {
    try {
      // @ts-ignore
      (globalThis as any)[prop] = (dom.window as any)[prop];
    } catch (_e) {
      // ignore read-only properties
    }
  }
});

// Provide a basic document.createRange implementation used by some libs
// @ts-ignore
if (typeof (document as any).createRange === 'undefined') {
  // @ts-ignore
  (document as any).createRange = () => ({
    setStart: () => {},
    setEnd: () => {},
    commonAncestorContainer: { nodeName: 'BODY', ownerDocument: document }
  });
}
