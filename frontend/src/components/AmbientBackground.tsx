'use client';

import { useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';

export default function AmbientBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pathname = usePathname();
  const isHomePage = pathname === '/';

  useEffect(() => {
    // Home page uses JumbotronBackground instead — skip animation
    if (isHomePage) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;

    let animationId: number;
    let time = 0;

    const resize = () => {
      canvas.width = Math.floor(window.innerWidth / 2);
      canvas.height = Math.floor(window.innerHeight / 2);
    };

    resize();
    window.addEventListener('resize', resize);

    // Big vivid aurora orbs
    const orbs = [
      { x: 0.85, y: 0.08, r: 300, color: [140, 60, 255], speed: 0.25, phase: 0, drift: 30, alpha: 0.18 },
      { x: 0.1, y: 0.9, r: 280, color: [80, 30, 200], speed: 0.2, phase: 2, drift: 35, alpha: 0.16 },
      { x: 0.5, y: 0.45, r: 350, color: [110, 50, 220], speed: 0.15, phase: 4, drift: 20, alpha: 0.12 },
      { x: 0.2, y: 0.15, r: 220, color: [170, 80, 255], speed: 0.3, phase: 1.5, drift: 32, alpha: 0.14 },
      { x: 0.75, y: 0.75, r: 250, color: [90, 40, 180], speed: 0.22, phase: 3, drift: 26, alpha: 0.13 },
      { x: 0.5, y: 0.28, r: 200, color: [150, 230, 0], speed: 0.35, phase: 0.5, drift: 18, alpha: 0.07 },
      { x: 0.92, y: 0.5, r: 180, color: [160, 50, 220], speed: 0.28, phase: 5, drift: 22, alpha: 0.1 },
    ];

    const draw = () => {
      const { width, height } = canvas;

      ctx.fillStyle = '#0A0A0F';
      ctx.fillRect(0, 0, width, height);

      const t = time * 0.016;

      for (const orb of orbs) {
        const ox = orb.x * width + Math.sin(t * orb.speed + orb.phase) * orb.drift;
        const oy = orb.y * height + Math.cos(t * orb.speed * 0.7 + orb.phase * 1.3) * orb.drift * 0.6;
        const pulse = 1 + Math.sin(t * orb.speed * 0.5 + orb.phase) * 0.1;
        const radius = orb.r * pulse;

        const grad = ctx.createRadialGradient(ox, oy, 0, ox, oy, radius);
        const [r, g, b] = orb.color;
        grad.addColorStop(0, `rgba(${r},${g},${b},${orb.alpha})`);
        grad.addColorStop(0.35, `rgba(${r},${g},${b},${orb.alpha * 0.6})`);
        grad.addColorStop(0.7, `rgba(${r},${g},${b},${orb.alpha * 0.2})`);
        grad.addColorStop(1, `rgba(${r},${g},${b},0)`);

        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, width, height);
      }

      const vig = ctx.createRadialGradient(
        width / 2, height / 2, height * 0.2,
        width / 2, height / 2, height * 0.9
      );
      vig.addColorStop(0, 'rgba(10,10,15,0)');
      vig.addColorStop(1, 'rgba(10,10,15,0.5)');
      ctx.fillStyle = vig;
      ctx.fillRect(0, 0, width, height);

      time++;
      animationId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationId);
    };
  }, [isHomePage]);

  // Always render the same JSX structure (React Rules of Hooks).
  // Hide everything with `hidden` when on the home page.
  return (
    <div className={isHomePage ? 'hidden' : undefined}>
      {/* Canvas aurora — half-res for perf */}
      <canvas
        ref={canvasRef}
        className="fixed inset-0 -z-10 pointer-events-none w-full h-full"
        aria-hidden="true"
      />

      {/* Film grain texture */}
      <div
        className="fixed inset-0 -z-[9] pointer-events-none opacity-[0.04] mix-blend-overlay"
        aria-hidden="true"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E")`,
          backgroundSize: '200px 200px',
        }}
      />

      {/* Subtle tech grid with radial mask */}
      <div
        className="fixed inset-0 -z-[8] pointer-events-none opacity-[0.03]"
        aria-hidden="true"
        style={{
          backgroundImage: `
            linear-gradient(rgba(170, 255, 0, 0.5) 1px, transparent 1px),
            linear-gradient(90deg, rgba(170, 255, 0, 0.5) 1px, transparent 1px)
          `,
          backgroundSize: '80px 80px',
          maskImage: 'radial-gradient(ellipse 50% 40% at 50% 45%, black 10%, transparent 60%)',
          WebkitMaskImage: 'radial-gradient(ellipse 50% 40% at 50% 45%, black 10%, transparent 60%)',
        }}
      />
    </div>
  );
}
