import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Omnibus Legal Compass',
  description: 'Indonesian Legal RAG System — AI-powered legal Q&A with citations',
  base: '/Omnibus-intelligence/',
  head: [['link', { rel: 'icon', type: 'image/png', href: '/logo.png' }]],
  themeConfig: {
    logo: '/logo.png',
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Guide', link: '/getting-started' },
      { text: 'API', link: '/api-reference' },
      { text: 'GitHub', link: 'https://github.com/vaskoyudha/Omnibus-intelligence' },
    ],
    sidebar: [
      {
        text: 'Introduction',
        items: [
          { text: 'Getting Started', link: '/getting-started' },
          { text: 'Architecture', link: '/architecture' },
        ],
      },
      {
        text: 'Features',
        items: [
          { text: 'Features Overview', link: '/features' },
          { text: 'Knowledge Graph', link: '/knowledge-graph' },
          { text: 'Competitive Comparison', link: '/comparison' },
        ],
      },
      {
        text: 'Reference',
        items: [
          { text: 'API Reference', link: '/api-reference' },
          { text: 'Deployment', link: '/deployment' },
        ],
      },
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/vaskoyudha/Omnibus-intelligence' },
    ],
    editLink: {
      pattern: 'https://github.com/vaskoyudha/Omnibus-intelligence/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },
    search: { provider: 'local' },
    footer: {
      message: 'Released under the MIT License.',
      copyright: 'This tool does not constitute legal advice.',
    },
  },
})
