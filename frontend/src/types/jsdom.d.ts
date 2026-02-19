// Minimal local declarations for 'jsdom' to satisfy TypeScript during build
// Keep tiny: declaring only what test-setup.ts uses (JSDOM constructor and Window)
declare module 'jsdom' {
  export interface DOMWindow {
    document: Document;
    navigator: Navigator;
    HTMLElement: any;
    Node: any;
    [key: string]: any;
  }

  export interface ConstructorOptions {
    url?: string;
    contentType?: string;
    referrer?: string;
    userAgent?: string;
    includeNodeLocations?: boolean;
    runScripts?: 'dangerously' | undefined;
    resources?: any;
  }

  export class JSDOM {
    constructor(html?: string, options?: ConstructorOptions);
    window: DOMWindow;
    serialize(): string;
    static fragment(html: string): DocumentFragment;
  }

  const jsdom: typeof import('jsdom');
  export default jsdom;
}
