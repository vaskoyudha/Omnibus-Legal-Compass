'use client';

import dynamic from 'next/dynamic';
import { useEffect, useRef, useCallback } from 'react';

// Dynamic import for Three.js Beams (no SSR)
const Beams = dynamic(() => import('./Beams'), { ssr: false });

// ── Garuda Pancasila ASCII Art ──────────────────────────────────────────
const GARUDA_ART = [
    '                     ◆                     ',
    '                    ◆◆◆                    ',
    '                   ◆◆◆◆◆                   ',
    '                  ◆◆   ◆◆                  ',
    '                 ◆◆ ░░░ ◆◆                 ',
    '            ╱╱  ◆◆ ░░░░░ ◆◆  ╲╲            ',
    '          ╱╱╱╱ ◆◆ ░░███░░ ◆◆ ╲╲╲╲          ',
    '        ╱╱╱╱╱ ◆◆ ░░█████░░ ◆◆ ╲╲╲╲╲        ',
    '      ╱╱╱╱╱╱ ◆◆  ░░█░█░█░░  ◆◆ ╲╲╲╲╲╲      ',
    '    ╱╱╱╱╱╱╱ ◆◆  ░░░█████░░░  ◆◆ ╲╲╲╲╲╲╲    ',
    '   ╱╱╱╱╱╱ ◆◆   ░░░░███░░░░   ◆◆ ╲╲╲╲╲╲   ',
    '  ╱╱╱╱╱╱ ◆◆    ░░░░░░░░░░░    ◆◆ ╲╲╲╲╲╲  ',
    '   ╱╱╱╱╱  ◆◆                 ◆◆  ╲╲╲╲╲   ',
    '    ╱╱╱╱    ◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆    ╲╲╲╲    ',
    '     ╱╱╱      ▔▔▔▔▔▔▔▔▔▔▔▔▔      ╲╲╲     ',
    '      ╲╲╲    ╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱    ╱╱╱      ',
    '       ╲╲╲╲╱╱ BHINNEKA TUNGGAL ╲╲╱╱╱╱       ',
    '        ╲╲╲╲    IKA           ╱╱╱╱        ',
    '         ╲╲╲╲               ╱╱╱╱         ',
    '          ╲╲╲╲╲           ╱╱╱╱╱          ',
    '           ╲╲╲╲╲╲       ╱╱╱╱╱╱           ',
    '             ▕▕▕         ▕▕▕             ',
    '             ▕▕▕         ▕▕▕             ',
];

const RAIN_CHARS = '§¶†‡©®™01αβγδεΩΣΠΦΨ';

interface GarudaChar { char: string; revealed: boolean; revealTime: number; glow: number; fs: number; fp: number; row: number; col: number; }
interface RainDrop { x: number; y: number; speed: number; chars: string[]; length: number; opacity: number; }
interface GNode { x: number; y: number; bx: number; by: number; r: number; ps: number; pp: number; label: string; conn: number[]; gi: number; or: number; os: number; op: number; }

function AsciiGarudaOverlay() {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const animRef = useRef<number>(0);
    const stateRef = useRef({
        chars: [] as GarudaChar[], rain: [] as RainDrop[],
        lg: [] as GNode[], rg: [] as GNode[],
        init: false, revealStart: 0,
    });

    const initChars = useCallback(() => {
        const chars: GarudaChar[] = [];
        const cR = GARUDA_ART.length / 2;
        const cC = (GARUDA_ART[0]?.length || 0) / 2;
        for (let row = 0; row < GARUDA_ART.length; row++) {
            for (let col = 0; col < GARUDA_ART[row].length; col++) {
                const c = GARUDA_ART[row][col];
                if (c !== ' ') {
                    const dr = (row - cR) / GARUDA_ART.length;
                    const dc = (col - cC) / (GARUDA_ART[0]?.length || 1);
                    const dist = Math.sqrt(dr * dr + dc * dc);
                    chars.push({ char: c, revealed: false, revealTime: dist * 3000 + Math.random() * 800, glow: 0, fs: 0.5 + Math.random() * 2, fp: Math.random() * Math.PI * 2, row, col });
                }
            }
        }
        return chars;
    }, []);

    const mkRain = useCallback((w: number, h: number): RainDrop[] => {
        const drops: RainDrop[] = [];
        for (let i = 0; i < Math.floor(w / 16); i++) {
            if (Math.random() < 0.25) {
                const len = 4 + Math.floor(Math.random() * 12);
                const chars = Array.from({ length: len }, () => RAIN_CHARS[Math.floor(Math.random() * RAIN_CHARS.length)]);
                drops.push({ x: i * 16, y: -Math.random() * h * 1.5, speed: 0.8 + Math.random() * 2.5, chars, length: len, opacity: 0.03 + Math.random() * 0.08 });
            }
        }
        return drops;
    }, []);

    const mkGraph = useCallback((side: 'l' | 'r', w: number, h: number): GNode[] => {
        const labels = side === 'l'
            ? ['UU', 'PP', 'Perpres', 'Perda', 'Permen', 'SE', 'TAP', 'Keppres']
            : ['Pasal', 'Ayat', 'BAB', 'Huruf', 'KUH', 'KUHP', 'Perpu', 'PMK'];
        const cx = side === 'l' ? w * 0.10 : w * 0.90;
        const cy = h * 0.42;
        const sp = Math.min(w * 0.08, 100);
        return labels.map((label, i) => {
            const a = (i / labels.length) * Math.PI * 2;
            const r = sp * (0.5 + Math.random() * 0.5);
            const bx = cx + Math.cos(a) * r, by = cy + Math.sin(a) * r * 1.3;
            return { x: bx, y: by, bx, by, r: 2 + Math.random() * 2, ps: 0.5 + Math.random() * 1.5, pp: Math.random() * Math.PI * 2, label, conn: [(i + 1) % labels.length, (i + 2) % labels.length], gi: 0.3 + Math.random() * 0.4, or: 3 + Math.random() * 5, os: 0.2 + Math.random() * 0.4, op: Math.random() * Math.PI * 2 };
        });
    }, []);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d', { alpha: true });
        if (!ctx) return;
        const s = stateRef.current;

        const resize = () => {
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            canvas.width = window.innerWidth * dpr; canvas.height = window.innerHeight * dpr;
            canvas.style.width = `${window.innerWidth}px`; canvas.style.height = `${window.innerHeight}px`;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            s.rain = mkRain(window.innerWidth, window.innerHeight);
            s.lg = mkGraph('l', window.innerWidth, window.innerHeight);
            s.rg = mkGraph('r', window.innerWidth, window.innerHeight);
        };

        resize();
        window.addEventListener('resize', resize);
        if (!s.init) {
            s.chars = initChars();
            s.revealStart = performance.now();
            s.init = true;
        }

        const drawG = (nodes: GNode[], t: number, a: number) => {
            for (const n of nodes) {
                n.x = n.bx + Math.sin(t * n.os + n.op) * n.or;
                n.y = n.by + Math.cos(t * n.os * 0.7 + n.op) * n.or * 0.8;
            }
            for (const n of nodes) {
                for (const ci of n.conn) {
                    const tgt = nodes[ci]; if (!tgt) continue;
                    const ep = (Math.sin(t * 0.8 + n.pp) + 1) / 2;
                    ctx.beginPath(); ctx.moveTo(n.x, n.y); ctx.lineTo(tgt.x, tgt.y);
                    ctx.strokeStyle = `rgba(170,255,0,${a * 0.12 * (0.3 + ep * 0.7)})`; ctx.lineWidth = 0.5; ctx.stroke();
                    const pt = (t * 0.3 + n.pp) % 1;
                    ctx.beginPath(); ctx.arc(n.x + (tgt.x - n.x) * pt, n.y + (tgt.y - n.y) * pt, 1, 0, Math.PI * 2);
                    ctx.fillStyle = `rgba(170,255,0,${a * 0.35})`; ctx.fill();
                }
            }
            for (const n of nodes) {
                const p = (Math.sin(t * n.ps + n.pp) + 1) / 2;
                const nr = n.r * (1 + p * 0.4);
                const na = a * n.gi * (0.6 + p * 0.4);
                const g = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, nr * 5);
                g.addColorStop(0, `rgba(170,255,0,${na * 0.3})`); g.addColorStop(1, 'rgba(170,255,0,0)');
                ctx.fillStyle = g; ctx.fillRect(n.x - nr * 5, n.y - nr * 5, nr * 10, nr * 10);
                ctx.beginPath(); ctx.arc(n.x, n.y, nr, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(170,255,0,${na})`; ctx.fill();
                ctx.font = '8px "Geist Mono",monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
                ctx.fillStyle = `rgba(170,255,0,${na * 0.6})`; ctx.fillText(n.label, n.x, n.y + nr + 10);
            }
            ctx.textAlign = 'start'; ctx.textBaseline = 'alphabetic';
        };

        const draw = (ts: number) => {
            const w = window.innerWidth, h = window.innerHeight;
            const elapsed = ts - s.revealStart, t = ts * 0.001;

            // Clear with transparency
            ctx.clearRect(0, 0, w, h);

            // Rain
            ctx.font = '11px "Geist Mono",monospace';
            for (const d of s.rain) {
                d.y += d.speed;
                if (d.y > h + d.length * 16) { d.y = -d.length * 16; for (let j = 0; j < d.chars.length; j++) d.chars[j] = RAIN_CHARS[Math.floor(Math.random() * RAIN_CHARS.length)]; }
                for (let j = 0; j < d.chars.length; j++) {
                    const cy = d.y + j * 16; if (cy < -16 || cy > h + 16) continue;
                    ctx.fillStyle = j === 0 ? `rgba(170,255,0,${Math.min(d.opacity * 4, 0.35)})` : `rgba(170,255,0,${d.opacity * (1 - j / d.length * 0.85)})`;
                    ctx.fillText(d.chars[j], d.x, cy);
                }
            }

            // Graphs
            const gf = Math.min(elapsed / 2500, 1);
            drawG(s.lg, t, gf * 0.85); drawG(s.rg, t, gf * 0.85);

            // Garuda ASCII Art
            const artW = GARUDA_ART[0]?.length || 1;
            const artH = GARUDA_ART.length;
            const charW = Math.min(w * 0.55 / artW, 11);
            const charH = charW * 1.8;
            const ox = (w - artW * charW) / 2;
            const oy = (h - artH * charH) / 2 - h * 0.05;

            ctx.font = `bold ${Math.floor(charW * 1.3)}px "Geist Mono","Courier New",monospace`;
            ctx.textAlign = 'center'; ctx.textBaseline = 'middle';

            for (const gc of s.chars) {
                if (!gc.revealed && elapsed > gc.revealTime) { gc.revealed = true; gc.glow = 1.0; }
                if (!gc.revealed) continue;
                gc.glow = Math.max(0, gc.glow - 0.012);

                const flicker = 0.55 + 0.45 * Math.sin(t * gc.fs + gc.fp);
                const base = 0.25 + 0.35 * flicker;
                const final = Math.min(base + gc.glow, 1.0);
                const px = ox + gc.col * charW + charW / 2;
                const py = oy + gc.row * charH + charH / 2;

                const c = gc.char;
                const isShield = c === '░' || c === '█';
                const isStructure = c === '◆';
                const isFrame = '╱╲▔▕╳'.includes(c);
                const isText = /[A-Z ]/.test(c);

                if (gc.glow > 0.2) { ctx.shadowColor = '#AAFF00'; ctx.shadowBlur = gc.glow * 25; }

                if (isShield) ctx.fillStyle = `rgba(170,255,0,${final * 0.85})`;
                else if (isStructure) ctx.fillStyle = `rgba(220,255,100,${final * 0.8})`;
                else if (isText) ctx.fillStyle = `rgba(255,255,255,${final * 0.95})`;
                else if (isFrame) ctx.fillStyle = `rgba(170,255,0,${final * 0.5})`;
                else ctx.fillStyle = `rgba(130,200,0,${final * 0.6})`;

                ctx.fillText(c, px, py);
                ctx.shadowBlur = 0;
            }
            ctx.textAlign = 'start'; ctx.textBaseline = 'alphabetic';

            // Center glow
            const glowPulse = 0.03 + 0.02 * Math.sin(t * 0.4);
            const cg = ctx.createRadialGradient(w / 2, h * 0.38, 0, w / 2, h * 0.38, h * 0.32);
            cg.addColorStop(0, `rgba(170,255,0,${glowPulse})`); cg.addColorStop(0.6, `rgba(170,255,0,${glowPulse * 0.3})`); cg.addColorStop(1, 'rgba(170,255,0,0)');
            ctx.fillStyle = cg; ctx.fillRect(0, 0, w, h);

            // Scan beam
            const sy = ((t * 40) % (h + 30)) - 15;
            const sg = ctx.createLinearGradient(0, sy - 12, 0, sy + 12);
            sg.addColorStop(0, 'rgba(170,255,0,0)'); sg.addColorStop(0.5, 'rgba(170,255,0,0.015)'); sg.addColorStop(1, 'rgba(170,255,0,0)');
            ctx.fillStyle = sg; ctx.fillRect(0, sy - 12, w, 24);

            // Vignette
            const v = ctx.createRadialGradient(w / 2, h * 0.38, h * 0.12, w / 2, h * 0.42, h * 0.85);
            v.addColorStop(0, 'rgba(10,10,15,0)'); v.addColorStop(0.5, 'rgba(10,10,15,0.12)'); v.addColorStop(1, 'rgba(10,10,15,0.65)');
            ctx.fillStyle = v; ctx.fillRect(0, 0, w, h);

            animRef.current = requestAnimationFrame(draw);
        };

        animRef.current = requestAnimationFrame(draw);
        return () => { window.removeEventListener('resize', resize); cancelAnimationFrame(animRef.current); };
    }, [initChars, mkRain, mkGraph]);

    return <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" aria-hidden="true" />;
}

export default function JumbotronBackground() {
    return (
        <div className="absolute inset-0 w-full h-full overflow-hidden">
            {/* Layer 1: Beams — CSS zoom-out + center-crop to show wide diagonal beams */}
            <div
                className="absolute"
                style={{
                    width: '170%',
                    height: '170%',
                    left: '-35%',
                    top: '-35%',
                }}
            >
                <Beams
                    beamWidth={3}
                    beamHeight={30}
                    beamNumber={20}
                    lightColor="#ffffff"
                    speed={2}
                    noiseIntensity={1.75}
                    scale={0.2}
                    rotation={30}
                />
            </div>

            {/* Layer 2: ASCII Garuda + Matrix Rain + Graph Animations (transparent canvas overlay) */}
            <AsciiGarudaOverlay />
        </div>
    );
}
